# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import base64
import datetime
import getpass
import os
import platform
import threading
import typing
import uuid

from psrpcore._base import Pipeline, RunspacePool
from psrpcore._crypto import encrypt_session_key
from psrpcore._events import (
    ConnectRunspacePoolEvent,
    CreatePipelineEvent,
    EndOfPipelineInputEvent,
    GetAvailableRunspacesEvent,
    GetCommandMetadataEvent,
    InitRunspacePoolEvent,
    PipelineHostResponseEvent,
    PipelineInputEvent,
    PublicKeyEvent,
    ResetRunspaceStateEvent,
    RunspacePoolHostResponseEvent,
    SessionCapabilityEvent,
    SetMaxRunspacesEvent,
    SetMinRunspacesEvent,
)
from psrpcore._exceptions import (
    InvalidPipelineState,
    InvalidProtocolVersion,
    InvalidRunspacePoolState,
    PSRPCoreError,
)
from psrpcore._payload import EMPTY_UUID, ProtocolVersion, PSRPPayload, StreamType
from psrpcore.types import (
    ApplicationPrivateData,
    DebugRecord,
    EncryptedSessionKey,
    ErrorCategory,
    ErrorCategoryInfo,
    ErrorDetails,
    ErrorRecord,
    HostMethodIdentifier,
    InformationRecordMsg,
    InvocationInfo,
    NETException,
    PipelineHostCall,
    PipelineState,
    ProgressRecordMsg,
    ProgressRecordType,
    PSDateTime,
    PSInvocationState,
    PSRPMessageType,
    PublicKeyRequest,
    RunspaceAvailability,
    RunspacePoolHostCall,
    RunspacePoolInitData,
    RunspacePoolState,
    RunspacePoolStateMsg,
    UserEvent,
    VerboseRecord,
    WarningRecord,
)


