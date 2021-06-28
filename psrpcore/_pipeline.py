# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import datetime
import getpass
import os
import platform
import threading
import typing
import uuid

from psrpcore._exceptions import (
    InvalidPipelineState,
    InvalidProtocolVersion,
)

from psrpcore._payload import (
    StreamType,
)

from psrpcore.types import (
    add_note_property,
    ApartmentState,
    CommandTypes,
    ErrorCategory,
    ErrorCategoryInfo,
    ErrorDetails,
    ErrorRecord,
    HostInfo,
    HostMethodIdentifier,
    InformationalRecord,
    InvocationInfo,
    NETException,
    PipelineResultTypes,
    ProgressRecordType,
    PSCustomObject,
    PSInvocationState,
    PSList,
    RemoteStreamOptions,
    PSDateTime,
    PSInt,
    PSString,
    PSUInt,
    PSVersion,
    PSObject,
)

from psrpcore.types._psrp_messages import (
    CreatePipeline,
    EndOfPipelineInput,
    GetCommandMetadata,
    InformationRecord,
    PipelineState,
    ProgressRecord,
    PSRPMessageType,
)

if typing.TYPE_CHECKING:
    from psrpcore._runspace import (
        RunspacePool,
        RunspacePoolType,
        ServerRunspacePool,
    )


def _dict_to_psobject(**kwargs) -> PSObject:
    """Builds a PSObject with note properties set by the kwargs."""
    obj = PSObject()
    for key, value in kwargs.items():
        add_note_property(obj, key, value)

    return obj


T = typing.TypeVar("T")


class _PipelineBase(typing.Generic[T]):
    def __new__(cls, *args, **kwargs):
        if cls in [_PipelineBase, _ClientPipeline, _ServerPipeline, GetCommandMetadataPipeline, PowerShell]:
            raise TypeError(
                f"Type {cls.__qualname__} cannot be instantiated; it can be used only as a base class for "
                f"client/server pipeline types."
            )

        return super().__new__(cls)

    def __init__(
        self,
        runspace_pool: T,
        pipeline_id: uuid.UUID,
    ):
        self.runspace_pool = runspace_pool
        self.state = PSInvocationState.NotStarted
        self.pipeline_id = pipeline_id
        runspace_pool.pipeline_table[self.pipeline_id] = self

    def close(self):
        del self.runspace_pool.pipeline_table[self.pipeline_id]

    def prepare_message(
        self,
        message: PSObject,
        message_type: typing.Optional[PSRPMessageType] = None,
        stream_type: StreamType = StreamType.default,
    ):
        self.runspace_pool.prepare_message(
            message, message_type=message_type, pipeline_id=self.pipeline_id, stream_type=stream_type
        )


class _ClientPipeline(_PipelineBase["RunspacePool"]):
    def __init__(
        self,
        runspace_pool: "RunspacePool",
    ):
        super().__init__(runspace_pool, uuid.uuid4())

    def invoke(self):
        self.prepare_message(self.to_psobject())
        self.state = PSInvocationState.Running

    def send(
        self,
        data: typing.Any,
    ):
        self.prepare_message(data, message_type=PSRPMessageType.PipelineInput)

    def send_end(self):
        self.prepare_message(EndOfPipelineInput())

    def host_response(
        self,
        ci: int,
        return_value: typing.Optional[typing.Any] = None,
        error_record: typing.Optional[ErrorRecord] = None,
    ):
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

    def to_psobject(self) -> PSObject:
        raise NotImplementedError()  # pragma: no cover


