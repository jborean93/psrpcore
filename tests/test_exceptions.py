# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

from psrpcore import _exceptions as exp
from psrpcore.types import PSInvocationState, PSVersion, RunspacePoolState


def test_missing_cipher():
    missing_cipher = exp.MissingCipherError()
    str(missing_cipher) == "Cannot (de)serialize a secure string without an exchanged session key"


def test_invalid_runspace_pool_state():
    invalid = exp.InvalidRunspacePoolState("open pool", RunspacePoolState.BeforeOpen, [RunspacePoolState.Opened])
    assert str(invalid) == (
        "Runspace Pool state must be one of 'RunspacePoolState.Opened' to open pool, "
        "current state is RunspacePoolState.BeforeOpen"
    )


def test_invalid_pipeline_state():
    invalid = exp.InvalidPipelineState(
        "open pipe", PSInvocationState.Completed, [PSInvocationState.Running, PSInvocationState.Stopped]
    )
    assert str(invalid) == (
        "Pipeline state must be one of 'PSInvocationState.Running, PSInvocationState.Stopped' to open pipe, "
        "current state is PSInvocationState.Completed"
    )


def test_invalid_protocol_version():
    invalid = exp.InvalidProtocolVersion("reset runspace", PSVersion("1.2"), PSVersion("1.3"))
    assert str(invalid) == "reset runspace requires a protocol version of 1.3, current version is 1.2"