class ServerRunspacePool(RunspacePool["ServerPipeline"]):
    """Server Runspace Pool.

    Represents a Runspace Pool from a server context.

    Args:
        application_private_data: Any data about the server which is sent to the
            client during negotiation.
    """

    def __init__(
        self,
        application_private_data: typing.Optional[typing.Dict] = None,
    ) -> None:
        super().__init__(
            EMPTY_UUID,
            application_arguments={},
            application_private_data=application_private_data or {},
        )

        # Pwsh uses the app private data in some places to determine what the remote protocol is. This isn't consistent
        # but happens enough that defaults should be set for these fields.
        ps_version = self.application_private_data.setdefault("PSVersionTable", {})
        if isinstance(ps_version, dict):
            ps_version.setdefault("PSRemotingProtocolVersion", self.our_capability.protocolversion)
            ps_version.setdefault("SerializationVersion", self.our_capability.SerializationVersion)

        self._is_client = False
        self._session_key = os.urandom(32)
        self._cipher.register_key(self._session_key)

    def connect(self) -> None:
        """Marks the pool as connected.

        This marks the pool as connected from a disconnected state. Generates
        the :class:`psrpcore.types.RunspacePoolStateMsg` that can be sent to the
        client.
        """
        if self.state == RunspacePoolState.Opened:
            return
        if self.state != RunspacePoolState.Disconnected:
            raise InvalidRunspacePoolState(
                "accept Runspace Pool connections", self.state, [RunspacePoolState.Disconnected]
            )

        # The incoming messages will be from a blank runspace pool so start back at 1
        # TODO: Verify there are no incoming fragments/messages not processed.
        self._ci_count = 1
        self._fragment_count = 1
        self._change_state(RunspacePoolState.Connecting)

    def send_event(
        self,
        event_identifier: int,
        source_identifier: str,
        sender: typing.Any = None,
        source_args: typing.Optional[typing.List[typing.Any]] = None,
        message_data: typing.Any = None,
        time_generated: typing.Optional[datetime.datetime] = None,
        computer: typing.Optional[str] = None,
    ) -> None:
        """Send event to client.

        Sends an event to the client Runspace Pool. Generates a
        :class:`psrpcore.types.UserEvent` message to be sent to the client.

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
            raise InvalidRunspacePoolState("generate a Runspace Pool event", self.state, [RunspacePoolState.Opened])

        time_generated = PSDateTime.now() if time_generated is None else time_generated
        computer = platform.node() if computer is None else computer

        self.prepare_message(
            UserEvent(
                EventIdentifier=event_identifier,
                SourceIdentifier=source_identifier,
                TimeGenerated=time_generated,
                Sender=sender,
                SourceArgs=source_args or [],
                MessageData=message_data,
                ComputerName=computer,
                RunspaceId=self.runspace_pool_id,
            )
        )

    def set_broken(
        self,
        error: ErrorRecord,
    ) -> None:
        """Mark pool as broken.

        Marks the Runspace Pool as broken and states the reason why. Generates
        the :class:`psrpcore.types.RunspacePoolStateMsg` that can be sent to the
        client.

        Args:
            error: The error record explaining why the pool is broken.
        """
        valid_states = [RunspacePoolState.Broken, RunspacePoolState.Opened]
        if self.state not in valid_states:
            raise InvalidRunspacePoolState("set as broken", self.state, valid_states)

        self._change_state(RunspacePoolState.Broken, error)

    def host_call(
        self,
        method: HostMethodIdentifier,
        parameters: typing.Optional[typing.List] = None,
        pipeline_id: typing.Optional[uuid.UUID] = None,
    ) -> int:
        """Request host call.

        Request a host call on the client. Will generate a
        :class:`psrpcore.types.RunspacePoolHostCall` message to be sent to the
        client.

        Args:
            method: The host method that is requested to be run.
            parameters: Parameters to invoke the call with.
            pipeline_id: The pipeline identifier if the host call is for a
                specific pipeline or nont.

        Returns:
            int: The call identifier for this hoist call.
        """
        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("create host call", self.state, [RunspacePoolState.Opened])

        ci = -100 if method.is_void() else self._ci_counter

        call_type = PipelineHostCall if pipeline_id else RunspacePoolHostCall
        call = call_type(
            ci=ci,
            mi=method,
            mp=parameters if parameters is not None else [],
        )
        self.prepare_message(call, pipeline_id=pipeline_id, stream_type=StreamType.prompt_response)

        return ci

    def request_key(self) -> None:
        """Request key exchange.

        Requests the client to start a key exchange so that
        :class:`psrpcore.types.PSSecureString` objects can be serialized. This
        generates a :class:`psrpcore.types.PublicKeyRequest` message to be sent
        to the client.

        This is not used in ProtocolVersion 2.2 or newer but still present for
        backwards compatibility.
        """
        if self._key_requested:
            return

        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("request exchange key", self.state, [RunspacePoolState.Opened])

        self.prepare_message(PublicKeyRequest())
        self._key_requested = True

    def runspace_availability_response(
        self,
        ci: int,
        response: typing.Union[bool, int],
    ) -> None:
        """Response to Runspace Availablity.

        Responds to a RunspacePool availability event. The following responses
        are expected for these events:

            :class:`SetMaxRunspacesEvent` - `bool`
                Whether the max request worked or not.

            :class:`SetMinRunspacesEvent` - `bool`
                Whether the min request worked or not.

            :class:`ResetRunspaceStateEvent` - `bool`
                Whether the reset request worked or not.

            :class:`GetRunspaceAvailabilityEvent` - `int`
                The number of runspaces that are available

        Args:
            ci: The call ID to respond to.
            response: The response to send.
        """
        if ci not in self._ci_events:
            raise PSRPCoreError(f"Cannot respond to {ci}, not requested by client.")

        event = self._ci_events[ci]
        if isinstance(event, (SetMaxRunspacesEvent, SetMinRunspacesEvent, ResetRunspaceStateEvent)) and not isinstance(
            response, bool
        ):
            raise PSRPCoreError(f"Response for this event expects a bool not {type(response).__name__}")

        if isinstance(event, GetAvailableRunspacesEvent) and not isinstance(response, int):
            raise PSRPCoreError(f"Response for this event expects an int not {type(response).__name__}")

        del self._ci_events[ci]
        handler = self._ci_handlers.pop(ci, None)
        if handler and response is True:
            handler(event)

        self.prepare_message(RunspaceAvailability(SetMinMaxRunspacesResponse=response, ci=ci))

    def receive_data(
        self,
        data: PSRPPayload,
    ) -> None:
        if self.state == RunspacePoolState.BeforeOpen:
            self._change_state(RunspacePoolState.Opening, emit=False)

        super().receive_data(data)

    def _change_state(
        self,
        state: RunspacePoolState,
        error: typing.Optional[ErrorRecord] = None,
        emit: bool = True,
    ) -> None:
        super()._change_state(state, error)

        # (Dis)connection states aren't sent to the client
        if emit and state not in [
            RunspacePoolState.Disconnected,
            RunspacePoolState.Disconnecting,
            RunspacePoolState.Connecting,
        ]:
            state_kwargs = {
                "RunspaceState": state.value,
            }
            if error:
                state_kwargs["ExceptionAsErrorRecord"] = error
            self.prepare_message(RunspacePoolStateMsg(**state_kwargs))

    def _process_ConnectRunspacePool(
        self,
        event: ConnectRunspacePoolEvent,
    ) -> None:
        # FIXME: Verify this behaviour when the props aren't set or when invalid ones are
        self._max_runspaces = event.max_runspaces or self.max_runspaces
        self._min_runspaces = event.min_runspaces or self.min_runspaces

        self.prepare_message(
            RunspacePoolInitData(
                MinRunspaces=self.min_runspaces,
                MaxRunspaces=self.max_runspaces,
            )
        )

        self.prepare_message(ApplicationPrivateData(ApplicationPrivateData=self.application_private_data))
        self._change_state(RunspacePoolState.Opened)

    def _process_CreatePipeline(
        self,
        event: CreatePipelineEvent,
    ) -> None:
        if event.pipeline_id not in self.pipeline_table:
            raise PSRPCoreError(f"Failed to find pipeline for incoming event {event.pipeline_id!s}")

        self.pipeline_table[event.pipeline_id].metadata = event.pipeline

    def _process_EndOfPipelineInput(
        self,
        event: EndOfPipelineInputEvent,
    ) -> None:
        pass

    def _process_GetAvailableRunspaces(
        self,
        event: GetAvailableRunspacesEvent,
    ) -> None:
        self._ci_events[event.ci] = event
        self._ci_handlers[event.ci] = None

    def _process_GetCommandMetadata(
        self,
        event: GetCommandMetadataEvent,
    ) -> None:
        if event.pipeline_id not in self.pipeline_table:
            raise PSRPCoreError(f"Failed to find pipeline for incoming event {event.pipeline_id!s}")

        self.pipeline_table[event.pipeline_id].metadata = event.pipeline

    def _process_InitRunspacePool(
        self,
        event: InitRunspacePoolEvent,
    ) -> None:
        self.apartment_state = event.apartment_state
        self.application_arguments = event.application_arguments
        self.host = event.host_info
        self.thread_options = event.ps_thread_options
        self._max_runspaces = event.max_runspaces
        self._min_runspaces = event.min_runspaces

        self.prepare_message(ApplicationPrivateData(ApplicationPrivateData=self.application_private_data))
        self._change_state(RunspacePoolState.Opened)

    def _process_PipelineHostResponse(
        self,
        event: PipelineHostResponseEvent,
    ) -> None:
        pass

    def _process_PipelineInput(
        self,
        event: PipelineInputEvent,
    ) -> None:
        pass

    def _process_PublicKey(
        self,
        event: PublicKeyEvent,
    ) -> None:
        self._key_requested = True
        encrypted_session_key = encrypt_session_key(event.key, self._session_key)

        msg = EncryptedSessionKey(
            EncryptedSessionKey=base64.b64encode(encrypted_session_key).decode(),
        )
        self.prepare_message(msg)

    def _process_ResetRunspaceState(
        self,
        event: ResetRunspaceStateEvent,
    ) -> None:
        self._ci_events[event.ci] = event
        self._ci_handlers[event.ci] = None

    def _process_RunspacePoolHostResponse(
        self,
        event: RunspacePoolHostResponseEvent,
    ) -> None:
        pass

    def _process_SessionCapability(
        self,
        event: SessionCapabilityEvent,
    ) -> None:
        super()._process_SessionCapability(event)

        if self.state == RunspacePoolState.Connecting:
            if self.runspace_pool_id != event.runspace_pool_id:
                raise PSRPCoreError("Incoming connection is targeted towards a different Runspace Pool")

        else:
            self.prepare_message(self.our_capability)
            self.runspace_pool_id = event.runspace_pool_id

    def _process_SetMaxRunspaces(
        self,
        event: SetMaxRunspacesEvent,
    ) -> None:
        self._ci_events[event.ci] = event
        self._ci_handlers[event.ci] = lambda e: setattr(self, "_max_runspaces", event.count)

    def _process_SetMinRunspaces(
        self,
        event: SetMinRunspacesEvent,
    ) -> None:
        self._ci_events[event.ci] = event
        self._ci_handlers[event.ci] = lambda e: setattr(self, "_min_runspaces", event.count)


class ServerPipeline(Pipeline["ServerRunspacePool"]):
    """Server Pipeline.

    Represent a server pipeline and the various methods that can be used to
    communicate with the client pipeline. Any data generated by this pipeline is
    retrieved through the Runspace Pool it is a member off.
    """

    def complete(self) -> None:
        """Marks the pipeline as closed.

        This marks the pipeline has completed and generates a
        :class:`psrpcore.types.PipelineState` message to be sent to the client.
        """
        self._change_state(PSInvocationState.Completed)

    def start(self) -> None:
        """Marks the pipeline as started."""
        valid_states = [PSInvocationState.NotStarted, PSInvocationState.Stopped, PSInvocationState.Completed]
        if self.state not in valid_states:
            raise InvalidPipelineState("start a pipeline", self.state, valid_states)

        self._change_state(PSInvocationState.Running)

    def stop(self) -> None:
        """Stops the pipeline.

        Stops a running pipeline and generates a
        :class:`psrpcore.types.PipelineState` message to be sent to the client.
        """
        if self.state == PSInvocationState.Stopped:
            return

        valid_states = [PSInvocationState.Running, PSInvocationState.Stopping]
        if self.state not in valid_states:
            raise InvalidPipelineState("stop a pipeline", self.state, [PSInvocationState.Running])

        exception = NETException(
            Message="The pipeline has been stopped.",
            HResult=-2146233087,
        )

        type_names = [
            "System.Management.Automation.PipelineStoppedException",
            "System.Management.Automation.RuntimeException",
            "System.SystemException",
        ]
        type_names.extend(exception.PSTypeNames)
        exception.PSObject.type_names = type_names

        stopped_error = ErrorRecord(
            Exception=exception,
            CategoryInfo=ErrorCategoryInfo(
                Category=ErrorCategory.OperationStopped,
                Reason="PipelineStoppedException",
            ),
            FullyQualifiedErrorId="PipelineStopped",
        )
        self._change_state(PSInvocationState.Stopped, error=stopped_error)

    def host_call(
        self,
        method: HostMethodIdentifier,
        parameters: typing.Optional[typing.List] = None,
    ) -> int:
        """Request pipeline host call.

        Request a host call on the client for the pipeline. Will generate a
        :class:`psrpcore.types.PipelineHostCall` message to be sent to the
        client.

        Args:
            method: The host method that is requested to be run.
            parameters: Parameters to invoke the call with.

        Returns:
            int: The call identifier for this hoist call.
        """
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("make a pipeline host call", self.state, [PSInvocationState.Running])

        return self.runspace_pool.host_call(method, parameters, self.pipeline_id)

    def write_output(
        self,
        value: typing.Any,
    ) -> None:
        """Write object.

        Write an object to the output stream.

        Args:
            value: The object to write.
        """
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("write pipeline output", self.state, [PSInvocationState.Running])

        self.prepare_message(value, message_type=PSRPMessageType.PipelineOutput)

    def write_error(
        self,
        exception: NETException,
        category_info: typing.Optional[ErrorCategoryInfo] = None,
        target_object: typing.Any = None,
        fully_qualified_error_id: typing.Optional[str] = None,
        error_details: typing.Optional[ErrorDetails] = None,
        invocation_info: typing.Optional[InvocationInfo] = None,
        pipeline_iteration_info: typing.Optional[typing.List[int]] = None,
        script_stack_trace: typing.Optional[str] = None,
    ) -> None:
        """Write Error Record.

        Write an error record to the error stream.

        Args:
            exception: The .NET exception.
            category_info: Info about the type of error record.
            target_object: The object the error record is related to.
            fully_qualified_error_id: A unique identifier for this specific
                error record.
            error_details: Further details about this error record.
            invocation_info: Info about what generated the error record.
            pipeline_iteration_info: Where in the pipeline did this error record
                get generated.
            scrript_stack_trace: The stack trace which shows where the error
                was generated.
        """
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("write pipeline error", self.state, [PSInvocationState.Running])

        category_info = category_info or ErrorCategoryInfo()

        value = ErrorRecord(
            Exception=exception,
            CategoryInfo=category_info,
            TargetObject=target_object,
            FullyQualifiedErrorId=fully_qualified_error_id,
            InvocationInfo=invocation_info,
            ErrorDetails=error_details,
            PipelineIterationInfo=pipeline_iteration_info,
            ScriptStackTrace=script_stack_trace,
        )
        value.serialize_extended_info = invocation_info is not None
        self.prepare_message(value, message_type=PSRPMessageType.ErrorRecord)

    def write_debug(
        self,
        message: str,
        invocation_info: typing.Optional[InvocationInfo] = None,
        pipeline_iteration_info: typing.Optional[typing.List[int]] = None,
    ) -> None:
        """Write a Debug Record."""
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("write pipeline debug", self.state, [PSInvocationState.Running])

        value = DebugRecord(
            Message=message,
            InvocationInfo=invocation_info,
            PipelineIterationInfo=pipeline_iteration_info,
        )
        value.serialize_extended_info = invocation_info is not None
        self.prepare_message(value, message_type=PSRPMessageType.DebugRecord)

    def write_verbose(
        self,
        message: str,
        invocation_info: typing.Optional[InvocationInfo] = None,
        pipeline_iteration_info: typing.Optional[typing.List[int]] = None,
    ) -> None:
        """Write a Verbose Record."""
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("write pipeline verbose", self.state, [PSInvocationState.Running])

        value = VerboseRecord(
            Message=message,
            InvocationInfo=invocation_info,
            PipelineIterationInfo=pipeline_iteration_info,
        )
        value.serialize_extended_info = invocation_info is not None
        self.prepare_message(value, message_type=PSRPMessageType.VerboseRecord)

    def write_warning(
        self,
        message: str,
        invocation_info: typing.Optional[InvocationInfo] = None,
        pipeline_iteration_info: typing.Optional[typing.List[int]] = None,
    ) -> None:
        """Write a Warning Record."""
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("write pipeline warning", self.state, [PSInvocationState.Running])

        value = WarningRecord(
            Message=message,
            InvocationInfo=invocation_info,
            PipelineIterationInfo=pipeline_iteration_info,
        )
        value.serialize_extended_info = invocation_info is not None
        self.prepare_message(value, message_type=PSRPMessageType.WarningRecord)

    def write_progress(
        self,
        activity: str,
        activity_id: int,
        status_description: str,
        current_operation: typing.Optional[str] = None,
        parent_activity_id: int = -1,
        percent_complete: int = -1,
        record_type: ProgressRecordType = ProgressRecordType.Processing,
        seconds_remaining: int = -1,
    ) -> None:
        """Write a progress record.

        Writes a progress record to send to the client.

        Args:
            activity: The description of the activity for which progress is
                being reported.
            activity_id: The Id of the activity to which this record
                corresponds. Used as a key for linking of subordinate
                activities.
            status_description: Current status of the operation, e.g.
                "35 of 50 items copied.".
            current_operation: Current operation of the many required to
                accomplish the activity, e.g. "copying foo.txt".
            parent_activity_id: The Id of the activity for which this record is
                a subordinate.
            percent_complete: The estimate of the percentage of total work for
                the activity that is completed. Set to a negative value to
                indicate that the percentage completed should not be displayed.
            record_type: The type of record represented.
            seconds_remaining: The estimate of time remaining until this
                activity is completed. Set to a negative value to indicate that
                the seconds remaining should not be displayed.
        """
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("write pipeline progress", self.state, [PSInvocationState.Running])

        value = ProgressRecordMsg(
            Activity=activity,
            ActivityId=activity_id,
            StatusDescription=status_description,
            CurrentOperation=current_operation,
            ParentActivityId=parent_activity_id,
            PercentComplete=percent_complete,
            Type=record_type,
            SecondsRemaining=seconds_remaining,
        )
        self.prepare_message(value, message_type=PSRPMessageType.ProgressRecord)

    def write_information(
        self,
        message_data: typing.Any,
        source: str,
        time_generated: typing.Optional[datetime.datetime] = None,
        tags: typing.Optional[typing.List[str]] = None,
        user: typing.Optional[str] = None,
        computer: typing.Optional[str] = None,
        process_id: typing.Optional[int] = None,
        native_thread_id: typing.Optional[int] = None,
        managed_thread_id: int = None,
    ) -> None:
        """Write an information record.

        Writes an information record to send to the client.

        Note:
            This requires ProtocolVersion 2.3 (PowerShell 5.1+).

        Args:
            message_data: Data for this record.
            source: The source of this record, e.g. script path, function name,
                etc.
            time_generated: The time the record was generated, will default to
                now if not specified.
            tags: Tags associated with the record, if any.
            user: The user that generated the record, defaults to the current
                user.
            computer: The computer that generated the record, defaults to the
                current computer.
            process_id: The process that generated the record, defaults to the
                current process.
            native_thread_id: The native thread that generated the record,
                defaults to the current thread.
            managed_thread_id: The managed thread that generated the record,
                defaults to 0.
        """
        their_version = getattr(self.runspace_pool.their_capability, "protocolversion", ProtocolVersion.Win7RC.value)
        required_version = ProtocolVersion.Pwsh5.value
        if their_version < required_version:
            raise InvalidProtocolVersion("writing information record", their_version, required_version)

        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("write pipeline information", self.state, [PSInvocationState.Running])

        time_generated = PSDateTime.now() if time_generated is None else time_generated
        if not tags:
            tags = []

        if user is None:
            try:
                # getuser on Windows relies on env vars that may not may not be set. Just fallback gracefully.
                user = getpass.getuser()

            except ModuleNotFoundError:  # pragma: no cover
                user = "Unknown"

        computer = platform.node() if computer is None else computer
        process_id = os.getpid() if process_id is None else process_id

        # get_native_id isn't available until 3.8, default to 0.
        native_thread_id = getattr(threading, "get_native_id", lambda: 0)()

        value = InformationRecordMsg(
            MessageData=message_data,
            Source=source,
            TimeGenerated=time_generated,
            Tags=tags,
            User=user,
            Computer=computer,
            ProcessId=process_id or 0,
            NativeThreadId=native_thread_id or 0,
            ManagedThreadId=managed_thread_id or 0,
        )
        self.prepare_message(value, message_type=PSRPMessageType.InformationRecord)

    def _change_state(
        self,
        state: PSInvocationState,
        error: typing.Optional[ErrorRecord] = None,
        emit: bool = True,
    ) -> None:
        if emit:
            pipe_state = PipelineState(
                PipelineState=int(state),
            )
            if error is not None:
                pipe_state.ExceptionAsErrorRecord = error
            self.prepare_message(pipe_state)

        super()._change_state(state)