class _ServerPipeline(_PipelineBase["ServerRunspacePool"]):
    def start(self):
        if self.state == PSInvocationState.Running:
            return

        if self.state != PSInvocationState.NotStarted:
            raise InvalidPipelineState("starting pipeline", self.state, [PSInvocationState.NotStarted])

        self.state = PSInvocationState.Running

    def close(self):
        if self.state == PSInvocationState.Stopped:
            return

        super().close()
        self.state = PSInvocationState.Completed
        self._send_state()

    def stop(self):
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
    ):
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
        pipeline_iteration_info: typing.Optional[typing.List[typing.Union[PSInt, int]]] = None,
        script_stack_trace: typing.Optional[str] = None,
        serialize_extended_info: bool = False,
    ):
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
        pipeline_iteration_info: typing.Optional[typing.List[typing.Union[PSInt, int]]] = None,
        serialize_extended_info: bool = False,
    ):
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
        pipeline_iteration_info: typing.Optional[typing.List[typing.Union[PSInt, int]]] = None,
        serialize_extended_info: bool = False,
    ):
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
        pipeline_iteration_info: typing.Optional[typing.List[typing.Union[PSInt, int]]] = None,
        serialize_extended_info: bool = False,
    ):
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
        activity: typing.Union[PSString, str],
        activity_id: typing.Union[PSInt, int],
        status_description: typing.Union[PSString, str],
        current_operation: typing.Optional[typing.Union[PSString, str]] = None,
        parent_activity_id: typing.Union[PSInt, int] = -1,
        percent_complete: typing.Union[PSInt, int] = -1,
        record_type: ProgressRecordType = ProgressRecordType.Processing,
        seconds_remaining: typing.Union[PSInt, int] = -1,
    ):
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
        source: typing.Union[PSString, str],
        time_generated: typing.Optional[typing.Union[PSDateTime, datetime.datetime]] = None,
        tags: typing.Optional[PSList] = None,
        user: typing.Optional[typing.Union[PSString, str]] = None,
        computer: typing.Optional[typing.Union[PSString, str]] = None,
        process_id: typing.Optional[typing.Union[PSUInt, int]] = None,
        native_thread_id: typing.Optional[typing.Union[PSUInt, int]] = None,
        managed_thread_id: typing.Union[PSUInt, int] = None,
    ):
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
        their_version = self.runspace_pool.their_capability.protocolversion
        required_version = PSVersion("2.3")
        if their_version < required_version:
            raise InvalidProtocolVersion("writing information record", their_version, required_version)

        if self.state != PSInvocationState.Running:
            raise InvalidPipelineState("writing information record", self.state, [PSInvocationState.Running])

        time_generated = PSDateTime.now() if time_generated is None else time_generated
        tags = tags or []

        if user is None:
            try:
                # getuser on Windows relies on env vars that may not may not be set. Just fallback gracefully.
                user = getpass.getuser()

            except ModuleNotFoundError:
                user = "Unknown"

        computer = platform.node() if computer is None else computer
        process_id = os.getpid() if process_id is None else process_id

        # get_native_id isn't available until 3.8, default to 0.
        if native_thread_id is None:
            if hasattr(threading, "get_native_id"):
                native_thread_id = threading.get_native_id()
            else:
                native_thread_id = 0
        native_thread_id = native_thread_id

        value = InformationRecord(
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
    ):
        state = PipelineState(
            PipelineState=int(self.state),
        )
        if error_record is not None:
            state.ExceptionAsErrorRecord = error_record
        self.prepare_message(state)


