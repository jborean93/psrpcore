# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import base64
import functools
import typing
import uuid

from psrpcore._base import Pipeline, RunspacePool
from psrpcore._command import Command
from psrpcore._crypto import create_keypair, decrypt_session_key, rsa
from psrpcore._events import (
    ApplicationPrivateDataEvent,
    DebugRecordEvent,
    EncryptedSessionKeyEvent,
    ErrorRecordEvent,
    InformationRecordEvent,
    PipelineHostCallEvent,
    PipelineHostResponseEvent,
    PipelineOutputEvent,
    PipelineStateEvent,
    ProgressRecordEvent,
    PublicKeyRequestEvent,
    RunspaceAvailabilityEvent,
    RunspacePoolHostCallEvent,
    RunspacePoolHostResponseEvent,
    RunspacePoolInitDataEvent,
    RunspacePoolStateEvent,
    SetRunspaceAvailabilityEvent,
    UserEventEvent,
    VerboseRecordEvent,
    WarningRecordEvent,
)
from psrpcore._exceptions import (
    InvalidPipelineState,
    InvalidProtocolVersion,
    InvalidRunspacePoolState,
)
from psrpcore._payload import ProtocolVersion, StreamType
from psrpcore._pipeline import GetMetadata, PowerShell
from psrpcore.types import (
    ApartmentState,
    CommandTypes,
    ConnectRunspacePool,
    EndOfPipelineInput,
    ErrorRecord,
    GetAvailableRunspaces,
    HostInfo,
    InitRunspacePool,
    PipelineHostResponse,
    PSInvocationState,
    PSRPMessageType,
    PSThreadOptions,
    PublicKey,
    RemoteStreamOptions,
    ResetRunspaceState,
    RunspacePoolHostResponse,
    RunspacePoolState,
    SetMaxRunspaces,
    SetMinRunspaces,
)


