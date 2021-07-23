# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import uuid

from psrpcore import _events as events
from psrpcore.types import (
    PipelineState,
    PSInvocationState,
    PSRPMessageType,
    RunspaceAvailability,
    RunspacePoolState,
    RunspacePoolStateMsg,
)


def test_create_pipeline_state_event():
    msg = PipelineState(PipelineState=PSInvocationState.Completed)
    event = events.PSRPEvent.create(PSRPMessageType.PipelineState, msg, uuid.UUID(int=0), uuid.UUID(int=0))
    assert isinstance(event, events.PipelineStateEvent)
    assert event.state == PSInvocationState.Completed
    assert event.reason is None


def test_runspace_availability_set():
    msg = RunspaceAvailability(SetMinMaxRunspacesResponse=True, ci=1)
    event = events.PSRPEvent.create(PSRPMessageType.RunspaceAvailability, msg, uuid.UUID(int=0), None)
    assert isinstance(event, events.SetRunspaceAvailabilityEvent)
    assert event.success == True


def test_runspace_availability_get():
    msg = RunspaceAvailability(SetMinMaxRunspacesResponse=10, ci=1)
    event = events.PSRPEvent.create(PSRPMessageType.RunspaceAvailability, msg, uuid.UUID(int=0), None)
    assert isinstance(event, events.GetRunspaceAvailabilityEvent)
    assert event.count == 10


def test_runspace_pool_state_event():
    msg = RunspacePoolStateMsg(RunspaceState=RunspacePoolState.Opened)
    event = events.PSRPEvent.create(PSRPMessageType.RunspacePoolState, msg, uuid.UUID(int=0), None)
    assert isinstance(event, events.RunspacePoolStateEvent)
    assert event.state == RunspacePoolState.Opened
    assert event.reason is None
