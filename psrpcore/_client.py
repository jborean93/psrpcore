# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import base64
import typing
import uuid

from psrpcore._base import (
    GetCommandMetadataPipeline,
    Pipeline,
    PowerShellPipeline,
    RunspacePool,
)
from psrpcore._command import Command
from psrpcore._crypto import PSRemotingCrypto, create_keypair, decrypt_session_key
from psrpcore._events import (
    ApplicationPrivateDataEvent,
    DebugRecordEvent,
    EncryptedSessionKeyEvent,
    ErrorRecordEvent,
    InformationRecordEvent,
    PipelineHostCallEvent,
    PipelineOutputEvent,
    PipelineStateEvent,
    ProgressRecordEvent,
    PublicKeyRequestEvent,
    RunspaceAvailabilityEvent,
    RunspacePoolHostCallEvent,
    RunspacePoolInitDataEvent,
    RunspacePoolStateEvent,
    UserEventEvent,
    VerboseRecordEvent,
    WarningRecordEvent,
)
from psrpcore._exceptions import (
    InvalidPipelineState,
    InvalidProtocolVersion,
    InvalidRunspacePoolState,
    PSRPCoreError,
)
from psrpcore._payload import EMPTY_UUID, StreamType
from psrpcore.types import (
    ApartmentState,
    ConnectRunspacePool,
    EndOfPipelineInput,
    ErrorRecord,
    GetAvailableRunspaces,
    HostInfo,
    InitRunspacePool,
    PipelineHostResponse,
    PSInvocationState,
    PSObject,
    PSRPMessageType,
    PSThreadOptions,
    PSVersion,
    PublicKey,
    ResetRunspaceState,
    RunspacePoolHostResponse,
    RunspacePoolState,
    SessionCapability,
    SetMaxRunspaces,
    SetMinRunspaces,
)

_DEFAULT_CAPABILITY = SessionCapability(
    PSVersion=PSVersion("2.0"),
    protocolversion=PSVersion("2.3"),
    SerializationVersion=PSVersion("1.1.0.1"),
)