class ClientRunspacePool(RunspacePool["_ClientPipeline"]):
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
        application_arguments: typing.Optional[typing.Dict[str, typing.Any]] = None,
        apartment_state: ApartmentState = ApartmentState.Unknown,
        host: typing.Optional[HostInfo] = None,
        thread_options: PSThreadOptions = PSThreadOptions.Default,
        min_runspaces: int = 1,
        max_runspaces: int = 1,
        runspace_pool_id: typing.Optional[uuid.UUID] = None,
    ) -> None:
        super().__init__(
            runspace_pool_id or uuid.uuid4(),
            application_arguments=application_arguments or {},
            application_private_data={},
        )
        self.apartment_state = apartment_state
        self.host = host
        self.thread_options = thread_options
        self._min_runspaces = min_runspaces
        self._max_runspaces = max_runspaces
        self._exchange_key: typing.Optional[rsa.RSAPrivateKey] = None

    def open(self) -> None:
        """Opens the Runspace Pool.

        This opens the Runspace Pool on the peer.
        """
        if self.state == RunspacePoolState.Opened:
            return
        if self.state != RunspacePoolState.BeforeOpen:
            raise InvalidRunspacePoolState("open a Runspace Pool", self.state, [RunspacePoolState.BeforeOpen])

        host = self.host or HostInfo()
        self._change_state(RunspacePoolState.Opening)

        self.prepare_message(self.our_capability)
        self.prepare_message(
            InitRunspacePool(
                MinRunspaces=self._min_runspaces,
                MaxRunspaces=self._max_runspaces,
                PSThreadOptions=self.thread_options,
                ApartmentState=self.apartment_state,
                HostInfo=host,
                ApplicationArguments=self.application_arguments,
            )
        )

    def connect(self) -> None:
        """Connects to the Runspace Pool.

        This connects to a disconnected Runspace Pool on the peer.
        """
        if self.state == RunspacePoolState.Opened:
            return
        if self.state != RunspacePoolState.BeforeOpen and self.state != RunspacePoolState.Disconnected:
            raise InvalidRunspacePoolState("connect to Runspace Pool", self.state, [RunspacePoolState.BeforeOpen])

        self._change_state(RunspacePoolState.Connecting)
        self.prepare_message(self.our_capability)
        self.prepare_message(ConnectRunspacePool())

    def get_available_runspaces(self) -> int:
        """Get the number of Runspaces available.

        This builds a request to get the number of available Runspaces in the
        pool. The :class:`psrpcore.GetRunspaceAvailabilityEvent` event is
        returned once the response is received from the server.

        Returns:
            int: The command id for this request.
        """
        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("get available Runspaces", self.state, [RunspacePoolState.Opened])

        ci = self._ci_counter
        self._ci_handlers[ci] = None
        self.prepare_message(GetAvailableRunspaces(ci=ci))

        return ci

    def exchange_key(self) -> None:
        """Exchange session specific key.

        Request the session key from the peer.
        """
        if self._key_requested:
            return

        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("start session key exchange", self.state, [RunspacePoolState.Opened])

        self._exchange_key, public_key = create_keypair()
        b64_public_key = base64.b64encode(public_key).decode()

        self.prepare_message(PublicKey(PublicKey=b64_public_key))
        self._key_requested = True

    def host_response(
        self,
        ci: int,
        return_value: typing.Optional[typing.Any] = None,
        error_record: typing.Optional[ErrorRecord] = None,
    ) -> None:
        """Respond to a host call.

        Respond to a host call event with either a return value or an error
        record. It is recommended to use :class:`psrpcore.ClientHostResponder`
        to respond to host calls as it will format the return values from a
        .NET type

        Args:
            ci: The call ID associated with the host call to response to.
            return_value: The return value for the host call.
            error_record: The error record raised by the host when running the
                host call.
        """
        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("respond to host call", self.state, [RunspacePoolState.Opened])

        call_event = typing.cast(
            typing.Union[RunspacePoolHostResponseEvent, PipelineHostResponseEvent], self._ci_events[ci]
        )
        method_identifier = call_event.method_identifier
        pipeline_id = call_event.pipeline_id

        host_call_obj = PipelineHostResponse if pipeline_id else RunspacePoolHostResponse

        host_call = host_call_obj(ci=ci, mi=method_identifier)
        if return_value is not None:
            host_call.mr = return_value

        if error_record is not None:
            host_call.me = error_record

        self.prepare_message(host_call, pipeline_id=pipeline_id, stream_type=StreamType.prompt_response)

        # Any of the above may fail causing the ci record to be dropped.
        # Instead only remove it once a response has been serialized and is
        # ready to send.
        del self._ci_events[ci]

    def reset_runspace_state(self) -> int:
        """Reset the Runspace Pool state.

        Resets the variable table for the Runspace Pool back to the default
        state. This requires the server to be running with PowerShell v5 or
        newer. Older versions will fail with :class:`InvalidProtocolVersion`.

        Returns:
            int: The command id for this request.
        """
        their_version = getattr(self.their_capability, "protocolversion", ProtocolVersion.Win7RC.value)
        required_version = ProtocolVersion.Pwsh5.value
        if their_version < required_version:
            raise InvalidProtocolVersion("reset Runspace Pool state", their_version, required_version)

        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("reset Runspace Pool state", self.state, [RunspacePoolState.Opened])

        ci = self._ci_counter
        self._ci_handlers[ci] = None
        self.prepare_message(ResetRunspaceState(ci=ci))

        return ci

    def set_max_runspaces(
        self,
        value: int,
    ) -> typing.Optional[int]:
        """Set the maximum number of runspaces.

        Build a request to set the maximum number of Runspaces the pool
        maintains. The `max_runspaces` property is updated once the
        :class:`SetMaxRunspacesEvent` is received.

        Args:
            value: The maximum number of runspaces in a pool to change to.

        Returns:
            Optional[int]: The command id for this request or ``None`` if no
                request was created.
        """
        if self.state == RunspacePoolState.BeforeOpen or self._max_runspaces == value:
            self._max_runspaces = value
            return None

        ci = self._ci_counter
        self._ci_handlers[ci] = functools.partial(self._set_runspaces_handler, "max", value)
        self.prepare_message(SetMaxRunspaces(MaxRunspaces=value, ci=ci))

        return ci

    def set_min_runspaces(
        self,
        value: int,
    ) -> typing.Optional[int]:
        """Set the minimum number of runspaces.

        Build a request to set the minimum number of Runspaces the pool
        maintains. The `min_runspaces` property is updated once the
        :class:`SetMinRunspacesEvent` is fired.

        Args:
            value: The minimum number of runspaces in a pool to change to.

        Returns:
            Optional[int]: The command id for this request or ``None`` if no
                request was created.
        """
        if self.state == RunspacePoolState.BeforeOpen or self._min_runspaces == value:
            self._min_runspaces = value
            return None

        ci = self._ci_counter
        self._ci_handlers[ci] = functools.partial(self._set_runspaces_handler, "min", value)
        self.prepare_message(SetMinRunspaces(MinRunspaces=value, ci=ci))

        return ci

    def _process_ApplicationPrivateData(
        self,
        event: ApplicationPrivateDataEvent,
    ) -> None:
        self.application_private_data = event.data
        if self.state == RunspacePoolState.Connecting:
            self._change_state(RunspacePoolState.Opened)

    def _process_DebugRecord(
        self,
        event: DebugRecordEvent,
    ) -> None:
        pass

    def _process_EncryptedSessionKey(
        self,
        event: EncryptedSessionKeyEvent,
    ) -> None:
        session_key = decrypt_session_key(
            self._exchange_key,  # type: ignore[arg-type] # Before we get this message the exchange_key is set
            event.key,
        )
        self._cipher.register_key(session_key)

    def _process_ErrorRecord(
        self,
        event: ErrorRecordEvent,
    ) -> None:
        pass

    def _process_InformationRecord(
        self,
        event: InformationRecordEvent,
    ) -> None:
        pass

    def _process_PipelineHostCall(
        self,
        event: PipelineHostCallEvent,
    ) -> None:
        if event.ci != -100:  # Used by pwsh to indicate this is a void method
            self._ci_events[event.ci] = event

    def _process_PipelineOutput(
        self,
        event: PipelineOutputEvent,
    ) -> None:
        pass

    def _process_PipelineState(
        self,
        event: PipelineStateEvent,
    ) -> None:
        pipeline_id = event.pipeline_id
        pipeline = self.pipeline_table[pipeline_id]
        pipeline.state = event.state

    def _process_ProgressRecord(
        self,
        event: ProgressRecordEvent,
    ) -> None:
        pass

    def _process_PublicKeyRequest(
        self,
        event: PublicKeyRequestEvent,
    ) -> None:
        self.exchange_key()

    def _process_RunspaceAvailability(
        self,
        event: RunspaceAvailabilityEvent,
    ) -> None:
        handler = self._ci_handlers.pop(event.ci)
        if handler is not None:
            handler(event)

    def _process_RunspacePoolHostCall(
        self,
        event: RunspacePoolHostCallEvent,
    ) -> None:
        if event.ci != -100:  # Used by pwsh to indicate this is a void method
            self._ci_events[event.ci] = event

    def _process_RunspacePoolInitData(
        self,
        event: RunspacePoolInitDataEvent,
    ) -> None:
        self._min_runspaces = event.min_runspaces
        self._max_runspaces = event.max_runspaces

    def _process_RunspacePoolState(
        self,
        event: RunspacePoolStateEvent,
    ) -> None:
        self._change_state(event.state)

    def _process_UserEvent(
        self,
        event: UserEventEvent,
    ) -> None:
        pass

    def _process_VerboseRecord(
        self,
        event: VerboseRecordEvent,
    ) -> None:
        pass

    def _process_WarningRecord(
        self,
        event: WarningRecordEvent,
    ) -> None:
        pass

    def _set_runspaces_handler(
        self,
        field: str,
        value: int,
        event: SetRunspaceAvailabilityEvent,
    ) -> None:
        """Changes the runspace count based on the result."""
        if event.success:
            setattr(self, f"_{field}_runspaces", value)


