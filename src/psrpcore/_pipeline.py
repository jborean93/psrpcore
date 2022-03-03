# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import typing

from psrpcore._command import Command
from psrpcore._payload import dict_to_psobject
from psrpcore.types import (
    ApartmentState,
    CommandTypes,
    CreatePipeline,
    GetCommandMetadata,
    HostInfo,
    PSObject,
    RemoteStreamOptions,
)


class PowerShell(PSObject):
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
        apartment_state: ApartmentState = None,
        history: typing.Optional[str] = None,
        host: typing.Optional[HostInfo] = None,
        is_nested: bool = False,
        no_input: bool = True,
        remote_stream_options: RemoteStreamOptions = RemoteStreamOptions.none,
        redirect_shell_error_to_out: bool = True,
    ) -> None:
        self.add_to_history = add_to_history
        self.apartment_state = apartment_state
        self.commands: typing.List[Command] = []
        self.history = history
        self.host = host or HostInfo()
        self.is_nested = is_nested
        self.no_input = no_input
        self.remote_stream_options = remote_stream_options
        self.redirect_shell_error_to_out = redirect_shell_error_to_out

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} add_to_history={self.add_to_history} apartment_state={self.apartment_state!r} "
            f"commands={self.commands!r} history={self.history!r} host={self.host!r} is_nested={self.is_nested} "
            f"no_input={self.no_input} remote_stream_options={self.remote_stream_options!r} "
            f"redirect_shell_error_to_out={self.redirect_shell_error_to_out!r}>"
        )

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        value: "PSObject",
        **kwargs: typing.Any,
    ) -> "PowerShell":
        powershell = value.PowerShell

        pipeline = PowerShell(
            add_to_history=value.AddToHistory,
            apartment_state=value.ApartmentState,
            history=powershell.History,
            host=HostInfo.FromPSObjectForRemoting(value.HostInfo),
            is_nested=value.IsNested,
            no_input=value.NoInput,
            remote_stream_options=value.RemoteStreamOptions,
            redirect_shell_error_to_out=powershell.RedirectShellErrorOutputPipe,
        )

        extra_cmds = getattr(powershell, "ExtraCmds", None)
        if extra_cmds is not None:
            commands = [c.Cmds for c in extra_cmds]
        else:
            commands = [powershell.Cmds]

        for statements in commands:
            for raw_cmd in statements:
                cmd = Command.FromPSObjectForRemoting(raw_cmd)
                pipeline.commands.append(cmd)

            pipeline.commands[-1].end_of_statement = True

        return pipeline

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "PowerShell",
        **kwargs: typing.Any,
    ) -> CreatePipeline:
        if not instance.commands:
            raise ValueError("A command is required to invoke a PowerShell pipeline.")

        extra_cmds: typing.List[typing.List[PSObject]] = [[]]
        for cmd in instance.commands:
            extra_cmds[-1].append(cmd)
            if cmd.end_of_statement:
                extra_cmds.append([])
        cmds = extra_cmds[0]

        # MS-PSRP 2.2.3.11 Pipeline
        # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/82a8d1c6-4560-4e68-bfd0-a63c36d6a199
        pipeline_kwargs = {
            "Cmds": cmds,
            "IsNested": instance.is_nested,
            "History": instance.history,
            "RedirectShellErrorOutputPipe": instance.redirect_shell_error_to_out,
        }

        if len(extra_cmds) > 1:
            # This isn't documented in MS-PSRP but this is how PowerShell batches multiple statements in 1 pipeline.
            # TODO: ExtraCmds may not work with protocol <=2.1.
            pipeline_kwargs["ExtraCmds"] = [dict_to_psobject(Cmds=s) for s in extra_cmds]

        return CreatePipeline(
            NoInput=instance.no_input,
            ApartmentState=instance.apartment_state,
            RemoteStreamOptions=instance.remote_stream_options,
            AddToHistory=instance.add_to_history,
            HostInfo=instance.host,
            PowerShell=dict_to_psobject(**pipeline_kwargs),
            IsNested=instance.is_nested,
        )


class GetMetadata(PSObject):
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
    ) -> None:
        if not isinstance(name, list):
            name = [name]
        self.name = name
        self.command_type = command_type
        self.namespace = namespace
        self.arguments = arguments

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} name={self.name!r} command_type={self.command_type!r} "
            f"namespace={self.namespace!r} arguments={self.arguments!r}>"
        )

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        value: PSObject,
        **kwargs: typing.Any,
    ) -> "GetMetadata":
        return GetMetadata(
            name=value.Name,
            command_type=value.CommandType,
            namespace=value.Namespace,
            arguments=value.ArgumentList,
        )

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "GetMetadata",
        **kwargs: typing.Any,
    ) -> GetCommandMetadata:
        return GetCommandMetadata(
            Name=instance.name,
            CommandType=instance.command_type,
            Namespace=instance.namespace,
            ArgumentList=instance.arguments,
        )