class ClientRunspacePool(RunspacePool):
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
            capability=_DEFAULT_CAPABILITY,
            application_arguments=application_arguments or {},
            application_private_data={},
        )
        self.apartment_state = apartment_state
        self.host = host
        self.thread_options = thread_options
        self._min_runspaces = min_runspaces
        self._max_runspaces = max_runspaces

    def connect(self) -> None:
        if self.state == RunspacePoolState.Opened:
            return
        if self.state != RunspacePoolState.Disconnected:
            raise InvalidRunspacePoolState("connect to Runspace Pool", self.state, [RunspacePoolState.Disconnected])

        self.state = RunspacePoolState.Connecting

        self.prepare_message(self.our_capability)
        self.prepare_message(ConnectRunspacePool())

    def close(self) -> None:
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
        self._ci_handlers[ci] = None
        self.prepare_message(GetAvailableRunspaces(ci=ci))

        return ci

    def open(self) -> None:
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

    def exchange_key(self) -> None:
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
        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("response to host call", self.state, [RunspacePoolState.Opened])

        call_event = self._ci_events.pop(ci)

        method_identifier = call_event.ps_object.mi
        pipeline_id = call_event.pipeline_id

        host_call_obj = PipelineHostResponse if pipeline_id else RunspacePoolHostResponse

        host_call = host_call_obj(ci=ci, mi=method_identifier)
        if return_value is not None:
            host_call.mr = return_value

        if error_record is not None:
            host_call.me = error_record

        self.prepare_message(host_call, pipeline_id=pipeline_id, stream_type=StreamType.prompt_response)

    def reset_runspace_state(self) -> typing.Optional[int]:
        """Reset the Runspace Pool state.

        Resets the variable table for the Runspace Pool back to the default
        state.
        """
        their_version = getattr(self.their_capability, "protocolversion", PSVersion("2.0"))
        required_version = PSVersion("2.3")
        if their_version < required_version:
            raise InvalidProtocolVersion("reset Runspace Pool state", their_version, required_version)
        if self.state == RunspacePoolState.BeforeOpen:
            return None
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
        `:class:SetMaxRunspacesEvent` is fired.

        Args:
            value: The maximum number of runspaces in a pool to change to.
        """
        if self.state == RunspacePoolState.BeforeOpen or self._max_runspaces == value:
            self._max_runspaces = value
            return None

        ci = self._ci_counter
        self._ci_handlers[ci] = lambda e: setattr(self, "_max_runspaces", value)
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
            return None

        ci = self._ci_counter
        self._ci_handlers[ci] = lambda e: setattr(self, "_min_runspaces", value)
        self.prepare_message(SetMinRunspaces(MinRunspaces=value, ci=ci))

        return ci

    def _process_ApplicationPrivateData(
        self,
        event: ApplicationPrivateDataEvent,
    ) -> None:
        self.application_private_data = event.ps_object.ApplicationPrivateData

    def _process_DebugRecord(
        self,
        event: DebugRecordEvent,
    ) -> None:
        pass

    def _process_EncryptedSessionKey(
        self,
        event: EncryptedSessionKeyEvent,
    ) -> None:
        encrypted_session_key = base64.b64decode(event.ps_object.EncryptedSessionKey)
        session_key = decrypt_session_key(
            self._exchange_key,  # type: ignore[arg-type] # Before we get this message the exchange_key is set
            encrypted_session_key,
        )
        self._cipher = PSRemotingCrypto(session_key)

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
        # Store the event for the host response to use.
        self._ci_events[event.ps_object.ci] = event

    def _process_PipelineOutput(
        self,
        event: PipelineOutputEvent,
    ) -> None:
        pass

    def _process_PipelineState(
        self,
        event: PipelineStateEvent,
    ) -> None:
        # We can ensure a PipelineState will have a pipeline_id
        pipeline_id = event.pipeline_id
        pipeline = self.pipeline_table[pipeline_id]
        pipeline.state = event.state

        if event.state in [PSInvocationState.Completed, PSInvocationState.Stopped]:
            del self.pipeline_table[pipeline_id]

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
        handler = self._ci_handlers.pop(int(event.ps_object.ci))
        if handler is not None:
            handler(event)

    def _process_RunspacePoolHostCall(
        self,
        event: RunspacePoolHostCallEvent,
    ) -> None:
        # Store the event for the host response to use.
        self._ci_events[int(event.ps_object.ci)] = event

    def _process_RunspacePoolInitData(
        self,
        event: RunspacePoolInitDataEvent,
    ) -> None:
        self._min_runspaces = event.ps_object.MinRunspaces
        self._max_runspaces = event.ps_object.MaxRunspaces

    def _process_RunspacePoolState(
        self,
        event: RunspacePoolStateEvent,
    ) -> None:
        self.state = event.state

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


class _ClientPipeline(Pipeline["ClientRunspacePool"]):
    def __init__(
        self,
        runspace_pool: "ClientRunspacePool",
    ) -> None:
        super().__init__(runspace_pool, uuid.uuid4())

    def invoke(self) -> None:
        self.prepare_message(self.to_psobject())
        self.state = PSInvocationState.Running

    def send(
        self,
        data: typing.Any,
    ) -> None:
        self.prepare_message(data, message_type=PSRPMessageType.PipelineInput)

    def send_end(self) -> None:
        self.prepare_message(EndOfPipelineInput())

    def host_response(
        self,
        ci: int,
        return_value: typing.Optional[typing.Any] = None,
        error_record: typing.Optional[ErrorRecord] = None,
    ) -> None:
        """Respond to a host call.

        Respond to a host call event with either a return value or an error record.

        Args:
            ci: The call ID associated with the host call to response to.
            return_value: The return value for the host call.
            error_record: The error record raised by the host when running the host call.
        """
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("response to pipeline host call", self.state, [PSInvocationState.Running])

        self.runspace_pool.host_response(ci, return_value, error_record)


class ClientPowerShell(PowerShellPipeline, _ClientPipeline):
    def __init__(
        self,
        runspace_pool: "ClientRunspacePool",
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(runspace_pool=runspace_pool, *args, **kwargs)

    def add_argument(
        self,
        value: typing.Any,
    ) -> "ClientPowerShell":
        return self.add_parameter(None, value)

    def add_command(
        self,
        cmdlet: typing.Union[str, Command],
        use_local_scope: typing.Optional[bool] = None,
    ) -> "ClientPowerShell":
        if isinstance(cmdlet, str):
            cmdlet = Command(cmdlet, use_local_scope=use_local_scope)

        elif use_local_scope is not None:
            raise TypeError("Cannot set use_local_scope with Command")

        self.commands.append(cmdlet)
        return self

    def add_parameter(
        self,
        name: typing.Optional[str],
        value: typing.Any = None,
    ) -> "ClientPowerShell":
        if not self.commands:
            raise ValueError(
                "A command is required to add a parameter/argument. A command must be added to the "
                "PowerShell instance first."
            )

        self.commands[-1].add_parameter(name, value)
        return self

    def add_parameters(
        self,
        parameters: typing.Dict[str, typing.Any],
    ) -> "ClientPowerShell":
        for name, value in parameters.items():
            self.add_parameter(name, value)

        return self

    def add_script(
        self,
        script: str,
        use_local_scope: typing.Optional[bool] = None,
    ) -> "ClientPowerShell":
        return self.add_command(Command(script, True, use_local_scope=use_local_scope))

    def add_statement(self) -> "ClientPowerShell":
        if self.commands:
            self.commands[-1].end_of_statement = True

        return self


class ClientGetCommandMetadata(GetCommandMetadataPipeline, _ClientPipeline):
    def __init__(
        self,
        runspace_pool: "ClientRunspacePool",
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(runspace_pool=runspace_pool, *args, **kwargs)