class _ClientPipeline(Pipeline["ClientRunspacePool"]):
    """Client Pipeline.

    Represents a client pipeline and the various methods that can be used to
    communicate with the server pipeline. Any data generated by this pipeline
    is retrieved through the Runspace Pool is is a member off.
    """

    def __init__(
        self,
        runspace_pool: "ClientRunspacePool",
        pipeline_id: typing.Optional[uuid.UUID] = None,
    ) -> None:
        super().__init__(runspace_pool, pipeline_id or uuid.uuid4())
        self._message_type: typing.Optional[PSRPMessageType] = None

    def start(self) -> None:
        """Invokes the pipeline.

        Starts the pipeline on the server. This creates the request to create
        and queue the pipeline on the server.
        """
        valid_states = [PSInvocationState.NotStarted, PSInvocationState.Stopped, PSInvocationState.Completed]
        if self.state not in valid_states:
            raise InvalidPipelineState("start a pipeline", self.state, valid_states)

        self.prepare_message(self.metadata, message_type=self._message_type)
        self.state = PSInvocationState.Running

    def send(
        self,
        data: typing.Any,
    ) -> None:
        """Send data to the pipeline.

        Sends input data to a running pipeline.

        Args:
            data: The data to send to the pipeline.
        """
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("send pipeline input", self.state, [PSInvocationState.Running])

        self.prepare_message(data, message_type=PSRPMessageType.PipelineInput)

    def send_eof(self) -> None:
        """Send EOF to the input pipe.

        Sends the end of input marker to the pipeline to state no more input is
        expected for the pipeline.
        """
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("send pipeline input EOF", self.state, [PSInvocationState.Running])

        self.prepare_message(EndOfPipelineInput())

    def host_response(
        self,
        ci: int,
        return_value: typing.Optional[typing.Any] = None,
        error_record: typing.Optional[ErrorRecord] = None,
    ) -> None:
        """Respond to a host call.

        Respond to a host call event with either a return value or an error
        record.

        Args:
            ci: The call ID associated with the host call to response to.
            return_value: The return value for the host call.
            error_record: The error record raised by the host when running the
                host call.
        """
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("response to pipeline host call", self.state, [PSInvocationState.Running])

        self.runspace_pool.host_response(ci, return_value, error_record)


