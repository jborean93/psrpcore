# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import logging
import typing
import uuid
from xml.etree import ElementTree

from psrpcore._command import Command
from psrpcore._crypto import PSRemotingCrypto, rsa
from psrpcore._events import PSRPEvent, SessionCapabilityEvent
from psrpcore._exceptions import InvalidRunspacePoolState, PSRPCoreError
from psrpcore._payload import (
    ProtocolVersion,
    PSRPMessage,
    PSRPPayload,
    StreamType,
    create_message,
    dict_to_psobject,
    unpack_fragment,
    unpack_message,
)
from psrpcore.types import (
    ApartmentState,
    CommandTypes,
    CreatePipeline,
    EndOfPipelineInput,
    ErrorRecord,
    GetCommandMetadata,
    HostInfo,
    PSInvocationState,
    PSObject,
    PSRPMessageType,
    PSThreadOptions,
    PSVersion,
    RemoteStreamOptions,
    RunspacePoolState,
    SessionCapability,
    deserialize,
    serialize,
)

log = logging.getLogger(__name__)

T = typing.TypeVar("T", bound="RunspacePool")


_DEFAULT_CAPABILITY = SessionCapability(
    PSVersion=PSVersion("2.0"),
    protocolversion=ProtocolVersion.Pwsh5.value,
    SerializationVersion=PSVersion("1.1.0.1"),
)


