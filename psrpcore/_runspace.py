# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import base64
import datetime
import os
import platform
import typing
import uuid

from xml.etree import (
    ElementTree,
)

from psrpcore._crypto import (
    create_keypair,
    encrypt_session_key,
    decrypt_session_key,
    PSRemotingCrypto,
)

from psrpcore._events import (
    ApplicationPrivateDataEvent,
    ConnectRunspacePoolEvent,
    CreatePipelineEvent,
    DebugRecordEvent,
    EncryptedSessionKeyEvent,
    EndOfPipelineInputEvent,
    ErrorRecordEvent,
    GetAvailableRunspacesEvent,
    GetCommandMetadataEvent,
    InformationRecordEvent,
    InitRunspacePoolEvent,
    PipelineHostCallEvent,
    PipelineHostResponseEvent,
    PipelineInputEvent,
    PipelineOutputEvent,
    PipelineStateEvent,
    ProgressRecordEvent,
    PSRPEvent,
    PublicKeyEvent,
    PublicKeyRequestEvent,
    ResetRunspaceStateEvent,
    RunspaceAvailabilityEvent,
    RunspacePoolHostCallEvent,
    RunspacePoolHostResponseEvent,
    RunspacePoolInitDataEvent,
    RunspacePoolStateEvent,
    SessionCapabilityEvent,
    SetMaxRunspacesEvent,
    SetMinRunspacesEvent,
    UserEventEvent,
    VerboseRecordEvent,
    WarningRecordEvent,
)

from psrpcore._exceptions import (
    InvalidProtocolVersion,
    InvalidRunspacePoolState,
    PSRPCoreError,
)

from psrpcore._payload import (
    create_message,
    EMPTY_UUID,
    PSRPMessage,
    PSRPPayload,
    StreamType,
    unpack_fragment,
    unpack_message,
)

from psrpcore._pipeline import (
    Command,
    PipelineType,
    ServerGetCommandMetadata,
    ServerPowerShell,
)

from psrpcore._serializer import (
    deserialize,
    serialize,
)

from psrpcore.types import (
    ApartmentState,
    ErrorRecord,
    HostInfo,
    HostMethodIdentifier,
    PSInvocationState,
    PSThreadOptions,
    RunspacePoolState,
    PSDateTime,
    PSGuid,
    PSInt,
    PSObject,
    PSString,
    PSVersion,
)

from psrpcore.types._psrp_messages import (
    ApplicationPrivateData,
    ConnectRunspacePool,
    EncryptedSessionKey,
    EndOfPipelineInput,
    GetAvailableRunspaces,
    InitRunspacePool,
    PipelineHostCall,
    PipelineHostResponse,
    PSRPMessageType,
    PublicKey,
    PublicKeyRequest,
    ResetRunspaceState,
    RunspaceAvailability,
    RunspacePoolHostCall,
    RunspacePoolHostResponse,
    RunspacePoolInitData,
    RunspacePoolState as RunspacePoolStateMsg,
    SessionCapability,
    SetMaxRunspaces,
    SetMinRunspaces,
    UserEvent,
)


_DEFAULT_CAPABILITY = SessionCapability(
    PSVersion=PSVersion("2.0"),
    protocolversion=PSVersion("2.3"),
    SerializationVersion=PSVersion("1.1.0.1"),
)


