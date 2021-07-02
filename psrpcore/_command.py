# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import typing

from psrpcore._payload import dict_to_psobject
from psrpcore.types import PipelineResultTypes, PSObject, PSVersion


class Command(PSObject):
    def __init__(
        self,
        name: str,
        is_script: bool = False,
        use_local_scope: typing.Optional[bool] = None,
    ) -> None:
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

    def __repr__(self) -> str:
        cls = self.__class__
        return (
            f"{cls.__name__}(name='{self.command_text}', is_script={self.is_script}, "
            f"use_local_scope={self.use_local_scope!s})"
        )

    def __str__(self) -> str:
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
        stream: PipelineResultTypes = PipelineResultTypes.Output,
    ) -> None:
        if stream == PipelineResultTypes.none:
            self._merge_my = stream
            self._merge_to = stream

        self.redirect_error(stream)
        self.redirect_warning(stream)
        self.redirect_verbose(stream)
        self.redirect_debug(stream)
        self.redirect_information(stream)

    def redirect_error(
        self,
        stream: PipelineResultTypes = PipelineResultTypes.Output,
    ) -> None:
        self._validate_redirection_to(stream)
        if stream == PipelineResultTypes.none:
            self._merge_my = PipelineResultTypes.none
            self._merge_to = PipelineResultTypes.none

        elif stream != PipelineResultTypes.Null:
            self._merge_my = PipelineResultTypes.Error
            self._merge_to = stream

        self._merge_error = stream

    def redirect_warning(
        self,
        stream: PipelineResultTypes = PipelineResultTypes.Output,
    ) -> None:
        self._validate_redirection_to(stream)
        self._merge_warning = stream

    def redirect_verbose(
        self,
        stream: PipelineResultTypes = PipelineResultTypes.Output,
    ) -> None:
        self._validate_redirection_to(stream)
        self._merge_verbose = stream

    def redirect_debug(
        self,
        stream: PipelineResultTypes = PipelineResultTypes.Output,
    ) -> None:
        self._validate_redirection_to(stream)
        self._merge_debug = stream

    def redirect_information(
        self,
        stream: PipelineResultTypes = PipelineResultTypes.Output,
    ) -> None:
        self._validate_redirection_to(stream)
        self._merge_information = stream

    def _validate_redirection_to(
        self,
        stream: PipelineResultTypes,
    ) -> None:
        if stream not in [PipelineResultTypes.none, PipelineResultTypes.Output, PipelineResultTypes.Null]:
            raise ValueError("Invalid redirection stream, must be none, Output, or Null")

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        obj: PSObject,
        **kwargs: typing.Any,
    ) -> "Command":
        cmd = cls(
            name=obj.Cmd,
            is_script=obj.IsScript,
            use_local_scope=obj.UseLocalScope,
        )
        for argument in obj.Args:
            cmd.parameters.append((argument.N, argument.V))

        merge_unclaimed = PipelineResultTypes.Output | PipelineResultTypes.Error
        cmd.merge_unclaimed = bool(obj.MergePreviousResults == merge_unclaimed)

        cmd._merge_my = obj.MergeMyResult
        cmd._merge_to = obj.MergeToResult

        # Depending on the peer protocolversion, these fields may not be present.
        for name in ["Error", "Warning", "Verbose", "Debug", "Information"]:
            value = getattr(obj, f"Merge{name}", None)
            if value is not None:
                setattr(cmd, f"_merge_{name.lower()}", value)

        return cmd

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "Command",
        **kwargs: typing.Any,
    ) -> PSObject:
        protocol_version = None
        if "their_capability" in kwargs:
            protocol_version = getattr(kwargs["their_capability"], "protocolversion", None)

        if not protocol_version:
            protocol_version = PSVersion("2.2")

        merge_previous = (
            PipelineResultTypes.Output | PipelineResultTypes.Error
            if instance.merge_unclaimed
            else PipelineResultTypes.none
        )

        command_kwargs = {
            "Cmd": instance.command_text,
            "Args": [dict_to_psobject(N=n, V=v) for n, v in instance.parameters],
            "IsScript": instance.is_script,
            "UseLocalScope": instance.use_local_scope,
            "MergeMyResult": instance.merge_my,
            "MergeToResult": instance.merge_to,
            "MergePreviousResults": merge_previous,
        }

        # For backwards compatibility we need to optional set these values based on the peer's protocol version.
        if protocol_version >= PSVersion("2.2"):
            command_kwargs["MergeError"] = instance.merge_error
            command_kwargs["MergeWarning"] = instance.merge_warning
            command_kwargs["MergeVerbose"] = instance.merge_verbose
            command_kwargs["MergeDebug"] = instance.merge_debug

        if protocol_version >= PSVersion("2.3"):
            command_kwargs["MergeInformation"] = instance.merge_information

        return dict_to_psobject(**command_kwargs)
