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

from psrpcore._base import (
    GetCommandMetadataPipeline,
    Pipeline,
    PowerShellPipeline,
    RunspacePool,
)
from psrpcore._command import Command
from psrpcore._crypto import PSRemotingCrypto, encrypt_session_key
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
from psrpcore._payload import EMPTY_UUID, StreamType
from psrpcore.types import (
    ApplicationPrivateData,
    CommandTypes,
    EncryptedSessionKey,
    ErrorCategory,
    ErrorCategoryInfo,
    ErrorDetails,
    ErrorRecord,
    HostInfo,
    HostMethodIdentifier,
    InformationalRecord,
    InformationRecordMsg,
    InvocationInfo,
    NETException,
    PipelineHostCall,
    PipelineState,
    ProgressRecord,
    ProgressRecordType,
    PSCustomObject,
    PSDateTime,
    PSInt,
    PSInvocationState,
    PSList,
    PSRPMessageType,
    PSString,
    PSVersion,
    PublicKeyRequest,
    RunspaceAvailability,
    RunspacePoolHostCall,
    RunspacePoolInitData,
    RunspacePoolState,
    RunspacePoolStateMsg,
    SessionCapability,
    UserEvent,
)

_DEFAULT_CAPABILITY = SessionCapability(
    PSVersion=PSVersion("2.0"),
    protocolversion=PSVersion("2.3"),
    SerializationVersion=PSVersion("1.1.0.1"),
)


class ServerRunspacePool(RunspacePool):
    def __init__(
        self,
        application_private_data: typing.Optional[typing.Dict] = None,
    ) -> None:
        super().__init__(
            EMPTY_UUID,
            capability=_DEFAULT_CAPABILITY,
            application_arguments={},
            application_private_data=application_private_data or {},
        )

    def connect(self) -> None:
        if self.state == RunspacePoolState.Opened:
            return
        if self.state != RunspacePoolState.Disconnected:
            raise InvalidRunspacePoolState(
                "accept Runspace Pool connections", self.state, [RunspacePoolState.BeforeOpen]
            )

        # The incoming messages will be from a blank runspace pool so start back at 0
        # TODO: Should I also reset ci count.
        # TODO: Verify there are no incoming fragments/messages not processed.
        self._fragment_count = 0
        self.state = RunspacePoolState.Connecting

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
                RunspaceId=self.runspace_pool_id,
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

    def request_key(self) -> None:
        if self._cipher:
            return

        if self.state != RunspacePoolState.Opened:
            raise InvalidRunspacePoolState("request exchange key", self.state, [RunspacePoolState.Opened])

        self.prepare_message(PublicKeyRequest())

    def _process_ConnectRunspacePool(
        self,
        event: ConnectRunspacePoolEvent,
    ) -> None:
        # TODO: Verify this behaviour when the props aren't set
        self._max_runspaces = getattr(event.ps_object, "MaxRunspaces", self.max_runspaces)
        self._min_runspaces = getattr(event.ps_object, "MinRunspaces", self.min_runspaces)

        self.prepare_message(
            RunspacePoolInitData(
                MinRunspaces=self.min_runspaces,
                MaxRunspaces=self.max_runspaces,
            )
        )

        self.prepare_message(ApplicationPrivateData(ApplicationPrivateData=self.application_private_data))
        self.state = RunspacePoolState.Opened

    def _process_CreatePipeline(
        self,
        event: CreatePipelineEvent,
    ) -> None:
        create_pipeline = event.ps_object
        powershell = create_pipeline.PowerShell

        pipeline = ServerPowerShell(
            runspace_pool=self,
            pipeline_id=event.pipeline_id,
            add_to_history=create_pipeline.AddToHistory,
            apartment_state=create_pipeline.ApartmentState,
            history=powershell.History,
            host=HostInfo.FromPSObjectForRemoting(create_pipeline.HostInfo),
            is_nested=create_pipeline.IsNested,
            no_input=create_pipeline.NoInput,
            remote_stream_options=create_pipeline.RemoteStreamOptions,
            redirect_shell_error_to_out=powershell.RedirectShellErrorOutputPipe,
        )
        commands = [powershell.Cmds]
        commands.extend([c.Cmds for c in getattr(powershell, "ExtraCmds", [])])

        for statements in commands:
            for raw_cmd in statements:
                cmd = Command.FromPSObjectForRemoting(raw_cmd)
                pipeline.commands.append(cmd)

            pipeline.commands[-1].end_of_statement = True

        event.pipeline = pipeline

    def _process_EndOfPipelineInput(
        self,
        event: EndOfPipelineInputEvent,
    ) -> None:
        pass

    def _process_GetAvailableRunspaces(
        self,
        event: GetAvailableRunspacesEvent,
    ) -> None:
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
    ) -> None:
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
    ) -> None:
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
    ) -> None:
        pass

    def _process_RunspacePoolHostResponse(
        self,
        event: RunspacePoolHostResponseEvent,
    ) -> None:
        pass

    def _process_SessionCapability(
        self,
        event: SessionCapabilityEvent,
    ) -> None:
        pre_state = self.state
        super()._process_SessionCapability(event)

        if pre_state == RunspacePoolState.Connecting:
            if self.runspace_pool_id != event.runspace_pool_id:
                raise PSRPCoreError("Incoming connection is targeted towards a different Runspace Pool")

        else:
            self.prepare_message(self.our_capability)
            self.runspace_pool_id = event.runspace_pool_id

    def _process_SetMaxRunspaces(
        self,
        event: SetMaxRunspacesEvent,
    ) -> None:
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
    ) -> None:
        self._min_runspaces = event.ps_object.MinRunspaces
        self.prepare_message(
            RunspaceAvailability(
                SetMinMaxRunspacesResponse=True,
                ci=event.ps_object.ci,
            )
        )