class _RunspacePoolBase:
    """Runspace Pool base class.

    This is the base class for a Runspace Pool. It contains the common
    attributes and methods used by both a client and server based Runspace
    Pool.

    Args:
        runspace_id: The UUID that identified the Runspace Pool.
        capability: The SessionCapability of the caller.
        application_arguments: Any arguments supplied when creating the
            Runspace Pool as a client.
        application_private_data: Any special data supplied by the Runspace
            Pool as a server.

    Attributes:
        host: The HostInfo that contains host information of the client.
        runspace_id: See args.
        state: The current state of the Runspace Pool.
        apartment_state: The apartment state of the thread used to execute
            commands within this Runspace Pool.
        thread_options: Determines whether a new thread is created for each
            invocation.
        pipeline_table: A dictionary that contains associated pipelines with
            this Runspace Pool.
        our_capability: The SessionCapability of the caller.
        their_capability: The SessionCapability of the peer, only populated
            after the Runspace Pool has been opened.
        application_arguments: The application arguments from the client, will
            be populated for the server after the Runspace Pool has been
            opened.
        application_private_data: The app private data supplied by the server,
            will be populated for the client after the Runspace Pool has been
            opened.
    """

    def __new__(cls, *args, **kwargs):
        if cls in [_RunspacePoolBase]:
            raise TypeError(
                f"Type {cls.__qualname__} cannot be instantiated; it can be used only as a base class for "
                f"Runspace Pool types."
            )

        return super().__new__(cls)

    def __init__(
        self,
        runspace_id: uuid.UUID,
        capability: SessionCapability,
        application_arguments: typing.Dict,
        application_private_data: typing.Dict,
    ):
        self.runspace_id = runspace_id
        self.host: typing.Optional[HostInfo] = None
        self.state = RunspacePoolState.BeforeOpen
        self.apartment_state = ApartmentState.Unknown
        self.thread_options = PSThreadOptions.Default
        self.pipeline_table: typing.Dict[uuid.UUID, "PipelineType"] = {}
        self.our_capability = capability
        self.their_capability: typing.Optional[SessionCapability] = None
        self.application_arguments = application_arguments
        self.application_private_data = application_private_data

        self._ci_table = {}
        self.__ci_counter = 1
        self.__fragment_counter = 1
        self._cipher: typing.Optional[PSRemotingCrypto] = None
        self._exchange_key = None
        self._min_runspaces = 0
        self._max_runspaces = 0
        self._send_buffer: typing.List[PSRPMessage] = []
        self._receive_buffer = bytearray()
        self._incoming_buffer: typing.Dict[int, typing.Union[typing.List[bytes], PSRPEvent, PSRPMessage]] = {}

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
        ci = self.__ci_counter
        self.__ci_counter += 1
        return ci

    @property
    def _fragment_counter(
        self,
    ) -> int:
        """Counter used for fragment object IDs."""
        count = self.__fragment_counter
        self.__fragment_counter += 1
        return count

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

                # Special edge case where we need to change the RunspacePool state when the last SessionCapability
                # fragment was sent.
                if (
                    self.state == RunspacePoolState.Opening
                    and message.message_type == PSRPMessageType.SessionCapability
                ):
                    self.state = RunspacePoolState.NegotiationSent

        if current_buffer:
            return PSRPPayload(bytes(current_buffer), stream_type, pipeline_id)

    def receive_data(
        self,
        data: PSRPPayload,
    ):
        """Store any incoming data.

        Stores any incoming payloads in an internal buffer to be processed.
        This buffer is read when calling `:meth:next_event()`.

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

            buffer = self._incoming_buffer.setdefault(fragment.object_id, [])
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
                self._incoming_buffer[fragment.object_id] = message

        for object_id in list(self._incoming_buffer.keys()):
            event = self._incoming_buffer[object_id]
            if isinstance(event, list):
                continue

            event = self._process_message(event)

            # We only want to clear the incoming buffer entry once we know the caller has the object.
            del self._incoming_buffer[object_id]
            return event

        # Need more data from te peer to produce an event.
        return

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
        required_states = [
            RunspacePoolState.Connecting,
            RunspacePoolState.Opened,
            RunspacePoolState.Opening,
            RunspacePoolState.NegotiationSent,
            RunspacePoolState.NegotiationSucceeded,
        ]
        if self.state not in required_states:
            raise InvalidRunspacePoolState("send PSRP message", self.state, required_states)

        if isinstance(message, EndOfPipelineInput):
            b_data = b""  # Special edge case for this particular message type
        else:
            b_data = ElementTree.tostring(serialize(message, cipher=self._cipher), encoding="utf-8", method="xml")

        if message_type is None:
            message_type = PSRPMessageType(message.PSObject.psrp_message_type)

        is_client = isinstance(self, RunspacePool)
        message = create_message(is_client, message_type, b_data, self.runspace_id, pipeline_id)

        object_id = self._fragment_counter
        psrp_message = PSRPMessage(message_type, message, self.runspace_id, pipeline_id, object_id, stream_type)
        self._send_buffer.append(psrp_message)

    def _process_message(
        self,
        message: PSRPMessage,
    ) -> PSRPEvent:
        """Process a TransportDataAction data message received from a peer."""
        if not message.data:
            # Special edge case for EndOfPipelineInput which has no data.
            ps_object = None

        else:
            ps_object = deserialize(ElementTree.fromstring(message.data), cipher=self._cipher)

        event = PSRPEvent(message.message_type, ps_object, message.runspace_pool_id, message.pipeline_id)

        process_func = getattr(self, f"_process_{message.message_type.name}", None)
        if process_func:
            process_func(event)

        else:
            # FIXME: Convert to a warning
            print(f"Received unknown message {message.message_type!s}")

        return event

    def _process_SessionCapability(
        self,
        event: SessionCapabilityEvent,
    ):
        # TODO: Verify the versions
        self.their_capability = event.ps_object
        self.state = RunspacePoolState.NegotiationSucceeded


class RunspacePool(_RunspacePoolBase):
    """Client Runspace Pool.

    Represents a Runspace Pool on a remote host which can contain one or more
    running pipelines. This is a non blocking connection object that handles
    the incoming and outgoing PSRP packets without worrying about the IO. This
    model is inspired by `Sans-IO model`_ where this object deals with only
    the PSRP protocol and needs to be combined with an IO transport separately.

    This is meant to be a close representation of the
    `System.Management.Automation.Runspaces.RunspacePool`_ .NET class.

    Args:
        application_arguments: Arguments that are sent to the server and
            accessible through `$PSSenderInfo.ApplicationArguments` of a
            pipeline that runs in this Runspace Pool.
        apartment_state: The apartment state of the thread used to execute
            commands within this Runspace Pool.
        host: The HostInfo that describes the client hosting application.
        thread_options: Determines whether a new thread is created for each
            invocation.
        min_runspaces: The minimum number of Runspaces a pool can hold.
        max_runspaces: The maximum number of Runspaces a pool can hold.
        runspace_pool_id: Manually set the Runspace Pool ID, used when
            reconnecting to an existing Runspace Pool.

    .. _System.Management.Automation.Runspaces.RunspacePool:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.runspaces.runspacepool

    .. _Sans-IO model:
        https://sans-io.readthedocs.io/
    """

    def __init__(
        self,
        application_arguments: typing.Optional[typing.Dict] = None,
        apartment_state: ApartmentState = ApartmentState.Unknown,
        host: typing.Optional[HostInfo] = None,
        thread_options: PSThreadOptions = PSThreadOptions.Default,
        min_runspaces: int = 1,
        max_runspaces: int = 1,
        runspace_pool_id: typing.Optional[uuid.UUID] = None,
    ):
        super().__init__(
            runspace_pool_id or uuid.uuid4(),
            capability=_DEFAULT_CAPABILITY,
            application_arguments=application_arguments or {},
            application_private_data={},
        )
        self.apartment_state = apartment_state
        self.host = host
        self.thread_options = thread_options
        self._min_runspaces = min_runspaces
        self._max_runspaces = max_runspaces

    def connect(self):
        if self.state == RunspacePoolState.Opened:
            return
        if self.state != RunspacePoolState.Disconnected:
            raise InvalidRunspacePoolState("connect to Runspace Pool", self.state, [RunspacePoolState.Disconnected])

        self.state = RunspacePoolState.Connecting

        self.prepare_message(self.our_capability)
        self.prepare_message(ConnectRunspacePool())

    def close(self):
        """Closes the RunspacePool.

        This closes the RunspacePool on the peer. Closing the Runspace Pool is
        done through a connection specific process. This method just verifies
        the Runspace Pool is in a state that can be closed and that no
        pipelines are still running.
        """
        if self.state in [RunspacePoolState.Closed, RunspacePoolState.Closing, RunspacePoolState.Broken]:
            return
        if self.pipeline_table:
            raise PSRPCoreError("Must close these pipelines first")

        self.state = RunspacePoolState.Closing

    def get_available_runspaces(self) -> int:
        """Get the number of Runspaces available.

        This builds a request to get the number of available Runspaces in the
        pool. The
        :class:`psrp.protocol.powershell_events.GetRunspaceAvailabilityEvent`
        is returned once the response is received from the server.
        """
        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("get available Runspaces", self.state, [RunspacePoolState.Opened])

        ci = self._ci_counter
        self._ci_table[ci] = None
        self.prepare_message(GetAvailableRunspaces(ci=ci))

        return ci

    def open(self):
        """Opens the RunspacePool.

        This opens the RunspacePool on the peer.
        """
        if self.state == RunspacePoolState.Opened:
            return
        if self.state != RunspacePoolState.BeforeOpen:
            raise InvalidRunspacePoolState("open Runspace Pool", self.state, [RunspacePoolState.BeforeOpen])

        host = self.host or HostInfo()
        self.state = RunspacePoolState.Opening

        self.prepare_message(self.our_capability)

        init_runspace_pool = InitRunspacePool(
            MinRunspaces=self._min_runspaces,
            MaxRunspaces=self._max_runspaces,
            PSThreadOptions=self.thread_options,
            ApartmentState=self.apartment_state,
            HostInfo=host,
            ApplicationArguments=self.application_arguments,
        )
        self.prepare_message(init_runspace_pool)

    def exchange_key(self):
        """Exchange session specific key.

        Request the session key from the peer.
        """
        if self._cipher:
            return

        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("start session key exchange", self.state, [RunspacePoolState.Opened])

        self._exchange_key, public_key = create_keypair()
        b64_public_key = base64.b64encode(public_key).decode()

        self.prepare_message(PublicKey(PublicKey=b64_public_key))

    def host_response(
        self,
        ci: int,
        return_value: typing.Optional[typing.Any] = None,
        error_record: typing.Optional[ErrorRecord] = None,
    ):
        """Respond to a host call.

        Respond to a host call event with either a return value or an error
        record.

        Args:
            ci: The call ID associated with the host call to response to.
            return_value: The return value for the host call.
            error_record: The error record raised by the host when running the
                host call.
        """
        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("response to host call", self.state, [RunspacePoolState.Opened])

        call_event = self._ci_table.pop(ci)

        method_identifier = call_event.ps_object.mi
        pipeline_id = call_event.pipeline_id

        host_call_obj = PipelineHostResponse if pipeline_id else RunspacePoolHostResponse

        host_call = host_call_obj(ci=ci, mi=method_identifier)
        if return_value is not None:
            host_call.mr = return_value

        if error_record is not None:
            host_call.me = error_record

        self.prepare_message(host_call, pipeline_id=pipeline_id, stream_type=StreamType.prompt_response)

    def reset_runspace_state(self) -> int:
        """Reset the Runspace Pool state.

        Resets the variable table for the Runspace Pool back to the default
        state.
        """
        their_version = self.their_capability.protocolversion
        required_version = PSVersion("2.3")
        if their_version < required_version:
            raise InvalidProtocolVersion("reset Runspace Pool state", their_version, required_version)
        if self.state == RunspacePoolState.BeforeOpen:
            return
        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("reset Runspace Pool state", self.state, [RunspacePoolState.Opened])

        ci = self._ci_counter
        self._ci_table[ci] = None
        self.prepare_message(ResetRunspaceState(ci=ci))

        return ci

    def set_max_runspaces(
        self,
        value: int,
    ) -> typing.Optional[int]:
        """Set the maximum number of runspaces.

        Build a request to set the maximum number of Runspaces the pool
        maintains. The `max_runspaces` property is updated once the
        `:class:SetMaxRunspacesEvent` is fired.

        Args:
            value: The maximum number of runspaces in a pool to change to.
        """
        if self.state == RunspacePoolState.BeforeOpen or self._max_runspaces == value:
            self._max_runspaces = value
            return

        ci = self._ci_counter
        self._ci_table[ci] = lambda e: setattr(self, "_max_runspaces", value)
        self.prepare_message(SetMaxRunspaces(MaxRunspaces=value, ci=ci))

        return ci

    def set_min_runspaces(
        self,
        value: int,
    ) -> typing.Optional[int]:
        """Set the minimum number of runspaces.

        Build a request to set the minimum number of Runspaces the pool
        maintains. The `min_runspaces` property is updated once the
        `:class:SetMinRunspacesEvent` is fired.

        Args:
            value: The minimum number of runspaces in a pool to change to.
        """
        if self.state == RunspacePoolState.BeforeOpen or self._min_runspaces == value:
            self._min_runspaces = value
            return

        ci = self._ci_counter
        self._ci_table[ci] = lambda e: setattr(self, "_min_runspaces", value)
        self.prepare_message(SetMinRunspaces(MinRunspaces=value, ci=ci))

        return ci

    def _process_ApplicationPrivateData(
        self,
        event: ApplicationPrivateDataEvent,
    ):
        self.application_private_data = event.ps_object.ApplicationPrivateData

    def _process_DebugRecord(
        self,
        event: DebugRecordEvent,
    ):
        pass

    def _process_EncryptedSessionKey(
        self,
        event: EncryptedSessionKeyEvent,
    ):
        encrypted_session_key = base64.b64decode(event.ps_object.EncryptedSessionKey)
        session_key = decrypt_session_key(self._exchange_key, encrypted_session_key)
        self._cipher = PSRemotingCrypto(session_key)

    def _process_ErrorRecord(
        self,
        event: ErrorRecordEvent,
    ):
        pass

    def _process_InformationRecord(
        self,
        event: InformationRecordEvent,
    ):
        pass

    def _process_PipelineHostCall(
        self,
        event: PipelineHostCallEvent,
    ):
        # Store the event for the host response to use.
        self._ci_table[event.ps_object.ci] = event

    def _process_PipelineOutput(
        self,
        event: PipelineOutputEvent,
    ):
        pass

    def _process_PipelineState(
        self,
        event: PipelineStateEvent,
    ):
        pipeline = self.pipeline_table[event.pipeline_id]
        pipeline.state = event.state

        if event.state in [PSInvocationState.Completed, PSInvocationState.Stopped]:
            del self.pipeline_table[event.pipeline_id]

    def _process_ProgressRecord(
        self,
        event: ProgressRecordEvent,
    ):
        pass

    def _process_PublicKeyRequest(
        self,
        event: PublicKeyRequestEvent,
    ):
        self.exchange_key()

    def _process_RunspaceAvailability(
        self,
        event: RunspaceAvailabilityEvent,
    ):
        handler = self._ci_table.pop(int(event.ps_object.ci))
        if handler is not None:
            handler(event)

    def _process_RunspacePoolHostCall(
        self,
        event: RunspacePoolHostCallEvent,
    ):
        # Store the event for the host response to use.
        self._ci_table[int(event.ps_object.ci)] = event

    def _process_RunspacePoolInitData(
        self,
        event: RunspacePoolInitDataEvent,
    ):
        self._min_runspaces = event.ps_object.MinRunspaces
        self._max_runspaces = event.ps_object.MaxRunspaces

    def _process_RunspacePoolState(
        self,
        event: RunspacePoolStateEvent,
    ):
        self.state = event.state

    def _process_UserEvent(
        self,
        event: UserEventEvent,
    ):
        pass

    def _process_VerboseRecord(
        self,
        event: VerboseRecordEvent,
    ):
        pass

    def _process_WarningRecord(
        self,
        event: WarningRecordEvent,
    ):
        pass


class ServerRunspacePool(_RunspacePoolBase):
    def __init__(
        self,
        application_private_data: typing.Optional[typing.Dict] = None,
    ):
        super().__init__(
            EMPTY_UUID,
            capability=_DEFAULT_CAPABILITY,
            application_arguments={},
            application_private_data=application_private_data or {},
        )

    def format_event(
        self,
        event_identifier: typing.Union[PSInt, int],
        source_identifier: typing.Union[PSString, str],
        sender: typing.Any = None,
        source_args: typing.Optional[typing.List[typing.Any]] = None,
        message_data: typing.Any = None,
        time_generated: typing.Optional[typing.Union[PSDateTime, datetime.datetime]] = None,
        computer: typing.Optional[typing.Union[PSString, str]] = None,
    ):
        """Send event to client.

        Sends an event to the client Runspace Pool.

        Args:
            event_identifier: Unique identifier of this event.
            source_identifier: Identifier associated with the source of this
                event.
            sender: Object that generated this event.
            source_args: List of arguments captured by the original event
                source.
            message_data: Additional user data associated with this event.
            time_generated: Time and date that this event was generated,
                defaults to now.
            computer: The name of the computer on which this event was
                generated, defaults to the current computer.
        """
        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("generate Runspace Pool event", self.state, [RunspacePoolState.Opened])

        time_generated = PSDateTime.now() if time_generated is None else time_generated
        computer = platform.node() if computer is None else computer

        self.prepare_message(
            UserEvent(
                EventIdentifier=PSInt(event_identifier),
                SourceIdentifier=PSString(source_identifier),
                TimeGenerated=time_generated,
                Sender=sender,
                SourceArgs=source_args or [],
                MessageData=message_data,
                ComputerName=computer,
                RunspaceId=self.runspace_id,
            )
        )

    def host_call(
        self,
        method: HostMethodIdentifier,
        parameters: typing.Optional[typing.List] = None,
        pipeline_id: typing.Optional[uuid.UUID] = None,
    ) -> int:
        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("create host call", self.state, [RunspacePoolState.Opened])

        ci = self._ci_counter

        call_type = PipelineHostCall if pipeline_id else RunspacePoolHostCall
        call = call_type(
            ci=ci,
            mi=method,
            mp=parameters,
        )
        self.prepare_message(call, pipeline_id=pipeline_id, stream_type=StreamType.prompt_response)

        return ci

    def request_key(self):
        if self._cipher:
            return

        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("request exchange key", self.state, [RunspacePoolState.Opened])

        self.prepare_message(PublicKeyRequest())

    def _process_ConnectRunspacePool(
        self,
        event: ConnectRunspacePoolEvent,
    ):
        # TODO: Handle <S></S> ConnectRunspacePool object
        self._max_runspaces = event.ps_object.MaxRunspaces
        self._min_runspaces = event.ps_object.MinRunspaces

        self.prepare_message(
            RunspacePoolInitData(
                MinRunspaces=self.min_runspaces,
                MaxRunspaces=self.max_runspaces,
            )
        )

        self.prepare_message(ApplicationPrivateData(ApplicationPrivateData=self.application_private_data))

    def _process_CreatePipeline(
        self,
        event: CreatePipelineEvent,
    ):
        create_pipeline = event.ps_object
        powershell = create_pipeline.PowerShell

        pipeline = ServerPowerShell(
            runspace_pool=self,
            pipeline_id=event.pipeline_id,
            add_to_history=create_pipeline.AddToHistory,
            apartment_state=create_pipeline.ApartmentState,
            history=powershell.History,
            host=HostInfo.from_psobject(create_pipeline.HostInfo),
            is_nested=create_pipeline.IsNested,
            no_input=create_pipeline.NoInput,
            remote_stream_options=create_pipeline.RemoteStreamOptions,
            redirect_shell_error_to_out=powershell.RedirectShellErrorOutputPipe,
        )
        commands = [powershell.Cmds]
        commands.extend([c.Cmds for c in getattr(powershell, "ExtraCmds", [])])

        for statements in commands:
            for raw_cmd in statements:
                cmd = Command.from_psobject(raw_cmd)
                pipeline.commands.append(cmd)

            pipeline.commands[-1].end_of_statement = True

        event.pipeline = pipeline

    def _process_EndOfPipelineInput(
        self,
        event: EndOfPipelineInputEvent,
    ):
        pass

    def _process_GetAvailableRunspaces(
        self,
        event: GetAvailableRunspacesEvent,
    ):
        # TODO: This should reflect the available runspaces and not the max.
        self.prepare_message(
            RunspaceAvailability(
                SetMinMaxRunspacesResponse=self.max_runspaces,
                ci=event.ps_object.ci,
            )
        )

    def _process_GetCommandMetadata(
        self,
        event: GetCommandMetadataEvent,
    ):
        get_meta = event.ps_object
        pipeline = ServerGetCommandMetadata(
            runspace_pool=self,
            pipeline_id=event.pipeline_id,
            name=get_meta.Name,
            command_type=get_meta.CommandType,
            namespace=get_meta.Namespace,
            arguments=get_meta.ArgumentList,
        )
        event.pipeline = pipeline

    def _process_InitRunspacePool(
        self,
        event: InitRunspacePoolEvent,
    ):
        self.apartment_state = event.ps_object.ApartmentState
        self.application_arguments = event.ps_object.ApplicationArguments
        self.host = event.ps_object.HostInfo
        self.thread_options = event.ps_object.PSThreadOptions
        self._max_runspaces = event.ps_object.MaxRunspaces
        self._min_runspaces = event.ps_object.MinRunspaces

        self.prepare_message(ApplicationPrivateData(ApplicationPrivateData=self.application_private_data))
        self.state = RunspacePoolState.Opened
        self.prepare_message(RunspacePoolStateMsg(RunspaceState=int(self.state)))

    def _process_PipelineHostResponse(
        self,
        event: PipelineHostResponseEvent,
    ):
        pass

    def _process_PipelineInput(
        self,
        event: PipelineInputEvent,
    ):
        pass

    def _process_PublicKey(
        self,
        event: PublicKeyEvent,
    ):
        session_key = os.urandom(32)
        self._cipher = PSRemotingCrypto(session_key)

        exchange_key = base64.b64decode(event.ps_object.PublicKey)
        encrypted_session_key = encrypt_session_key(exchange_key, session_key)

        msg = EncryptedSessionKey(
            EncryptedSessionKey=base64.b64encode(encrypted_session_key).decode(),
        )
        self.prepare_message(msg)

    def _process_ResetRunspaceState(
        self,
        event: ResetRunspaceStateEvent,
    ):
        pass

    def _process_RunspacePoolHostResponse(
        self,
        event: RunspacePoolHostResponseEvent,
    ):
        pass

    def _process_SessionCapability(
        self,
        event: SessionCapabilityEvent,
    ):
        super()._process_SessionCapability(event)
        self.prepare_message(self.our_capability)
        self.runspace_id = event.runspace_pool_id

    def _process_SetMaxRunspaces(
        self,
        event: SetMaxRunspacesEvent,
    ):
        self._max_runspaces = event.ps_object.MaxRunspaces
        self.prepare_message(
            RunspaceAvailability(
                SetMinMaxRunspacesResponse=True,
                ci=event.ps_object.ci,
            )
        )

    def _process_SetMinRunspaces(
        self,
        event: SetMinRunspacesEvent,
    ):
        self._min_runspaces = event.ps_object.MinRunspaces
        self.prepare_message(
            RunspaceAvailability(
                SetMinMaxRunspacesResponse=True,
                ci=event.ps_object.ci,
            )
        )


RunspacePoolType = typing.TypeVar("RunspacePoolType", bound=_RunspacePoolBase)