class PowerShell(_PipelineBase):
    """
    Args:
        add_to_history: Whether to add the pipeline to the history field of the runspace.
        apartment_state: The apartment state of the thread that executes the pipeline.
        host: The host information to use when executing the pipeline.
        no_input: Whether there is any data to be input into the pipeline.
        remote_stream_options: Whether to add invocation info the the PowerShell streams or not.
        redirect_shell_error_to_out: Redirects the global error output pipe to the commands error output pipe.
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
        *args,
        **kwargs,
    ):
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

    def to_psobject(self) -> CreatePipeline:
        if not self.commands:
            raise ValueError("A command is required to invoke a PowerShell pipeline.")

        extra_cmds = [[]]
        for cmd in self.commands:
            cmd_psobject = cmd.to_psobject(self.runspace_pool.their_capability.protocolversion)
            extra_cmds[-1].append(cmd_psobject)
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
            pipeline_kwargs["ExtraCmds"] = [_dict_to_psobject(Cmds=s) for s in extra_cmds]

        return CreatePipeline(
            NoInput=self.no_input,
            ApartmentState=self.apartment_state,
            RemoteStreamOptions=self.remote_stream_options,
            AddToHistory=self.add_to_history,
            HostInfo=self.host,
            PowerShell=_dict_to_psobject(**pipeline_kwargs),
            IsNested=self.is_nested,
        )


class ClientPowerShell(PowerShell, _ClientPipeline):
    def __init__(
        self,
        runspace_pool: "RunspacePool",
        *args,
        **kwargs,
    ):
        super().__init__(runspace_pool=runspace_pool, *args, **kwargs)

    def add_argument(
        self,
        value: typing.Any,
    ):
        self.add_parameter(None, value)

    def add_command(
        self,
        cmdlet: typing.Union[str, "Command"],
        use_local_scope: typing.Optional[bool] = None,
    ):
        if isinstance(cmdlet, str):
            cmdlet = Command(cmdlet, use_local_scope=use_local_scope)

        elif use_local_scope is not None:
            raise TypeError("Cannot set use_local_scope with Command")

        self.commands.append(cmdlet)

    def add_parameter(
        self,
        name: typing.Optional[str],
        value: typing.Any = None,
    ):
        if not self.commands:
            raise ValueError(
                "A command is required to add a parameter/argument. A command must be added to the "
                "PowerShell instance first."
            )

        self.commands[-1].parameters.append((name, value))

    def add_parameters(
        self,
        parameters: typing.Dict[str, typing.Any],
    ):
        for name, value in parameters.items():
            self.add_parameter(name, value)

    def add_script(
        self,
        script: str,
        use_local_scope: typing.Optional[bool] = None,
    ):
        self.add_command(Command(script, True, use_local_scope=use_local_scope))

    def add_statement(self):
        if not self.commands:
            return

        self.commands[-1].end_of_statement = True


class ServerPowerShell(PowerShell, _ServerPipeline):
    def __init__(
        self,
        runspace_pool: "ServerRunspacePool",
        pipeline_id: str,
        *args,
        **kwargs,
    ):
        super().__init__(runspace_pool=runspace_pool, pipeline_id=pipeline_id, *args, **kwargs)


class GetCommandMetadataPipeline(_PipelineBase):
    def __init__(
        self,
        name: typing.Union[str, typing.List[str]],
        command_type: CommandTypes = CommandTypes.All,
        namespace: typing.Optional[typing.List[str]] = None,
        arguments: typing.Optional[typing.List[str]] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if not isinstance(name, list):
            name = [name]
        self.name = name
        self.command_type = command_type
        self.namespace = namespace
        self.arguments = arguments

    def to_psobject(self) -> GetCommandMetadata:
        return GetCommandMetadata(
            Name=self.name,
            CommandType=self.command_type,
            Namespace=self.namespace,
            ArgumentList=self.arguments,
        )


class ClientGetCommandMetadata(GetCommandMetadataPipeline, _ClientPipeline):
    def __init__(
        self,
        runspace_pool: "RunspacePool",
        *args,
        **kwargs,
    ):
        super().__init__(runspace_pool=runspace_pool, *args, **kwargs)


class ServerGetCommandMetadata(GetCommandMetadataPipeline, _ServerPipeline):
    def __init__(
        self,
        runspace_pool: "ServerRunspacePool",
        pipeline_id: str,
        *args,
        **kwargs,
    ):
        super().__init__(runspace_pool=runspace_pool, pipeline_id=pipeline_id, *args, **kwargs)
        self._count = None
        # TODO: Add support for writing other command info types.

    def write_count(
        self,
        count: typing.Union[PSInt, int],
    ):
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
    ):

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
    ):
        if self._count is None:
            raise ValueError("write_count must be called before writing to the command metadata pipeline")
        super().write_output(value)


class Command:
    def __init__(
        self,
        name: str,
        is_script: bool = False,
        use_local_scope: typing.Optional[bool] = None,
    ):
        self.command_text = name
        self.is_script = is_script
        self.use_local_scope = use_local_scope
        self.parameters: typing.List[typing.Tuple[typing.Optional[str], typing.Any]] = []
        self.end_of_statement = False

        self.merge_unclaimed = False
        self._merge_my = PipelineResultTypes.none
        self._merge_to = PipelineResultTypes.none
        self._merge_error = PipelineResultTypes.none
        self._merge_warning = PipelineResultTypes.none
        self._merge_verbose = PipelineResultTypes.none
        self._merge_debug = PipelineResultTypes.none
        self._merge_information = PipelineResultTypes.none

    def __repr__(self):
        cls = self.__class__
        return (
            f"{cls.__name__}(name='{self.command_text}', is_script={self.is_script}, "
            f"use_local_scope={self.use_local_scope!s})"
        )

    def __str__(self):
        return self.command_text

    @property
    def merge_my(self) -> PipelineResultTypes:
        return self._merge_my

    @property
    def merge_to(self) -> PipelineResultTypes:
        return self._merge_to

    @property
    def merge_error(self) -> PipelineResultTypes:
        return self._merge_error

    @property
    def merge_warning(self) -> PipelineResultTypes:
        return self._merge_warning

    @property
    def merge_verbose(self) -> PipelineResultTypes:
        return self._merge_verbose

    @property
    def merge_debug(self) -> PipelineResultTypes:
        return self._merge_debug

    @property
    def merge_information(self) -> PipelineResultTypes:
        return self._merge_information

    def redirect_all(
        self,
        stream: PipelineResultTypes.Output,
    ):
        if stream == PipelineResultTypes.none:
            self._merge_my = stream
            self._merge_to = stream

        self.redirect_error(stream)
        self.redirect_warning(stream)
        self.redirect_verbose(stream)
        self.redirect_debug(stream)
        self.redirect_information(stream)

    def redirect_error(self, stream: PipelineResultTypes.Output):
        self._validate_redirection_to(stream)
        if stream == PipelineResultTypes.none:
            self._merge_my = PipelineResultTypes.none
            self._merge_to = PipelineResultTypes.none

        elif stream != PipelineResultTypes.Null:
            self._merge_my = PipelineResultTypes.Error
            self._merge_to = stream

        self._merge_error = stream

    def redirect_warning(self, stream: PipelineResultTypes.Output):
        self._validate_redirection_to(stream)
        self._merge_warning = stream

    def redirect_verbose(self, stream: PipelineResultTypes.Output):
        self._validate_redirection_to(stream)
        self._merge_verbose = stream

    def redirect_debug(self, stream: PipelineResultTypes.Output):
        self._validate_redirection_to(stream)
        self._merge_debug = stream

    def redirect_information(self, stream: PipelineResultTypes.Output):
        self._validate_redirection_to(stream)
        self._merge_information = stream

    def _validate_redirection_to(
        self,
        stream: PipelineResultTypes,
    ):
        if stream not in [PipelineResultTypes.none, PipelineResultTypes.Output, PipelineResultTypes.Null]:
            raise ValueError("Invalid redirection stream, must be none, Output, or Null")

    def to_psobject(
        self,
        protocol_version: PSVersion,
    ) -> PSObject:
        merge_previous = (
            PipelineResultTypes.Output | PipelineResultTypes.Error if self.merge_unclaimed else PipelineResultTypes.none
        )

        command_kwargs = {
            "Cmd": self.command_text,
            "Args": [_dict_to_psobject(N=n, V=v) for n, v in self.parameters],
            "IsScript": self.is_script,
            "UseLocalScope": self.use_local_scope,
            "MergeMyResult": self.merge_my,
            "MergeToResult": self.merge_to,
            "MergePreviousResults": merge_previous,
        }

        # For backwards compatibility we need to optional set these values based on the peer's protocol version.
        if protocol_version >= PSVersion("2.2"):
            command_kwargs["MergeError"] = self.merge_error
            command_kwargs["MergeWarning"] = self.merge_warning
            command_kwargs["MergeVerbose"] = self.merge_verbose
            command_kwargs["MergeDebug"] = self.merge_debug

        if protocol_version >= PSVersion("2.3"):
            command_kwargs["MergeInformation"] = self.merge_information

        return _dict_to_psobject(**command_kwargs)

    @staticmethod
    def from_psobject(
        command: PSObject,
    ) -> "Command":
        cmd = Command(
            name=command.Cmd,
            is_script=command.IsScript,
            use_local_scope=command.UseLocalScope,
        )
        for argument in command.Args:
            cmd.parameters.append((argument.N, argument.V))

        merge_unclaimed = PipelineResultTypes.Output | PipelineResultTypes.Error
        cmd.merge_unclaimed = bool(command.MergePreviousResults == merge_unclaimed)

        cmd._merge_my = command.MergeMyResult
        cmd._merge_to = command.MergeToResult

        # Depending on the peer protocolversion, these fields may not be present.
        for name in ["Error", "Warning", "Verbose", "Debug", "Information"]:
            value = getattr(command, f"Merge{name}", None)
            if value is not None:
                setattr(cmd, f"_merge_{name.lower()}", value)

        return cmd


PipelineType = typing.TypeVar("PipelineType", bound=_PipelineBase)