class _ServerPipeline(Pipeline["ServerRunspacePool"]):
    def start(self) -> None:
        if self.state == PSInvocationState.Running:
            return

        if self.state != PSInvocationState.NotStarted:
            raise InvalidPipelineState("starting pipeline", self.state, [PSInvocationState.NotStarted])

        self.state = PSInvocationState.Running

    def close(self) -> None:
        if self.state == PSInvocationState.Stopped:
            return

        super().close()
        self.state = PSInvocationState.Completed
        self._send_state()

    def stop(self) -> None:
        if self.state in [PSInvocationState.Stopped, PSInvocationState.Stopping]:
            return

        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("closing pipeline", self.state, [PSInvocationState.Running])

        self.state = PSInvocationState.Stopped

        exception = NETException(
            Message="The pipeline has been stopped.",
            HResult=-2146233087,
        )
        exception.PSTypeNames.extend(
            [
                "System.Management.Automation.PipelineStoppedException",
                "System.Management.Automation.RuntimeException",
                "System.SystemException",
            ]
        )

        stopped_error = ErrorRecord(
            Exception=exception,
            CategoryInfo=ErrorCategoryInfo(
                Category=ErrorCategory.OperationStopped,
                Reason="PipelineStoppedException",
            ),
            FullyQualifiedErrorId="PipelineStopped",
        )
        self._send_state(stopped_error)
        super().close()

    def host_call(
        self,
        method: HostMethodIdentifier,
        parameters: typing.Optional[typing.List] = None,
    ) -> int:
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("making pipeline host call", self.state, [PSInvocationState.Running])

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
            raise InvalidPipelineState("writing output record", self.state, [PSInvocationState.Running])

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
        serialize_extended_info: bool = False,
    ) -> None:
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("writing error record", self.state, [PSInvocationState.Running])

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
        value.serialize_extended_info = serialize_extended_info
        self.prepare_message(value, message_type=PSRPMessageType.ErrorRecord)

    def write_debug(
        self,
        message: typing.Union[str],
        invocation_info: typing.Optional[InvocationInfo] = None,
        pipeline_iteration_info: typing.Optional[typing.List[int]] = None,
        serialize_extended_info: bool = False,
    ) -> None:
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("writing debug record", self.state, [PSInvocationState.Running])

        value = InformationalRecord(
            Message=message,
            InvocationInfo=invocation_info,
            PipelineIterationInfo=pipeline_iteration_info,
        )
        value.serialize_extended_info = serialize_extended_info
        self.prepare_message(value, message_type=PSRPMessageType.DebugRecord)

    def write_verbose(
        self,
        message: typing.Union[str],
        invocation_info: typing.Optional[InvocationInfo] = None,
        pipeline_iteration_info: typing.Optional[typing.List[int]] = None,
        serialize_extended_info: bool = False,
    ) -> None:
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("writing verbose record", self.state, [PSInvocationState.Running])

        value = InformationalRecord(
            Message=message,
            InvocationInfo=invocation_info,
            PipelineIterationInfo=pipeline_iteration_info,
        )
        value.serialize_extended_info = serialize_extended_info
        self.prepare_message(value, message_type=PSRPMessageType.VerboseRecord)

    def write_warning(
        self,
        message: typing.Union[str],
        invocation_info: typing.Optional[InvocationInfo] = None,
        pipeline_iteration_info: typing.Optional[typing.List[int]] = None,
        serialize_extended_info: bool = False,
    ) -> None:
        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("writing warning record", self.state, [PSInvocationState.Running])

        value = InformationalRecord(
            Message=message,
            InvocationInfo=invocation_info,
            PipelineIterationInfo=pipeline_iteration_info,
        )
        value.serialize_extended_info = serialize_extended_info
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
            raise InvalidPipelineState("writing progress record", self.state, [PSInvocationState.Running])

        value = ProgressRecord(
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
        tags: typing.Optional[PSList] = None,
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
        their_version = getattr(self.runspace_pool.their_capability, "protocolversion", PSVersion("0.0"))
        required_version = PSVersion("2.3")
        if their_version < required_version:
            raise InvalidProtocolVersion("writing information record", their_version, required_version)

        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("writing information record", self.state, [PSInvocationState.Running])

        time_generated = PSDateTime.now() if time_generated is None else time_generated
        if not tags:
            tags = PSList()

        if user is None:
            try:
                # getuser on Windows relies on env vars that may not may not be set. Just fallback gracefully.
                user = getpass.getuser()

            except ModuleNotFoundError:
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

    def _send_state(
        self,
        error_record: typing.Optional[ErrorRecord] = None,
    ) -> None:
        state = PipelineState(
            PipelineState=int(self.state),
        )
        if error_record is not None:
            state.ExceptionAsErrorRecord = error_record
        self.prepare_message(state)


class ServerPowerShell(PowerShellPipeline, _ServerPipeline):
    def __init__(
        self,
        runspace_pool: "ServerRunspacePool",
        pipeline_id: uuid.UUID,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(runspace_pool=runspace_pool, pipeline_id=pipeline_id, *args, **kwargs)


class ServerGetCommandMetadata(GetCommandMetadataPipeline, _ServerPipeline):
    def __init__(
        self,
        runspace_pool: "ServerRunspacePool",
        pipeline_id: uuid.UUID,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(runspace_pool=runspace_pool, pipeline_id=pipeline_id, *args, **kwargs)
        self._count: typing.Optional[int] = None
        # TODO: Add support for writing other command info types.

    def write_count(
        self,
        count: int,
    ) -> None:
        self._count = count
        obj = PSCustomObject(
            PSTypeName="Selected.Microsoft.PowerShell.Commands.GenericMeasureInfo",
            Count=count,
        )
        self.write_output(obj)

    def write_cmdlet_info(
        self,
        name: typing.Union[PSString, str],
        namespace: typing.Union[PSString, str],
        help_uri: typing.Union[PSString, str] = "",
        output_type: typing.Optional[typing.List[typing.Union[PSString, str]]] = None,
        parameters: typing.Optional[typing.Dict[typing.Union[PSString, str], typing.Any]] = None,
    ) -> None:

        self.write_output(
            PSCustomObject(
                PSTypeName="Selected.System.Management.Automation.CmdletInfo",
                CommandType=CommandTypes.Cmdlet,
                Name=name,
                Namespace=namespace,
                HelpUri=help_uri,
                OutputType=output_type or [],
                Parameters=parameters or {},
                ResolvedCommandName=None,
            )
        )

    def write_output(
        self,
        value: typing.Any,
    ) -> None:
        if self._count is None:
            raise ValueError("write_count must be called before writing to the command metadata pipeline")
        super().write_output(value)