class ClientPowerShell(_ClientPipeline):
    """Client PowerShell Pipeline.

    A PowerShell pipeline to be used from the client. This is the main pipeline
    class used by the client to start a pipeline on the server.

    Args:
        runspace_pool: The Runspace Pool the pipeline is a member off.
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
        pipeline_id: Manually set the Pipeline ID, used when reconnecting to an
            existing Pipeline.
    """

    def __init__(
        self,
        runspace_pool: "ClientRunspacePool",
        add_to_history: bool = False,
        apartment_state: ApartmentState = None,
        history: typing.Optional[str] = None,
        host: typing.Optional[HostInfo] = None,
        is_nested: bool = False,
        no_input: bool = True,
        remote_stream_options: RemoteStreamOptions = RemoteStreamOptions.none,
        redirect_shell_error_to_out: bool = True,
        pipeline_id: typing.Optional[uuid.UUID] = None,
    ) -> None:
        super().__init__(runspace_pool=runspace_pool, pipeline_id=pipeline_id)
        self.metadata: PowerShell = PowerShell(
            add_to_history=add_to_history,
            apartment_state=apartment_state or runspace_pool.apartment_state,
            history=history,
            host=host,
            is_nested=is_nested,
            no_input=no_input,
            remote_stream_options=remote_stream_options,
            redirect_shell_error_to_out=redirect_shell_error_to_out,
        )
        self._message_type = PSRPMessageType.CreatePipeline

    def add_argument(
        self,
        value: typing.Any,
    ) -> "ClientPowerShell":
        """Adds argument to the last command.

        Adds a positional argument to the last command in the pipeline.

        Args:
            value: The argument to add.

        Returns:
            ClientPowerShell: itself
        """
        return self.add_parameter(None, value)

    def add_command(
        self,
        cmdlet: typing.Union[str, Command],
        use_local_scope: typing.Optional[bool] = None,
    ) -> "ClientPowerShell":
        """Adds a command

        Adds a command to the current statement.

        Args:
            cmdlet: The command as a string or :class:`Command` object.
            use_local_scope: Whether the command is run under local scope or
                not.

        Returns:
            ClientPowerShell: itself
        """
        if isinstance(cmdlet, str):
            cmdlet = Command(cmdlet, use_local_scope=use_local_scope)

        elif use_local_scope is not None:
            raise TypeError("Cannot set use_local_scope with Command")

        self.metadata.commands.append(cmdlet)
        return self

    def add_parameter(
        self,
        name: typing.Optional[str],
        value: typing.Any = True,
    ) -> "ClientPowerShell":
        """Adds a parameter to the last command.

        Adds a parameter to the last command in the pipeline. A switch parameter
        can either have ``True``, ``False``, or ``None`` as the value with
        ``None`` being equivalent to ``False``.

        Args:
            name: The name of the parameter to add.
            value: The value to set for the parameter.

        Returns:
            ClientPowerShell: itself
        """
        commands = self.metadata.commands
        if not commands:
            raise ValueError(
                "A command is required to add a parameter/argument. A command must be added to the "
                "PowerShell instance first."
            )

        commands[-1].add_parameter(name, value)
        return self

    def add_parameters(
        self,
        **parameters: typing.Any,
    ) -> "ClientPowerShell":
        """Adds parameters to the last command.

        Like :meth:`ClientPowerShell.add_parameter` this adds multiple
        parameters to the last command in the pipeline. The key word arguments
        corresponds to the parameters to add.

        Args:
            parameters: The parameters to add as kwargs.

        Returns:
            ClientPowerShell: itself
        """
        for name, value in parameters.items():
            self.add_parameter(name, value)

        return self

    def add_script(
        self,
        script: str,
        use_local_scope: typing.Optional[bool] = None,
    ) -> "ClientPowerShell":
        """Adds a script.

        Adds a script to the current statement. A script is essentially a
        scriptblock containing the PowerShell code to execute.

        Args:
            script: The script to add.
            use_local_scope: Whether the command is run under local scope or
                not.

        Returns:
            ClientPowerShell: itself
        """
        return self.add_command(Command(script, True, use_local_scope=use_local_scope))

    def add_statement(self) -> "ClientPowerShell":
        """Adds a statement.

        Adds a statement to the pipeline. A statement can be used to separate
        multiple commands and scripts as separate statements rather than
        pipeline commands.

        Returns:
            ClientPowerShell: itself
        """
        commands = self.metadata.commands
        if commands:
            commands[-1].end_of_statement = True

        return self


