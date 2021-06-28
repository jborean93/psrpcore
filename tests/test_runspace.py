# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import psrpcore

from psrpcore.types import (
    ApartmentState,
    HostMethodIdentifier,
    ErrorCategoryInfo,
    ErrorRecord,
    NETException,
    PSGuid,
    PSThreadOptions,
    RunspacePoolState,
)

from .conftest import get_runspace_pair


def test_open_runspacepool():
    client = psrpcore.RunspacePool()
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
    assert server.runspace_id == client.runspace_id

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
    client = psrpcore.RunspacePool()
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
    server.format_event(1, "source id", sender="pool", message_data=True)
    client.receive_data(server.data_to_send())
    event = client.next_event()

    assert isinstance(event, psrpcore.UserEventEvent)
    assert event.ps_object["PSEventArgs.ComputerName"] is not None
    assert event.ps_object["PSEventArgs.EventIdentifier"] == 1
    assert event.ps_object["PSEventArgs.MessageData"] is True
    assert event.ps_object["PSEventArgs.RunspaceId"] == client.runspace_id
    assert event.ps_object["PSEventArgs.Sender"] == "pool"
    assert event.ps_object["PSEventArgs.SourceArgs"] == []
    assert event.ps_object["PSEventArgs.SourceIdentifier"] == "source id"
    assert event.ps_object["PSEventArgs.TimeGenerated"] is not None
