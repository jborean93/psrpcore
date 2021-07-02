# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import typing

from psrpcore.types import PSInvocationState, PSVersion, RunspacePoolState

T = typing.TypeVar("T")


class PSRPCoreError(Exception):
    """Base error for any PSRP errors."""


class MissingCipherError(PSRPCoreError):
    """Trying to (de)serialize a Secure String but no cipher was provided."""

    @property
    def message(self) -> str:
        return "Cannot (de)serialize a secure string without an exchanged session key"

    def __str__(self) -> str:
        return self.message


class _InvalidState(PSRPCoreError, typing.Generic[T]):
    _STATE_OBJ: typing.Optional[str] = None

    def __init__(
        self,
        action: str,
        current_state: T,
        expected_states: typing.List[T],
    ) -> None:
        self.action = action
        self.current_state = current_state
        self.expected_states = expected_states

    @property
    def message(self) -> str:
        expected_states = ", ".join(str(s) for s in self.expected_states)
        return (
            f"{self._STATE_OBJ} state must be one of '{expected_states}' to {self.action}, current state is "
            f"{self.current_state!s}"
        )

    def __str__(self) -> str:
        return self.message


class InvalidRunspacePoolState(_InvalidState[RunspacePoolState]):
    """The Runspace Pool is not in the required state."""

    _STATE_OBJ = "Runspace Pool"


class InvalidPipelineState(_InvalidState[PSInvocationState]):
    """The Pipeline is not in the required state."""

    _STATE_OBJ = "Pipeline"


class InvalidProtocolVersion(PSRPCoreError):
    """The protocolversion of the peer does not meet the required version."""

    def __init__(
        self,
        action: str,
        current_version: PSVersion,
        required_version: PSVersion,
    ):
        self.action = action
        self.current_version = current_version
        self.required_version = required_version

    @property
    def message(self) -> str:
        return (
            f"{self.action} requires a protocol version of {self.required_version}, current version is "
            f"{self.current_version}"
        )

    def __str__(self) -> str:
        return self.message