class ClientGetCommandMetadata(_ClientPipeline):
    """Client Get Command Metadata Pipeline.

    A Get Command Metadata pipeline to be used from the client.

    Args:
        runspace_pool: The Runspace Pool the pipeline is a member off.
        name: List of command names to get the metadata for. Uses ``*`` as a
            wildcard.
        command_type: The type of commands to filter by.
        namespace: Wildcard patterns describbing the command namespace to filter
            by.
        arguments: Extra arguments passed to the higher-layer above PSRP.
        pipeline_id: Manually set the Pipeline ID, used when reconnecting to an
            existing Pipeline.
    """

    def __init__(
        self,
        runspace_pool: "ClientRunspacePool",
        name: typing.Union[str, typing.List[str]],
        command_type: CommandTypes = CommandTypes.All,
        namespace: typing.Optional[typing.List[str]] = None,
        arguments: typing.Optional[typing.List[typing.Any]] = None,
        pipeline_id: typing.Optional[uuid.UUID] = None,
    ) -> None:
        super().__init__(runspace_pool=runspace_pool, pipeline_id=pipeline_id)
        self.metadata: GetMetadata = GetMetadata(
            name=name,
            command_type=command_type,
            namespace=namespace,
            arguments=arguments,
        )
        self._message_type = PSRPMessageType.GetCommandMetadata
