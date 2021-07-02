# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import re

import pytest

import psrpcore
from psrpcore.types import (
    ApartmentState,
    ErrorCategoryInfo,
    ErrorRecord,
    HostMethodIdentifier,
    NETException,
    PSThreadOptions,
    RunspacePoolState,
)

from .conftest import get_runspace_pair


def test_open_runspacepool():
    client = psrpcore.ClientRunspacePool()
    server = psrpcore.ServerRunspacePool()
    assert client.state == RunspacePoolState.BeforeOpen
    assert server.state == RunspacePoolState.BeforeOpen

    client.open()
    assert client.state == RunspacePoolState.Opening

    first = client.data_to_send()
    assert len(first.data) > 0
    assert first.stream_type == psrpcore.StreamType.default
    assert first.pipeline_id is None
    assert client.state == RunspacePoolState.NegotiationSent

    assert client.data_to_send() is None

    server.receive_data(first)
    session_cap = server.next_event()
    assert isinstance(session_cap, psrpcore.SessionCapabilityEvent)
    assert session_cap.ps_object.PSVersion == server.their_capability.PSVersion
    assert session_cap.ps_object.SerializationVersion == server.their_capability.SerializationVersion
    assert session_cap.ps_object.protocolversion == server.their_capability.protocolversion
    assert client.state == RunspacePoolState.NegotiationSent
    assert server.state == RunspacePoolState.NegotiationSucceeded
    assert server.runspace_pool_id == client.runspace_pool_id

    second = server.data_to_send()
    assert len(second.data) > 0
    assert second.stream_type == psrpcore.StreamType.default
    assert second.pipeline_id is None

    client.receive_data(second)
    session_cap = client.next_event()
    assert isinstance(session_cap, psrpcore.SessionCapabilityEvent)
    assert session_cap.ps_object.PSVersion == client.their_capability.PSVersion
    assert session_cap.ps_object.SerializationVersion == client.their_capability.SerializationVersion
    assert session_cap.ps_object.protocolversion == client.their_capability.protocolversion
    assert client.state == RunspacePoolState.NegotiationSucceeded
    assert server.state == RunspacePoolState.NegotiationSucceeded

    init_runspace_pool = server.next_event()
    assert isinstance(init_runspace_pool, psrpcore.InitRunspacePoolEvent)
    assert init_runspace_pool.ps_object.ApartmentState == ApartmentState.Unknown
    assert init_runspace_pool.ps_object.ApplicationArguments == {}
    assert init_runspace_pool.ps_object.HostInfo._isHostNull
    assert init_runspace_pool.ps_object.HostInfo._isHostRawUINull
    assert init_runspace_pool.ps_object.HostInfo._isHostUINull
    assert init_runspace_pool.ps_object.HostInfo._useRunspaceHost
    assert init_runspace_pool.ps_object.MaxRunspaces == 1
    assert init_runspace_pool.ps_object.MinRunspaces == 1
    assert init_runspace_pool.ps_object.PSThreadOptions == PSThreadOptions.Default
    assert client.state == RunspacePoolState.NegotiationSucceeded
    assert server.state == RunspacePoolState.Opened

    assert server.next_event() is None

    third = server.data_to_send()
    assert len(third.data) > 0
    assert third.stream_type == psrpcore.StreamType.default
    assert third.pipeline_id is None

    assert server.data_to_send() is None

    client.receive_data(third)
    private_data = client.next_event()
    assert isinstance(private_data, psrpcore.ApplicationPrivateDataEvent)
    assert private_data.ps_object.ApplicationPrivateData == {}
    assert client.application_private_data == {}
    assert client.state == RunspacePoolState.NegotiationSucceeded
    assert server.state == RunspacePoolState.Opened

    runspace_state = client.next_event()
    assert isinstance(runspace_state, psrpcore.RunspacePoolStateEvent)
    assert client.state == RunspacePoolState.Opened
    assert server.state == RunspacePoolState.Opened

    assert client.next_event() is None

    assert client.data_to_send() is None