class RunspacePool:
    """Runspace Pool base class.

    This is the base class for a Runspace Pool. It contains the common
    attributes and methods used by both a client and server based Runspace
    Pool.

    Args:
        runspace_pool_id: The UUID that identified the Runspace Pool.
        capability: The SessionCapability of the caller.
        application_arguments: Any arguments supplied when creating the
            Runspace Pool as a client.
        application_private_data: Any special data supplied by the Runspace
            Pool as a server.

    Attributes:
        runspace_pool_id: See args.
        our_capability: The SessionCapability of the caller.
        their_capability: The SessionCapability of the peer, only populated
            after the Runspace Pool has been opened.
        application_arguments: The application arguments from the client, will
            be populated for the server after the Runspace Pool has been
            opened.
        application_private_data: The app private data supplied by the server,
            will be populated for the client after the Runspace Pool has been
            opened.
        host: The HostInfo that contains host information of the client.
        state: The current state of the Runspace Pool.
        apartment_state: The apartment state of the thread used to execute
            commands within this Runspace Pool.
        thread_options: Determines whether a new thread is created for each
            invocation.
        pipeline_table: A dictionary that contains associated pipelines with
            this Runspace Pool.
    """

    def __new__(
        cls,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> "RunspacePool":
        if cls == RunspacePool:
            raise TypeError(
                f"Type {cls.__qualname__} cannot be instantiated; it can be used only as a base class for "
                f"client/server runspace pool types."
            )

        return super().__new__(cls)

    def __init__(
        self,
        runspace_pool_id: uuid.UUID,
        capability: typing.Optional[SessionCapability],
        application_arguments: typing.Dict[str, typing.Any],
        application_private_data: typing.Dict[str, typing.Any],
    ) -> None:
        self.runspace_pool_id = runspace_pool_id
        self.our_capability: SessionCapability = capability or _DEFAULT_CAPABILITY
        self.their_capability: typing.Optional[SessionCapability] = None
        self.application_arguments = application_arguments
        self.application_private_data = application_private_data
        self.host: typing.Optional[HostInfo] = None
        self.state = RunspacePoolState.BeforeOpen
        self.apartment_state = ApartmentState.Unknown
        self.thread_options = PSThreadOptions.Default
        self.pipeline_table: typing.Dict[uuid.UUID, "Pipeline"] = {}

        self._ci_handlers: typing.Dict[int, typing.Optional[typing.Callable[[PSRPEvent], None]]] = {}
        self._ci_events: typing.Dict[int, PSRPEvent] = {}
        self._ci_count = 1
        self._fragment_count = 1
        self._cipher: typing.Optional[PSRemotingCrypto] = None
        self._exchange_key: typing.Optional[rsa.RSAPrivateKey] = None
        self._min_runspaces = 0
        self._max_runspaces = 0
        self._send_buffer: typing.List[PSRPMessage] = []

        # Raw bytes received but not yet processed.
        self._receive_buffer = bytearray()

        # Fragments for each object_id that have been received but not yet combined to a message.
        self._incoming_fragments: typing.Dict[int, typing.List[bytearray]] = {}

        # Messages from combined fragments that have been received but not yet returned.
        self._incoming_messages: typing.Dict[int, PSRPMessage] = {}

    @property
    def max_runspaces(
        self,
    ) -> int:
        """The maximum number of runspaces the pool maintains."""
        return self._max_runspaces

    @property
    def min_runspaces(
        self,
    ) -> int:
        """The minimum number of runspaces the pool maintains."""
        return self._min_runspaces

    @property
    def _ci_counter(
        self,
    ) -> int:
        """Counter used for ci calls."""
        ci = self._ci_count
        self._ci_count += 1
        return ci

    @property
    def _fragment_counter(
        self,
    ) -> int:
        """Counter used for fragment object IDs."""
        count = self._fragment_count
        self._fragment_count += 1
        return count

    def begin_close(self) -> None:
        """Marks the Runspace Pool to be in the closing phase."""
        self._change_state(RunspacePoolState.Closing)

    def close(self) -> None:
        """Marks the Runspace Pool as closed.

        This closes the Runspace Pool. Communicating to the peer that the pool
        is being closed is done through a connection specific process. This
        method just verifies the Runspace Pool is in a state that can be closed
        and that no pipelines are still running.
        """
        if self.pipeline_table:
            raise PSRPCoreError("Must close existing pipelines before closing the pool")

        valid_states = [RunspacePoolState.Closed, RunspacePoolState.Closing, RunspacePoolState.Opened]
        if self.state not in valid_states:
            raise InvalidRunspacePoolState("close Runspace Pool", self.state, valid_states)

        self._change_state(RunspacePoolState.Closed)

    def begin_disconnect(self) -> None:
        """Marks the Runspace Pool to be in the disconnecting phase."""
        self._change_state(RunspacePoolState.Disconnecting)

    def disconnect(self) -> None:
        """Marks the Runspace Pool as disconnected.

        This disconnects the Runspace Pool. COmmunicating to the peer that the
        pool is disconnected is done through a connection specific process.
        """
        valid_states = [RunspacePoolState.Opened, RunspacePoolState.Disconnecting, RunspacePoolState.Disconnected]
        if self.state not in valid_states:
            raise InvalidRunspacePoolState("disconnect a Runspace Pool", self.state, valid_states)

        self._change_state(RunspacePoolState.Disconnected)

    def reconnect(self) -> None:
        """Marks the Runspace Pool as reconnected and opened."""
        valid_states = [RunspacePoolState.Disconnected, RunspacePoolState.Opened]
        if self.state not in valid_states:
            raise InvalidRunspacePoolState("reconnect to a Runspace Pool", self.state, valid_states)

        self._change_state(RunspacePoolState.Opened)

    def data_to_send(
        self,
        amount: typing.Optional[int] = None,
    ) -> typing.Optional[PSRPPayload]:
        """Gets the next PSRP payload.

        Returns the PSRPPayload that contains the data that needs to be sent
        to the peer. This is a non-blocking call and is used by the
        implementer to get the next PSRP payload that is then sent over it's
        transport.

        Args:
            amount: The maximum size of the data fragment that can be sent.
                This must be 22 or larger to fit the fragment headers.

        Returns:
             typing.Optional[PSRPPayload]: The payload (if any) that needs to
                be sent to the peer.
        """
        if amount is not None and amount < 22:
            raise ValueError("amount must be 22 or larger to fit a PSRP fragment")

        current_buffer = bytearray()
        stream_type = StreamType.default
        pipeline_id = None
        fragment_size = 21
        # TODO: prioritise prompt_response over default if the last fragment was an end fragment.

        for message in list(self._send_buffer):
            if amount is not None and amount < fragment_size:
                break

            if not current_buffer:
                stream_type = message.stream_type
                pipeline_id = message.pipeline_id

            # We can only combine fragments if they are for the same target.
            if pipeline_id != message.pipeline_id:
                break

            if amount is None:
                allowed_length = len(message)
            else:
                allowed_length = amount - fragment_size
                amount -= fragment_size + len(message)

            current_buffer += message.fragment(allowed_length)
            if len(message) == 0:
                self._send_buffer.remove(message)

        return PSRPPayload(bytes(current_buffer), stream_type, pipeline_id) if current_buffer else None

    def receive_data(
        self,
        data: PSRPPayload,
    ) -> None:
        """Store any incoming data.

        Stores any incoming payloads in an internal buffer to be processed.
        This buffer is read when calling :meth:`next_event()`.

        Args:
            data: The PSRP payload data received from the transport.
        """
        self._receive_buffer += data.data

    def next_event(
        self,
    ) -> typing.Optional[PSRPEvent]:
        """Process data received from the peer.

        This processes any PSRP data that has been received from the peer. Will
        return the next PSRP event in the receive buffer or `None` if not
        enough data is available.

        Returns:
            typing.Optional[PSRPEvent]: The next event present in the incoming
                data buffer or `None` if not enough data has been received.
        """
        # First unpacks the raw receive buffer into messages.
        while self._receive_buffer:
            fragment = unpack_fragment(self._receive_buffer)
            self._receive_buffer = self._receive_buffer[21 + len(fragment.data) :]

            buffer = self._incoming_fragments.setdefault(fragment.object_id, [])
            if fragment.fragment_id != len(buffer):
                raise PSRPCoreError(
                    f"Expecting fragment with a fragment id of {len(buffer)} not {fragment.fragment_id}"
                )
            buffer.append(fragment.data)

            if fragment.end:
                raw_message = unpack_message(bytearray(b"".join(buffer)))
                message = PSRPMessage(
                    raw_message.message_type, raw_message.data, raw_message.rpid, raw_message.pid, fragment.object_id
                )
                self._incoming_messages[fragment.object_id] = message
                del self._incoming_fragments[fragment.object_id]

        for object_id in list(self._incoming_messages.keys()):
            message = self._incoming_messages[object_id]
            # In case of a failure it is expected for the client to receive the correct data instead
            del self._incoming_messages[object_id]

            event = self._process_message(message)

            return event

        # Need more data from peer to produce an event.
        return None

    def prepare_message(
        self,
        message: PSObject,
        message_type: typing.Optional[PSRPMessageType] = None,
        pipeline_id: typing.Optional[uuid.UUID] = None,
        stream_type: StreamType = StreamType.default,
    ) -> None:
        """Adds a PSRP message to send buffer.

        Adds the given PSRP message to the send buffer to be sent when the
        caller requires it to.

        Args:
            message: The PSObject to be send.
            message_type: Override the message type of the PSRP messae in case
                message is not an actual PSRP Message object.
            pipeline_id: The pipeline id the message is for or `None` if it
                targets the runspace pool.
            stream_type: The stream type the message is for.
        """
        if isinstance(message, EndOfPipelineInput):
            b_data = b""  # Special edge case for this particular message type
        else:
            element = serialize(
                message,
                cipher=self._cipher,
                # Extra info we pass to the serializer that may adjust how objects are serialized.
                our_capability=self.our_capability,
                their_capability=self.their_capability,
            )
            b_data = ElementTree.tostring(element, encoding="utf-8", method="xml")

        if message_type is None:
            try:
                message_type = PSRPMessageType.get_message_id(type(message))
            except KeyError:
                raise ValueError("message_type must be specified when the message is not a PSRP message") from None

        is_client = isinstance(self, RunspacePool)
        b_msg = create_message(is_client, message_type, b_data, self.runspace_pool_id, pipeline_id)

        object_id = self._fragment_counter
        psrp_message = PSRPMessage(
            message_type, bytearray(b_msg), self.runspace_pool_id, pipeline_id, object_id, stream_type
        )
        self._send_buffer.append(psrp_message)

    def _change_state(
        self,
        state: RunspacePoolState,
        error: typing.Optional[ErrorRecord] = None,
    ) -> None:
        self.state = state

    def _process_message(
        self,
        message: PSRPMessage,
    ) -> PSRPEvent:
        """Process a TransportDataAction data message received from a peer."""
        ps_object: typing.Any
        if message.message_type == PSRPMessageType.EndOfPipelineInput:
            # Special edge case for EndOfPipelineInput which has no data.
            ps_object = EndOfPipelineInput()

        else:
            ps_object = deserialize(
                ElementTree.fromstring(message.data),
                cipher=self._cipher,
                # Extra info we pass to the serializer that may adjust how objects are serialized.
                our_capability=self.our_capability,
                their_capability=self.their_capability,
            )

        event = PSRPEvent.create(message.message_type, ps_object, message.runspace_pool_id, message.pipeline_id)

        process_func = getattr(self, f"_process_{message.message_type.name}", None)
        if process_func:
            process_func(event)

        else:
            log.warning(f"Received {message.message_type!s} but could not process it")

        return event

    def _process_SessionCapability(
        self,
        event: SessionCapabilityEvent,
    ) -> None:
        # This is the only common message that is processed the same by clients and servers.
        self.their_capability = event.ps_object


class Pipeline(typing.Generic[T]):
    """Pipeline base class.

    This is the base class for a Pipeline. It contains the common attributes
    and methods used by both a client and server base Pipeline.

    Args:
        runspace_pool: The Runspace Pool the pipeline is part of. When
            initialised the pipeline will add itself to the Runspace Pool
            pipeline table.
        pipeline_id: The Pipeline identifier.

    Attributes:
        runspace_pool: See args.
        pipeline_id: See args.
        state: The pipeline state.
    """

    def __new__(
        cls,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> "Pipeline":
        if cls == Pipeline:
            raise TypeError(
                f"Type {cls.__qualname__} cannot be instantiated; it can be used only as a base class for "
                f"client/server pipeline types."
            )

        return super().__new__(cls)

    def __init__(
        self,
        runspace_pool: T,
        pipeline_id: uuid.UUID,
    ) -> None:
        self.runspace_pool = runspace_pool
        self.pipeline_id = pipeline_id
        self.state = PSInvocationState.NotStarted
        runspace_pool.pipeline_table[self.pipeline_id] = self

    def close(self) -> None:
        """Close the Pipeline.

        Closes the pipeline by removing itself from the Runspace Pool pipeline
        table.
        """
        self.runspace_pool.pipeline_table.pop(self.pipeline_id, None)

    def prepare_message(
        self,
        message: PSObject,
        message_type: typing.Optional[PSRPMessageType] = None,
        stream_type: StreamType = StreamType.default,
    ) -> None:
        """Adds a PSRP message to send buffer.

        Adds the given PSRP message to the send buffer to be sent when the
        caller requires it to. This just calls `prepare_message` on the
        Runspace Pool but for this specific pipeline.

        Args:
            message: The PSObject to be send.
            message_type: Override the message type of the PSRP messae in case
                message is not an actual PSRP Message object.
            stream_type: The stream type the message is for.
        """
        self.runspace_pool.prepare_message(message, message_type, self.pipeline_id, stream_type)

    def to_psobject(
        self,
    ) -> PSObject:
        """Converts the pipeline to a PSObject for serialization."""
        raise NotImplementedError()  # pragma: no cover


class PowerShellPipeline(Pipeline):
    """PowerShell Pipeline.

    This implements the PowerShell pipeline specific methods used to invoke a
    PowerShell pipeline.

    Args:
        add_to_history: Whether to add the pipeline to the history field of the
            runspace.
        apartment_state: The apartment state of the thread that executes the
            pipeline.
        history: The value to use as a historial reference of the pipeline.
        host: The host information to use when executing the pipeline.
        is_nested: Whether the pipeline is nested in another pipeline or not.
        no_input: Whether there is any data to be input into the pipeline.
        remote_stream_options: Whether to add invocation info the the PowerShell
            streams or not.
        redirect_shell_error_to_out: Redirects the global error output pipe to
            the commands error output pipe.
    """

    def __init__(
        self,
        add_to_history: bool = False,
        apartment_state: typing.Optional[ApartmentState] = None,
        history: typing.Optional[str] = None,
        host: typing.Optional[HostInfo] = None,
        is_nested: bool = False,
        no_input: bool = True,
        remote_stream_options: RemoteStreamOptions = RemoteStreamOptions.none,
        redirect_shell_error_to_out: bool = True,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.add_to_history = add_to_history
        self.apartment_state = apartment_state or self.runspace_pool.apartment_state
        self.commands: typing.List[Command] = []
        self.history = history
        self.host = host or HostInfo()
        self.is_nested = is_nested
        self.no_input = no_input
        self.remote_stream_options = remote_stream_options
        self.redirect_shell_error_to_out = redirect_shell_error_to_out

    def to_psobject(
        self,
    ) -> CreatePipeline:
        if not self.commands:
            raise ValueError("A command is required to invoke a PowerShell pipeline.")

        extra_cmds: typing.List[typing.List[PSObject]] = [[]]
        for cmd in self.commands:
            extra_cmds[-1].append(cmd)
            if cmd.end_of_statement:
                extra_cmds.append([])
        cmds = extra_cmds.pop(0)

        # MS-PSRP 2.2.3.11 Pipeline
        # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/82a8d1c6-4560-4e68-bfd0-a63c36d6a199
        pipeline_kwargs = {
            "Cmds": cmds,
            "IsNested": self.is_nested,
            "History": self.history,
            "RedirectShellErrorOutputPipe": self.redirect_shell_error_to_out,
        }

        if extra_cmds:
            # This isn't documented in MS-PSRP but this is how PowerShell batches multiple statements in 1 pipeline.
            # TODO: ExtraCmds may not work with protocol <=2.1.
            pipeline_kwargs["ExtraCmds"] = [dict_to_psobject(Cmds=s) for s in extra_cmds]

        return CreatePipeline(
            NoInput=self.no_input,
            ApartmentState=self.apartment_state,
            RemoteStreamOptions=self.remote_stream_options,
            AddToHistory=self.add_to_history,
            HostInfo=self.host,
            PowerShell=dict_to_psobject(**pipeline_kwargs),
            IsNested=self.is_nested,
        )


class GetCommandMetadataPipeline(Pipeline):
    """Get Command Metadata Pipeline.

    This implements the GetCommandMetadata pipeline specific methods used to get
    command metadata information.

    Args:
        name: List of command names to get the metadata for. Uses ``*`` as a
            wildcard.
        command_type: The type of commands to filter by.
        namespace: Wildcard patterns describbing the command namespace to filter
            by.
        arguments: Extra arguments passed to the higher-layer above PSRP.
    """

    def __init__(
        self,
        name: typing.Union[str, typing.List[str]],
        command_type: CommandTypes = CommandTypes.All,
        namespace: typing.Optional[typing.List[str]] = None,
        arguments: typing.Optional[typing.List[typing.Any]] = None,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        if not isinstance(name, list):
            name = [name]
        self.name = name
        self.command_type = command_type
        self.namespace = namespace
        self.arguments = arguments

    def to_psobject(
        self,
    ) -> GetCommandMetadata:
        return GetCommandMetadata(
            Name=self.name,
            CommandType=self.command_type,
            Namespace=self.namespace,
            ArgumentList=self.arguments,
        )