def test_open_runspacepool_small():
    client = psrpcore.ClientRunspacePool()
    server = psrpcore.ServerRunspacePool()
    assert client.state == RunspacePoolState.BeforeOpen
    assert server.state == RunspacePoolState.BeforeOpen

    client.open()
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.BeforeOpen

    first = client.data_to_send(60)
    assert len(first.data) == 60
    assert first.stream_type == psrpcore.StreamType.default
    assert first.pipeline_id is None

    server.receive_data(first)
    assert server.next_event() is None
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.BeforeOpen

    server.receive_data(client.data_to_send(60))
    assert server.next_event() is None
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.BeforeOpen

    server.receive_data(client.data_to_send(60))
    assert server.next_event() is None
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.BeforeOpen

    server.receive_data(client.data_to_send(60))
    assert server.next_event() is None
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.BeforeOpen

    server.receive_data(client.data_to_send(60))
    assert server.next_event() is None
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.BeforeOpen

    server.receive_data(client.data_to_send(60))
    session_cap = server.next_event()
    assert isinstance(session_cap, psrpcore.SessionCapabilityEvent)
    assert client.state == RunspacePoolState.NegotiationSent
    assert server.state == RunspacePoolState.NegotiationSucceeded
    assert server.next_event() is None

    client.receive_data(server.data_to_send())
    assert server.data_to_send() is None
    session_cap = client.next_event()
    assert isinstance(session_cap, psrpcore.SessionCapabilityEvent)
    assert client.state == RunspacePoolState.NegotiationSucceeded
    assert server.state == RunspacePoolState.NegotiationSucceeded
    assert client.next_event() is None

    server.receive_data(client.data_to_send())
    init_runspace = server.next_event()
    assert isinstance(init_runspace, psrpcore.InitRunspacePoolEvent)
    assert client.state == RunspacePoolState.NegotiationSucceeded
    assert server.state == RunspacePoolState.Opened

    client.receive_data(server.data_to_send())
    assert server.data_to_send() is None
    private_data = client.next_event()
    assert isinstance(private_data, psrpcore.ApplicationPrivateDataEvent)
    assert client.state == RunspacePoolState.NegotiationSucceeded
    assert server.state == RunspacePoolState.Opened

    runspace_state = client.next_event()
    assert isinstance(runspace_state, psrpcore.RunspacePoolStateEvent)
    assert client.state == RunspacePoolState.Opened
    assert server.state == RunspacePoolState.Opened
    assert client.next_event() is None


def test_runspace_pool_set_runspaces():
    client, server = get_runspace_pair(2, 4)
    assert client.min_runspaces == 2
    assert client.max_runspaces == 4
    assert server.min_runspaces == 2
    assert server.max_runspaces == 4

    actual_ci = client.set_min_runspaces(3)
    assert actual_ci == 1
    assert client.min_runspaces == 2  # Won't change until it receives confirmation form server

    server.receive_data(client.data_to_send())
    min_event = server.next_event()
    assert isinstance(min_event, psrpcore.SetMinRunspacesEvent)
    assert min_event.ps_object.MinRunspaces == 3
    assert min_event.ps_object.ci == 1
    assert server.min_runspaces == 3
    assert client.min_runspaces == 2

    client.receive_data(server.data_to_send())
    resp_event = client.next_event()
    assert isinstance(resp_event, psrpcore.SetRunspaceAvailabilityEvent)
    assert resp_event.success is True
    assert resp_event.ps_object.ci == 1
    assert resp_event.ps_object.SetMinMaxRunspacesResponse is True
    assert server.min_runspaces == 3
    assert client.min_runspaces == 3

    actual_ci = client.set_max_runspaces(5)
    assert actual_ci == 2
    assert client.max_runspaces == 4
    assert server.max_runspaces == 4

    server.receive_data(client.data_to_send())
    max_event = server.next_event()
    assert isinstance(max_event, psrpcore.SetMaxRunspacesEvent)
    assert max_event.ps_object.MaxRunspaces == 5
    assert max_event.ps_object.ci == 2
    assert server.max_runspaces == 5
    assert client.max_runspaces == 4

    client.receive_data(server.data_to_send())
    resp_event = client.next_event()
    assert isinstance(resp_event, psrpcore.SetRunspaceAvailabilityEvent)
    assert resp_event.success is True
    assert resp_event.ps_object.ci == 2
    assert resp_event.ps_object.SetMinMaxRunspacesResponse is True
    assert server.max_runspaces == 5
    assert client.max_runspaces == 5

    actual_ci = client.get_available_runspaces()
    server.receive_data(client.data_to_send())
    get_avail = server.next_event()
    assert actual_ci == 3
    assert isinstance(get_avail, psrpcore.GetAvailableRunspacesEvent)
    assert get_avail.ps_object.ci == 3

    client.receive_data(server.data_to_send())
    runspace_avail = client.next_event()
    assert isinstance(runspace_avail, psrpcore.GetRunspaceAvailabilityEvent)
    assert runspace_avail.count == 5
    assert runspace_avail.ps_object.ci == 3
    assert runspace_avail.ps_object.SetMinMaxRunspacesResponse == 5


def test_runspace_host_call():
    client, server = get_runspace_pair()
    actual_ci = server.host_call(HostMethodIdentifier.WriteLine1, ["line"])
    client.receive_data(server.data_to_send())
    host_call = client.next_event()

    assert actual_ci == 1
    assert isinstance(host_call, psrpcore.RunspacePoolHostCallEvent)
    assert host_call.ps_object.ci == 1
    assert host_call.ps_object.mi == HostMethodIdentifier.WriteLine1
    assert host_call.ps_object.mp == ["line"]

    actual_ci = server.host_call(HostMethodIdentifier.ReadLine)
    client.receive_data(server.data_to_send())
    host_call = client.next_event()

    assert actual_ci == 2
    assert isinstance(host_call, psrpcore.RunspacePoolHostCallEvent)
    assert host_call.ps_object.ci == 2
    assert host_call.ps_object.mi == HostMethodIdentifier.ReadLine
    assert host_call.ps_object.mp is None

    error = ErrorRecord(
        Exception=NETException("ReadLine error"),
        CategoryInfo=ErrorCategoryInfo(
            Reason="Exception",
        ),
        FullyQualifiedErrorId="RemoteHostExecutionException",
    )
    client.host_response(2, error_record=error)
    server.receive_data(client.data_to_send())
    host_resp = server.next_event()

    assert isinstance(host_resp, psrpcore.RunspacePoolHostResponseEvent)
    assert host_resp.ps_object.ci == 2
    assert host_resp.ps_object.mi == HostMethodIdentifier.ReadLine
    assert isinstance(host_resp.ps_object.me, ErrorRecord)
    assert str(host_resp.ps_object.me) == "ReadLine error"
    assert host_resp.ps_object.me.Exception.Message == "ReadLine error"
    assert host_resp.ps_object.me.FullyQualifiedErrorId == "RemoteHostExecutionException"
    assert host_resp.ps_object.me.CategoryInfo.Reason == "Exception"


def test_runspace_reset():
    client, server = get_runspace_pair()
    actual_ci = client.reset_runspace_state()
    server.receive_data(client.data_to_send())
    reset = server.next_event()

    assert actual_ci == 1
    assert isinstance(reset, psrpcore.ResetRunspaceStateEvent)
    assert reset.ps_object.ci == 1

    assert server.data_to_send() is None


def test_runspace_user_event():
    client, server = get_runspace_pair()
    server.send_event(1, "source id", sender="pool", message_data=True)
    client.receive_data(server.data_to_send())
    event = client.next_event()

    assert isinstance(event, psrpcore.UserEventEvent)
    assert event.ps_object["PSEventArgs.ComputerName"] is not None
    assert event.ps_object["PSEventArgs.EventIdentifier"] == 1
    assert event.ps_object["PSEventArgs.MessageData"] is True
    assert event.ps_object["PSEventArgs.RunspaceId"] == client.runspace_pool_id
    assert event.ps_object["PSEventArgs.Sender"] == "pool"
    assert event.ps_object["PSEventArgs.SourceArgs"] == []
    assert event.ps_object["PSEventArgs.SourceIdentifier"] == "source id"
    assert event.ps_object["PSEventArgs.TimeGenerated"] is not None


def test_runspace_too_little_fragment_length():
    client = psrpcore.ClientRunspacePool()
    client.open()

    with pytest.raises(ValueError, match="amount must be 22 or larger to fit a PSRP fragment"):
        client.data_to_send(21)

    actual = client.data_to_send(22)
    assert isinstance(actual, psrpcore.PSRPPayload)
    assert len(actual.data) == 22


def test_receive_fragment_out_of_order():
    client = psrpcore.ClientRunspacePool()
    client.open()
    first = client.data_to_send(120)
    second = client.data_to_send(120)
    third = client.data_to_send()

    server = psrpcore.ServerRunspacePool()
    server.receive_data(first)
    server.receive_data(third)
    server.receive_data(second)

    with pytest.raises(psrpcore.PSRPCoreError, match="Expecting fragment with a fragment id of 1 not 2"):
        server.next_event()

    # Verify we can recover
    server.receive_data(second)
    server.receive_data(third)

    server = psrpcore.ServerRunspacePool()
    server.receive_data(second)

    with pytest.raises(psrpcore.PSRPCoreError, match="Expecting fragment with a fragment id of 0 not 1"):
        server.next_event()


def test_reset_invalid_state():
    client = psrpcore.ClientRunspacePool()
    pipe = psrpcore.ClientPowerShell(client)
    pipe.add_command("test")

    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Connecting, RunspacePoolState.Opened, "
        "RunspacePoolState.Opening, RunspacePoolState.NegotiationSent, RunspacePoolState.NegotiationSucceeded' "
        "to send PSRP message, current state is RunspacePoolState.BeforeOpen"
    )
    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        pipe.invoke()


def test_prepare_message_with_invalid_type():
    client = get_runspace_pair()[0]

    with pytest.raises(ValueError, match="message_type must be specified when the message is not a PSRP message"):
        client.prepare_message(ApartmentState.STA)


def test_unhandled_message_received(caplog):
    client = psrpcore.ClientRunspacePool()
    client.open()
    client.receive_data(client.data_to_send())

    cap_event = client.next_event()
    init_event = client.next_event()
    assert isinstance(cap_event, psrpcore.SessionCapabilityEvent)
    assert isinstance(init_event, psrpcore.InitRunspacePoolEvent)

    assert re.match(r"WARNING.*Received PSRPMessageType\.InitRunspacePool but could not process it", caplog.text)
