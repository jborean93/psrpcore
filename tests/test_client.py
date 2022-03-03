# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import re
import threading

import pytest

import psrpcore
from psrpcore.types import (
    ApartmentState,
    CommandTypes,
    ConsoleColor,
    Coordinates,
    DebugRecord,
    ErrorCategory,
    ErrorCategoryInfo,
    ErrorRecord,
    HostDefaultData,
    HostInfo,
    HostMethodIdentifier,
    InformationRecord,
    NETException,
    PipelineResultTypes,
    ProgressRecord,
    ProgressRecordType,
    PSCustomObject,
    PSInt,
    PSInvocationState,
    PSSecureString,
    PSString,
    PSThreadOptions,
    RemoteStreamOptions,
    RunspacePoolState,
    Size,
    VerboseRecord,
    WarningRecord,
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
    assert client.state == RunspacePoolState.Opening

    assert client.data_to_send() is None

    server.receive_data(first)
    session_cap = server.next_event()
    assert isinstance(session_cap, psrpcore.SessionCapabilityEvent)
    assert session_cap.ps_version == server.their_capability.PSVersion
    assert session_cap.serialization_version == server.their_capability.SerializationVersion
    assert session_cap.protocol_version == server.their_capability.protocolversion
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.Opening
    assert server.runspace_pool_id == client.runspace_pool_id

    second = server.data_to_send()
    assert len(second.data) > 0
    assert second.stream_type == psrpcore.StreamType.default
    assert second.pipeline_id is None

    client.receive_data(second)
    session_cap = client.next_event()
    assert isinstance(session_cap, psrpcore.SessionCapabilityEvent)
    assert session_cap.ps_version == client.their_capability.PSVersion
    assert session_cap.serialization_version == client.their_capability.SerializationVersion
    assert session_cap.protocol_version == client.their_capability.protocolversion
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.Opening

    init_runspace_pool = server.next_event()
    assert isinstance(init_runspace_pool, psrpcore.InitRunspacePoolEvent)
    assert (
        repr(init_runspace_pool) == f"<InitRunspacePoolEvent runspace_pool_id={client.runspace_pool_id!r} "
        f"min_runspaces=1 max_runspaces=1 ps_thread_options=<PSThreadOptions.Default: 0> "
        f"apartment_state=<ApartmentState.Unknown: 2> "
        f"host_info=HostInfo(IsHostNull=True, IsHostUINull=True, IsHostRawUINull=True, UseRunspaceHost=True, "
        f"HostDefaultData=None) application_arguments={{}}>"
    )
    assert init_runspace_pool.apartment_state == ApartmentState.Unknown
    assert init_runspace_pool.application_arguments == {}
    assert init_runspace_pool.host_info.IsHostNull
    assert init_runspace_pool.host_info.IsHostRawUINull
    assert init_runspace_pool.host_info.IsHostUINull
    assert init_runspace_pool.host_info.UseRunspaceHost
    assert init_runspace_pool.max_runspaces == 1
    assert init_runspace_pool.min_runspaces == 1
    assert init_runspace_pool.ps_thread_options == PSThreadOptions.Default
    assert client.state == RunspacePoolState.Opening
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
    assert private_data.data == {
        "PSVersionTable": {
            "PSRemotingProtocolVersion": psrpcore.types.PSVersion("2.3"),
            "SerializationVersion": psrpcore.types.PSVersion("1.1.0.1"),
        }
    }
    assert (
        repr(private_data) == f"<ApplicationPrivateDataEvent runspace_pool_id={client.runspace_pool_id!r}: "
        f"{{'PSVersionTable': {{'PSRemotingProtocolVersion': PSVersion(major=2, minor=3), 'SerializationVersion': "
        f"PSVersion(major=1, minor=1, build=0, revision=1)}}}}>"
    )
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.Opened

    runspace_state = client.next_event()
    assert isinstance(runspace_state, psrpcore.RunspacePoolStateEvent)
    assert repr(runspace_state) == (
        f"<RunspacePoolStateEvent runspace_pool_id={client.runspace_pool_id!r} state=<RunspacePoolState.Opened: 2> "
        f"reason=None>"
    )
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
    assert server.state == RunspacePoolState.Opening

    server.receive_data(client.data_to_send(60))
    assert server.next_event() is None
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.Opening

    server.receive_data(client.data_to_send(60))
    assert server.next_event() is None
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.Opening

    server.receive_data(client.data_to_send(60))
    assert server.next_event() is None
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.Opening

    server.receive_data(client.data_to_send(60))
    assert server.next_event() is None
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.Opening

    server.receive_data(client.data_to_send(60))
    session_cap = server.next_event()
    assert isinstance(session_cap, psrpcore.SessionCapabilityEvent)
    assert repr(session_cap) == (
        f"<SessionCapabilityEvent runspace_pool_id={client.runspace_pool_id!r} ps_version=2.0 protocol_version=2.3 "
        f"serialization_version=1.1.0.1>"
    )
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.Opening
    assert server.next_event() is None

    client.receive_data(server.data_to_send())
    assert server.data_to_send() is None
    session_cap = client.next_event()
    assert isinstance(session_cap, psrpcore.SessionCapabilityEvent)
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.Opening
    assert client.next_event() is None

    server.receive_data(client.data_to_send())
    init_runspace = server.next_event()
    assert isinstance(init_runspace, psrpcore.InitRunspacePoolEvent)
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.Opened

    client.receive_data(server.data_to_send())
    assert server.data_to_send() is None
    private_data = client.next_event()
    assert isinstance(private_data, psrpcore.ApplicationPrivateDataEvent)
    assert client.state == RunspacePoolState.Opening
    assert server.state == RunspacePoolState.Opened

    runspace_state = client.next_event()
    assert isinstance(runspace_state, psrpcore.RunspacePoolStateEvent)
    assert client.state == RunspacePoolState.Opened
    assert server.state == RunspacePoolState.Opened
    assert client.next_event() is None


def test_runspace_pool_get_runspace_availability():
    client, server = get_runspace_pair(2, 4)

    actual_ci = client.get_available_runspaces()
    server.receive_data(client.data_to_send())
    get_avail = server.next_event()
    assert isinstance(get_avail, psrpcore.GetAvailableRunspacesEvent)
    assert (
        repr(get_avail) == f"<GetAvailableRunspacesEvent runspace_pool_id={client.runspace_pool_id!r} "
        f"ci={actual_ci}>"
    )
    assert get_avail.ci is not None

    with pytest.raises(psrpcore.PSRPCoreError, match=r"Cannot respond to \d+, not requested by client."):
        server.runspace_availability_response(get_avail.ci + 10, 3)

    with pytest.raises(psrpcore.PSRPCoreError, match="Response for this event expects an int not str"):
        server.runspace_availability_response(get_avail.ci, "3")

    server.runspace_availability_response(get_avail.ci, 3)

    client.receive_data(server.data_to_send())
    runspace_avail = client.next_event()
    assert isinstance(runspace_avail, psrpcore.GetRunspaceAvailabilityEvent)
    assert repr(runspace_avail) == (
        f"<GetRunspaceAvailabilityEvent runspace_pool_id={client.runspace_pool_id!r} ci={get_avail.ci} count=3>"
    )
    assert runspace_avail.ci is not None
    assert runspace_avail.count == 3


def test_runspace_host_call():
    client, server = get_runspace_pair()

    s_host = psrpcore.ServerHostRequestor(server)
    actual_ci = s_host.write_line("line")
    assert actual_ci is None
    client.receive_data(server.data_to_send())
    host_call = client.next_event()

    assert isinstance(host_call, psrpcore.RunspacePoolHostCallEvent)
    assert repr(host_call) == (
        f"<RunspacePoolHostCallEvent runspace_pool_id={client.runspace_pool_id!r} ci=-100 "
        f"method_identifier=<HostMethodIdentifier.WriteLine2: 16> method_parameters=['line']>"
    )
    assert host_call.ci == -100
    assert host_call.method_identifier == HostMethodIdentifier.WriteLine2
    assert host_call.method_parameters == ["line"]

    actual_ci = s_host.read_line()
    client.receive_data(server.data_to_send())
    host_call = client.next_event()

    assert actual_ci == 1
    assert isinstance(host_call, psrpcore.RunspacePoolHostCallEvent)
    assert host_call.ci == 1
    assert host_call.method_identifier == HostMethodIdentifier.ReadLine
    assert host_call.method_parameters == []

    error = ErrorRecord(
        Exception=NETException("ReadLine error"),
        CategoryInfo=ErrorCategoryInfo(
            Reason="Exception",
        ),
        FullyQualifiedErrorId="RemoteHostExecutionException",
    )
    client.host_response(1, error_record=error)
    server.receive_data(client.data_to_send())
    host_resp = server.next_event()

    assert isinstance(host_resp, psrpcore.RunspacePoolHostResponseEvent)
    assert repr(host_resp) == (
        f"<RunspacePoolHostResponseEvent runspace_pool_id={client.runspace_pool_id!r} ci=1 "
        f"method_identifier=<HostMethodIdentifier.ReadLine: 11> result=None error='ReadLine error'>"
    )
    assert host_resp.ci == 1
    assert host_resp.method_identifier == HostMethodIdentifier.ReadLine
    assert isinstance(host_resp.error, ErrorRecord)
    assert str(host_resp.error) == "ReadLine error"
    assert host_resp.error.Exception.Message == "ReadLine error"
    assert host_resp.error.FullyQualifiedErrorId == "RemoteHostExecutionException"
    assert host_resp.error.CategoryInfo.Reason == "Exception"


def test_runspace_reset():
    client, server = get_runspace_pair()
    actual_ci = client.reset_runspace_state()
    server.receive_data(client.data_to_send())
    reset = server.next_event()

    assert actual_ci == 1
    assert isinstance(reset, psrpcore.ResetRunspaceStateEvent)
    assert repr(reset) == f"<ResetRunspaceStateEvent runspace_pool_id={client.runspace_pool_id!r} ci=1>"
    assert reset.ci == 1

    server.runspace_availability_response(actual_ci, True)
    client.receive_data(server.data_to_send())
    avail = client.next_event()
    assert isinstance(avail, psrpcore.SetRunspaceAvailabilityEvent)
    assert (
        repr(avail) == f"<SetRunspaceAvailabilityEvent runspace_pool_id={client.runspace_pool_id!r} ci=1 success=True>"
    )
    assert avail.success is True


def test_runspace_user_event():
    client, server = get_runspace_pair()
    server.send_event(1, "source id", sender="pool", message_data=True)
    client.receive_data(server.data_to_send())
    event = client.next_event()

    assert isinstance(event, psrpcore.UserEventEvent)
    assert repr(event) == f"<UserEventEvent runspace_pool_id={client.runspace_pool_id!r} pipeline_id=None>"
    assert isinstance(event.event, psrpcore.types.UserEvent)
    assert event.event.ComputerName is not None
    assert event.event.EventIdentifier == 1
    assert event.event.MessageData is True
    assert event.event.RunspaceId == client.runspace_pool_id
    assert event.event.Sender == "pool"
    assert event.event.SourceArgs == []
    assert event.event.SourceIdentifier == "source id"
    assert event.event.TimeGenerated is not None


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


def test_open_already_opened_client():
    client = get_runspace_pair()[0]
    client.open()
    assert client.data_to_send() is None
    assert client.state == RunspacePoolState.Opened


def test_open_closed_client():
    client = get_runspace_pair()[0]
    client.close()

    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.BeforeOpen' to open a Runspace Pool, current state is "
        "RunspacePoolState.Closed"
    )
    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        client.open()


def test_connect_with_already_opened_client():
    client = get_runspace_pair()[0]
    client.connect()

    assert client.data_to_send() is None


def test_connect_fail_with_closed_runspace():
    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.BeforeOpen' to connect to Runspace Pool, current "
        "state is RunspacePoolState.Closed"
    )
    client = get_runspace_pair()[0]
    client.close()

    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        client.connect()


def test_disconnect_fail_not_opened():
    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Opened, RunspacePoolState.Disconnecting, "
        "RunspacePoolState.Disconnected' to disconnect a Runspace Pool, current state is RunspacePoolState.BeforeOpen"
    )

    client = psrpcore.ClientRunspacePool()

    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        client.disconnect()


def test_disconnect_and_reconnect_runspace_pool():
    client, server = get_runspace_pair()

    assert client.state == RunspacePoolState.Opened
    assert server.state == RunspacePoolState.Opened

    client.begin_disconnect()
    server.begin_disconnect()
    assert client.state == RunspacePoolState.Disconnecting
    assert server.state == RunspacePoolState.Disconnecting

    client.disconnect()
    server.disconnect()

    assert client.state == RunspacePoolState.Disconnected
    assert server.state == RunspacePoolState.Disconnected

    client.reconnect()
    server.reconnect()

    assert client.state == RunspacePoolState.Opened
    assert client.state == RunspacePoolState.Opened

    # Assert it doesn't fail when already connected
    client.reconnect()
    server.reconnect()


def test_reconnect_invalid_state():
    client = get_runspace_pair()[0]

    client.close()

    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Disconnected, RunspacePoolState.Opened' to "
        "reconnect to a Runspace Pool, current state is RunspacePoolState.Closed"
    )
    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        client.reconnect()


def test_disconnect_and_connect_runspace_pool():
    client, server = get_runspace_pair()

    assert client.state == RunspacePoolState.Opened
    assert server.state == RunspacePoolState.Opened

    client.disconnect()
    server.disconnect()

    assert client.state == RunspacePoolState.Disconnected
    assert server.state == RunspacePoolState.Disconnected

    client = psrpcore.ClientRunspacePool(runspace_pool_id=client.runspace_pool_id)
    assert client.state == RunspacePoolState.BeforeOpen

    server.next_event()
    client.connect()
    server.connect()
    assert client.state == RunspacePoolState.Connecting
    assert server.state == RunspacePoolState.Connecting

    server.receive_data(client.data_to_send())
    cap = server.next_event()
    assert isinstance(cap, psrpcore.SessionCapabilityEvent)
    assert cap.runspace_pool_id == client.runspace_pool_id
    assert client.state == RunspacePoolState.Connecting
    assert server.state == RunspacePoolState.Connecting

    connect = server.next_event()
    assert isinstance(connect, psrpcore.ConnectRunspacePoolEvent)
    assert (
        repr(connect) == f"<ConnectRunspacePoolEvent runspace_pool_id={client.runspace_pool_id!r} "
        "min_runspaces=None max_runspaces=None>"
    )
    assert connect.runspace_pool_id == client.runspace_pool_id
    assert client.state == RunspacePoolState.Connecting
    assert server.state == RunspacePoolState.Opened

    client.receive_data(server.data_to_send())
    init = client.next_event()
    assert isinstance(init, psrpcore.RunspacePoolInitDataEvent)
    assert repr(init) == (
        f"<RunspacePoolInitDataEvent runspace_pool_id={client.runspace_pool_id!r} min_runspaces=1 max_runspaces=1>"
    )
    assert client.state == RunspacePoolState.Connecting
    assert server.state == RunspacePoolState.Opened

    app_data = client.next_event()
    assert isinstance(app_data, psrpcore.ApplicationPrivateDataEvent)
    assert client.state == RunspacePoolState.Opened
    assert server.state == RunspacePoolState.Opened


def test_fail_to_close_with_pipelines():
    client = get_runspace_pair()[0]
    ps = psrpcore.ClientPowerShell(client)

    with pytest.raises(psrpcore.PSRPCoreError, match="Must close existing pipelines before closing the pool"):
        client.close()


def test_fail_to_close_invalid_state():
    client = psrpcore.ClientRunspacePool()

    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Closed, RunspacePoolState.Closing, "
        "RunspacePoolState.Opened' to close Runspace Pool, current state is RunspacePoolState.BeforeOpen"
    )
    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        client.close()


def test_get_available_runspaces_invalid_state():
    client = get_runspace_pair()[0]
    client.close()

    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Opened' to get available Runspaces, current state "
        "is RunspacePoolState.Closed"
    )
    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        client.get_available_runspaces()


def test_exchange_key_invalid_state():
    client = get_runspace_pair()[0]
    client.close()

    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Opened' to start session key exchange, current state "
        "is RunspacePoolState.Closed"
    )
    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        client.exchange_key()


def test_respond_host_state():
    client = get_runspace_pair()[0]
    client.close()

    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Opened' to respond to host call, current state "
        "is RunspacePoolState.Closed"
    )
    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        client.host_response(0)


def test_reset_runspace_pool_invalid_state():
    client = get_runspace_pair()[0]
    client.close()

    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Opened' to reset Runspace Pool state, current state "
        "is RunspacePoolState.Closed"
    )
    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        client.reset_runspace_state()


def test_reset_runspace_pool_invalid_protocol():
    client = psrpcore.ClientRunspacePool()

    expected = re.escape("reset Runspace Pool state requires a protocol version of 2.3, current version is 2.0")
    with pytest.raises(psrpcore.InvalidProtocolVersion, match=expected):
        client.reset_runspace_state()


def test_set_max_runspaces():
    client, server = get_runspace_pair()

    ci = client.set_max_runspaces(5)
    assert ci is not None
    assert client.max_runspaces == 1

    server.receive_data(client.data_to_send())
    set_max = server.next_event()
    assert isinstance(set_max, psrpcore.SetMaxRunspacesEvent)
    assert repr(set_max) == f"<SetMaxRunspacesEvent runspace_pool_id={client.runspace_pool_id!r} ci={ci} count=5>"
    assert set_max.ci == ci
    assert set_max.count == 5
    assert server.max_runspaces == 1

    with pytest.raises(psrpcore.PSRPCoreError, match=r"Cannot respond to \d+, not requested by client."):
        server.runspace_availability_response(set_max.ci + 10, True)

    with pytest.raises(psrpcore.PSRPCoreError, match="Response for this event expects a bool not int"):
        server.runspace_availability_response(set_max.ci, 1)

    server.runspace_availability_response(set_max.ci, False)
    assert server.max_runspaces == 1

    client.receive_data(server.data_to_send())
    resp = client.next_event()
    assert isinstance(resp, psrpcore.SetRunspaceAvailabilityEvent)
    assert resp.ci == ci
    assert resp.success is False
    assert client.max_runspaces == 1

    ci = client.set_max_runspaces(5)
    assert ci is not None
    assert client.max_runspaces == 1

    server.receive_data(client.data_to_send())
    set_max = server.next_event()
    assert isinstance(set_max, psrpcore.SetMaxRunspacesEvent)
    assert set_max.ci == ci
    assert set_max.count == 5
    assert server.max_runspaces == 1

    server.runspace_availability_response(set_max.ci, True)
    assert server.max_runspaces == 5

    client.receive_data(server.data_to_send())
    resp = client.next_event()
    assert isinstance(resp, psrpcore.SetRunspaceAvailabilityEvent)
    assert resp.ci == ci
    assert resp.success is True
    assert client.max_runspaces == 5


def test_set_min_runspaces():
    client, server = get_runspace_pair(max_runspaces=2)

    ci = client.set_min_runspaces(2)
    assert ci is not None
    assert client.min_runspaces == 1

    server.receive_data(client.data_to_send())
    set_min = server.next_event()
    assert isinstance(set_min, psrpcore.SetMinRunspacesEvent)
    assert repr(set_min) == f"<SetMinRunspacesEvent runspace_pool_id={client.runspace_pool_id!r} ci={ci} count=2>"
    assert set_min.ci == ci
    assert set_min.count == 2
    assert server.min_runspaces == 1

    with pytest.raises(psrpcore.PSRPCoreError, match=r"Cannot respond to \d+, not requested by client."):
        server.runspace_availability_response(set_min.ci + 10, True)

    with pytest.raises(psrpcore.PSRPCoreError, match="Response for this event expects a bool not int"):
        server.runspace_availability_response(set_min.ci, 1)

    server.runspace_availability_response(set_min.ci, False)
    assert server.min_runspaces == 1

    client.receive_data(server.data_to_send())
    resp = client.next_event()
    assert isinstance(resp, psrpcore.SetRunspaceAvailabilityEvent)
    assert resp.ci == ci
    assert resp.success is False
    assert client.min_runspaces == 1

    ci = client.set_min_runspaces(2)
    assert ci is not None
    assert client.min_runspaces == 1

    server.receive_data(client.data_to_send())
    set_min = server.next_event()
    assert isinstance(set_min, psrpcore.SetMinRunspacesEvent)
    assert set_min.ci == ci
    assert set_min.count == 2
    assert server.min_runspaces == 1

    server.runspace_availability_response(set_min.ci, True)
    assert server.min_runspaces == 2

    client.receive_data(server.data_to_send())
    resp = client.next_event()
    assert isinstance(resp, psrpcore.SetRunspaceAvailabilityEvent)
    assert resp.ci == ci
    assert resp.success is True
    assert client.min_runspaces == 2


def test_set_min_max_before_open():
    client = psrpcore.ClientRunspacePool()
    assert client.set_max_runspaces(2) is None
    assert client.max_runspaces == 2

    assert client.set_min_runspaces(2) is None
    assert client.min_runspaces == 2


def test_set_min_max_to_same_value():
    client = get_runspace_pair()[0]
    assert client.set_max_runspaces(1) is None
    assert client.max_runspaces == 1

    assert client.set_min_runspaces(1) is None
    assert client.min_runspaces == 1


def test_pipeline_host_response_invalid_state():
    client = get_runspace_pair()[0]
    ps = psrpcore.ClientPowerShell(client)

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.Running' to response to pipeline host call, current "
        "state is PSInvocationState.NotStarted"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        ps.host_response(1, None)


def test_create_pipeline():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientPowerShell(client)
    assert c_pipeline.state == PSInvocationState.NotStarted

    with pytest.raises(ValueError, match="A command is required to invoke a PowerShell pipeline"):
        c_pipeline.start()

    c_pipeline.add_script("testing")
    c_pipeline.start()
    assert c_pipeline.state == PSInvocationState.Running

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.NotStarted, PSInvocationState.Stopped, "
        "PSInvocationState.Completed' to start a pipeline, current state is PSInvocationState.Running"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        c_pipeline.start()

    create_data = client.data_to_send()
    server.receive_data(create_data)
    with pytest.raises(psrpcore.PSRPCoreError, match="Failed to find pipeline for incoming event"):
        server.next_event()

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(create_data)
    create_pipeline = server.next_event()
    assert isinstance(create_pipeline, psrpcore.CreatePipelineEvent)
    assert repr(create_pipeline) == (
        f"<CreatePipelineEvent runspace_pool_id={client.runspace_pool_id!r} pipeline_id={c_pipeline.pipeline_id!r} "
        f"pipeline=<PowerShell add_to_history=False apartment_state=<ApartmentState.Unknown: 2> "
        f"commands=[<Command command_text='testing' is_script=True use_local_scope=None end_of_statement=True>] "
        f"history=None host=HostInfo(IsHostNull=True, IsHostUINull=True, IsHostRawUINull=True, UseRunspaceHost=True, "
        f"HostDefaultData=None) is_nested=False no_input=True remote_stream_options=<RemoteStreamOptions.none: 0> "
        f"redirect_shell_error_to_out=True>>"
    )
    assert isinstance(s_pipeline.metadata, psrpcore.PowerShell)
    assert create_pipeline.pipeline_id == c_pipeline.pipeline_id

    assert s_pipeline.runspace_pool == server
    assert s_pipeline.state == PSInvocationState.NotStarted
    assert len(server.pipeline_table) == 1
    assert server.pipeline_table[s_pipeline.pipeline_id] == s_pipeline

    pwsh = s_pipeline.metadata
    assert pwsh.add_to_history is False
    assert pwsh.apartment_state == ApartmentState.Unknown
    assert len(pwsh.commands) == 1
    assert pwsh.commands[0].command_text == "testing"
    assert pwsh.commands[0].end_of_statement is True
    assert pwsh.commands[0].is_script is True
    assert pwsh.commands[0].parameters == []
    assert pwsh.commands[0].use_local_scope is None
    assert pwsh.history is None
    assert isinstance(pwsh.host, HostInfo)
    assert pwsh.host.HostDefaultData is None
    assert pwsh.host.IsHostNull is True
    assert pwsh.host.IsHostRawUINull is True
    assert pwsh.host.IsHostUINull is True
    assert pwsh.host.UseRunspaceHost is True
    assert pwsh.is_nested is False
    assert pwsh.no_input is True

    assert pwsh.redirect_shell_error_to_out is True
    assert pwsh.remote_stream_options == RemoteStreamOptions.none

    s_pipeline.start()
    s_pipeline.write_output("output msg")
    s_pipeline.complete()

    client.receive_data(server.data_to_send())
    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == PSInvocationState.Running

    out = client.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert out.data == "output msg"

    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == PSInvocationState.Completed
    assert c_pipeline.state == PSInvocationState.Completed
    assert client.pipeline_table == {c_pipeline.pipeline_id: c_pipeline}
    assert server.pipeline_table == {s_pipeline.pipeline_id: s_pipeline}

    s_pipeline.close()
    assert server.pipeline_table == {}

    c_pipeline.close()
    assert client.pipeline_table == {}


def test_create_pipeline_host_data():
    client, server = get_runspace_pair()

    c_host_data = HostDefaultData(
        ForegroundColor=ConsoleColor.Red,
        BackgroundColor=ConsoleColor.White,
        CursorPosition=Coordinates(1, 2),
        WindowPosition=Coordinates(3, 4),
        CursorSize=5,
        BufferSize=Size(6, 7),
        WindowSize=Size(8, 9),
        MaxWindowSize=Size(10, 11),
        MaxPhysicalWindowSize=Size(12, 13),
        WindowTitle="Test Title",
    )
    c_host = HostInfo(
        UseRunspaceHost=False,
        IsHostNull=False,
        IsHostUINull=False,
        IsHostRawUINull=False,
        HostDefaultData=c_host_data,
    )

    c_pipeline = psrpcore.ClientPowerShell(client, host=c_host)
    c_pipeline.add_script("testing")
    c_pipeline.start()

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()
    s_host = s_pipeline.metadata.host

    assert isinstance(s_host, HostInfo)
    assert s_host.IsHostNull is False
    assert s_host.IsHostUINull is False
    assert s_host.IsHostRawUINull is False
    assert s_host.UseRunspaceHost is False
    assert isinstance(s_host.HostDefaultData, HostDefaultData)
    assert s_host.HostDefaultData.ForegroundColor == ConsoleColor.Red
    assert s_host.HostDefaultData.BackgroundColor == ConsoleColor.White
    assert s_host.HostDefaultData.CursorPosition.X == 1
    assert s_host.HostDefaultData.CursorPosition.Y == 2
    assert s_host.HostDefaultData.WindowPosition.X == 3
    assert s_host.HostDefaultData.WindowPosition.Y == 4
    assert s_host.HostDefaultData.CursorSize == 5
    assert s_host.HostDefaultData.BufferSize.Width == 6
    assert s_host.HostDefaultData.BufferSize.Height == 7
    assert s_host.HostDefaultData.WindowSize.Width == 8
    assert s_host.HostDefaultData.WindowSize.Height == 9
    assert s_host.HostDefaultData.MaxWindowSize.Width == 10
    assert s_host.HostDefaultData.MaxWindowSize.Height == 11
    assert s_host.HostDefaultData.MaxPhysicalWindowSize.Width == 12
    assert s_host.HostDefaultData.MaxPhysicalWindowSize.Height == 13
    assert s_host.HostDefaultData.WindowTitle == "Test Title"


def test_pipeline_multiple_commands():
    client, server = get_runspace_pair()
    c_pipeline = psrpcore.ClientPowerShell(client)

    c_pipeline.add_command("Get-ChildItem")
    c_pipeline.add_command("Select-Object", use_local_scope=True)
    complex_command = psrpcore.Command("Format-List", use_local_scope=False)
    complex_command.redirect_error(PipelineResultTypes.Output)
    c_pipeline.add_command(complex_command)

    with pytest.raises(TypeError, match="Cannot set use_local_scope with Command"):
        c_pipeline.add_command(complex_command, use_local_scope=False)

    c_pipeline.start()

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()
    pwsh = s_pipeline.metadata

    assert len(pwsh.commands) == 3
    assert str(pwsh.commands[0]) == "Get-ChildItem"
    assert (
        repr(pwsh.commands[0])
        == "<Command command_text='Get-ChildItem' is_script=False use_local_scope=None end_of_statement=False>"
    )
    assert pwsh.commands[0].command_text == "Get-ChildItem"
    assert pwsh.commands[0].end_of_statement is False
    assert pwsh.commands[0].use_local_scope is None
    assert pwsh.commands[0].merge_error == PipelineResultTypes.none
    assert pwsh.commands[0].merge_my == PipelineResultTypes.none
    assert pwsh.commands[0].merge_to == PipelineResultTypes.none
    assert str(pwsh.commands[1]) == "Select-Object"
    assert (
        repr(pwsh.commands[1])
        == "<Command command_text='Select-Object' is_script=False use_local_scope=True end_of_statement=False>"
    )
    assert pwsh.commands[1].command_text == "Select-Object"
    assert pwsh.commands[1].end_of_statement is False
    assert pwsh.commands[1].use_local_scope is True
    assert pwsh.commands[1].merge_error == PipelineResultTypes.none
    assert pwsh.commands[1].merge_my == PipelineResultTypes.none
    assert pwsh.commands[1].merge_to == PipelineResultTypes.none
    assert str(pwsh.commands[2]) == "Format-List"
    assert (
        repr(pwsh.commands[2])
        == "<Command command_text='Format-List' is_script=False use_local_scope=False end_of_statement=True>"
    )
    assert pwsh.commands[2].command_text == "Format-List"
    assert pwsh.commands[2].end_of_statement is True
    assert pwsh.commands[2].use_local_scope is False
    assert pwsh.commands[2].merge_error == PipelineResultTypes.Output
    assert pwsh.commands[2].merge_my == PipelineResultTypes.Error
    assert pwsh.commands[2].merge_to == PipelineResultTypes.Output


def test_pipeline_multiple_statements():
    client, server = get_runspace_pair()
    c_pipeline = psrpcore.ClientPowerShell(client)

    c_pipeline.add_statement()  # Should do nothing, not fail
    c_pipeline.add_command("Get-ChildItem")
    c_pipeline.add_command("Format-List")
    c_pipeline.add_statement()
    c_pipeline.add_script("Test-Path", use_local_scope=True)
    c_pipeline.add_statement()
    c_pipeline.add_command("Get-Service")
    c_pipeline.add_command("Format-Table")
    c_pipeline.start()

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()
    pwsh = s_pipeline.metadata

    assert len(pwsh.commands) == 5
    assert pwsh.commands[0].command_text == "Get-ChildItem"
    assert pwsh.commands[0].use_local_scope is None
    assert pwsh.commands[0].is_script is False
    assert pwsh.commands[0].end_of_statement is False
    assert pwsh.commands[1].command_text == "Format-List"
    assert pwsh.commands[1].use_local_scope is None
    assert pwsh.commands[1].is_script is False
    assert pwsh.commands[1].end_of_statement is True
    assert pwsh.commands[2].command_text == "Test-Path"
    assert pwsh.commands[2].use_local_scope is True
    assert pwsh.commands[2].is_script is True
    assert pwsh.commands[2].end_of_statement is True
    assert pwsh.commands[3].command_text == "Get-Service"
    assert pwsh.commands[3].use_local_scope is None
    assert pwsh.commands[3].is_script is False
    assert pwsh.commands[3].end_of_statement is False
    assert pwsh.commands[4].command_text == "Format-Table"
    assert pwsh.commands[4].use_local_scope is None
    assert pwsh.commands[4].is_script is False
    assert pwsh.commands[4].end_of_statement is True


def test_pipeline_parameters():
    client, server = get_runspace_pair()
    c_pipeline = psrpcore.ClientPowerShell(client)

    expected = re.escape(
        "A command is required to add a parameter/argument. A command must be added to the "
        "PowerShell instance first."
    )
    with pytest.raises(ValueError, match=expected):
        c_pipeline.add_argument("argument")

    with pytest.raises(ValueError, match=expected):
        c_pipeline.add_parameter("name", "value")

    with pytest.raises(ValueError, match=expected):
        c_pipeline.add_parameters(name="value")

    c_pipeline.add_command("Get-ChildItem")
    c_pipeline.add_argument("/tmp")
    c_pipeline.add_argument(True)
    c_pipeline.add_statement()

    c_pipeline.add_command("Get-ChildItem")
    c_pipeline.add_parameter("Path", "/tmp")
    c_pipeline.add_parameter("Force")
    c_pipeline.add_statement()

    c_pipeline.add_command("Get-ChildItem")
    c_pipeline.add_parameters(Path="/tmp", Force=True)

    c_pipeline.start()

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()

    assert s_pipeline.metadata.commands[0].parameters == [(None, "/tmp"), (None, True)]
    assert s_pipeline.metadata.commands[1].parameters == [("Path", "/tmp"), ("Force", True)]
    assert s_pipeline.metadata.commands[2].parameters == [("Path", "/tmp"), ("Force", True)]


def test_pipeline_redirection():
    client, server = get_runspace_pair()
    c_pipeline = psrpcore.ClientPowerShell(client)

    command = psrpcore.Command("My-Cmdlet")

    expected = re.escape("Invalid redirection stream, must be none, Output, or Null")
    with pytest.raises(ValueError, match=expected):
        command.redirect_error(PipelineResultTypes.Error)

    with pytest.raises(ValueError, match=expected):
        command.redirect_debug(PipelineResultTypes.Error)

    with pytest.raises(ValueError, match=expected):
        command.redirect_warning(PipelineResultTypes.Error)

    with pytest.raises(ValueError, match=expected):
        command.redirect_verbose(PipelineResultTypes.Error)

    with pytest.raises(ValueError, match=expected):
        command.redirect_information(PipelineResultTypes.Error)

    with pytest.raises(ValueError, match=expected):
        command.redirect_all(PipelineResultTypes.Error)

    command.redirect_error(PipelineResultTypes.Output)
    command.merge_unclaimed = True
    c_pipeline.add_command(command)

    command = psrpcore.Command("My-Cmdlet2")
    command.redirect_all(PipelineResultTypes.Null)
    c_pipeline.add_command(command)

    command = psrpcore.Command("My-Cmdlet3")
    command.redirect_debug(PipelineResultTypes.Output)
    c_pipeline.add_command(command)

    command = psrpcore.Command("My-Cmdlet4")
    command.redirect_warning(PipelineResultTypes.Output)
    c_pipeline.add_command(command)

    command = psrpcore.Command("My-Cmdlet5")
    command.redirect_verbose(PipelineResultTypes.Output)
    c_pipeline.add_command(command)

    command = psrpcore.Command("My-Cmdlet6")
    command.redirect_information(PipelineResultTypes.Output)
    c_pipeline.add_command(command)

    command = psrpcore.Command("My-Cmdlet7")
    command.redirect_all(PipelineResultTypes.Output)
    command.redirect_all(PipelineResultTypes.none)  # Resets it back to normal
    c_pipeline.add_command(command)

    c_pipeline.start()
    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()
    pwsh = s_pipeline.metadata

    assert pwsh.commands[0].command_text == "My-Cmdlet"
    assert pwsh.commands[0].merge_debug == PipelineResultTypes.none
    assert pwsh.commands[0].merge_error == PipelineResultTypes.Output
    assert pwsh.commands[0].merge_information == PipelineResultTypes.none
    assert pwsh.commands[0].merge_my == PipelineResultTypes.Error
    assert pwsh.commands[0].merge_to == PipelineResultTypes.Output
    assert pwsh.commands[0].merge_unclaimed is True
    assert pwsh.commands[0].merge_verbose == PipelineResultTypes.none
    assert pwsh.commands[0].merge_warning == PipelineResultTypes.none

    assert pwsh.commands[1].command_text == "My-Cmdlet2"
    assert pwsh.commands[1].merge_debug == PipelineResultTypes.Null
    assert pwsh.commands[1].merge_error == PipelineResultTypes.Null
    assert pwsh.commands[1].merge_information == PipelineResultTypes.Null
    assert pwsh.commands[1].merge_my == PipelineResultTypes.none
    assert pwsh.commands[1].merge_to == PipelineResultTypes.none
    assert pwsh.commands[1].merge_unclaimed is False
    assert pwsh.commands[1].merge_verbose == PipelineResultTypes.Null
    assert pwsh.commands[1].merge_warning == PipelineResultTypes.Null

    assert pwsh.commands[2].command_text == "My-Cmdlet3"
    assert pwsh.commands[2].merge_debug == PipelineResultTypes.Output
    assert pwsh.commands[2].merge_error == PipelineResultTypes.none
    assert pwsh.commands[2].merge_information == PipelineResultTypes.none
    assert pwsh.commands[2].merge_my == PipelineResultTypes.none
    assert pwsh.commands[2].merge_to == PipelineResultTypes.none
    assert pwsh.commands[2].merge_unclaimed is False
    assert pwsh.commands[2].merge_verbose == PipelineResultTypes.none
    assert pwsh.commands[2].merge_warning == PipelineResultTypes.none

    assert pwsh.commands[3].command_text == "My-Cmdlet4"
    assert pwsh.commands[3].merge_debug == PipelineResultTypes.none
    assert pwsh.commands[3].merge_error == PipelineResultTypes.none
    assert pwsh.commands[3].merge_information == PipelineResultTypes.none
    assert pwsh.commands[3].merge_my == PipelineResultTypes.none
    assert pwsh.commands[3].merge_to == PipelineResultTypes.none
    assert pwsh.commands[3].merge_unclaimed is False
    assert pwsh.commands[3].merge_verbose == PipelineResultTypes.none
    assert pwsh.commands[3].merge_warning == PipelineResultTypes.Output

    assert pwsh.commands[4].command_text == "My-Cmdlet5"
    assert pwsh.commands[4].merge_debug == PipelineResultTypes.none
    assert pwsh.commands[4].merge_error == PipelineResultTypes.none
    assert pwsh.commands[4].merge_information == PipelineResultTypes.none
    assert pwsh.commands[4].merge_my == PipelineResultTypes.none
    assert pwsh.commands[4].merge_to == PipelineResultTypes.none
    assert pwsh.commands[4].merge_unclaimed is False
    assert pwsh.commands[4].merge_verbose == PipelineResultTypes.Output
    assert pwsh.commands[4].merge_warning == PipelineResultTypes.none

    assert pwsh.commands[5].command_text == "My-Cmdlet6"
    assert pwsh.commands[5].merge_debug == PipelineResultTypes.none
    assert pwsh.commands[5].merge_error == PipelineResultTypes.none
    assert pwsh.commands[5].merge_information == PipelineResultTypes.Output
    assert pwsh.commands[5].merge_my == PipelineResultTypes.none
    assert pwsh.commands[5].merge_to == PipelineResultTypes.none
    assert pwsh.commands[5].merge_unclaimed is False
    assert pwsh.commands[5].merge_verbose == PipelineResultTypes.none
    assert pwsh.commands[5].merge_warning == PipelineResultTypes.none

    assert pwsh.commands[6].command_text == "My-Cmdlet7"
    assert pwsh.commands[6].merge_debug == PipelineResultTypes.none
    assert pwsh.commands[6].merge_error == PipelineResultTypes.none
    assert pwsh.commands[6].merge_information == PipelineResultTypes.none
    assert pwsh.commands[6].merge_my == PipelineResultTypes.none
    assert pwsh.commands[6].merge_to == PipelineResultTypes.none
    assert pwsh.commands[6].merge_unclaimed is False
    assert pwsh.commands[6].merge_verbose == PipelineResultTypes.none
    assert pwsh.commands[6].merge_warning == PipelineResultTypes.none


def test_pipeline_input_output():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientPowerShell(client, no_input=False)
    assert c_pipeline.state == PSInvocationState.NotStarted

    c_pipeline.add_script("Get-Service")

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.Running' to send pipeline input, current state is "
        "PSInvocationState.NotStarted"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        c_pipeline.send("data")

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.Running' to send pipeline input EOF, current state is "
        "PSInvocationState.NotStarted"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        c_pipeline.send_eof()

    c_pipeline.start()
    assert c_pipeline.state == PSInvocationState.Running

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(client.data_to_send())
    create_pipeline = server.next_event()

    assert isinstance(create_pipeline, psrpcore.CreatePipelineEvent)
    assert isinstance(create_pipeline.pipeline, psrpcore.PowerShell)
    assert len(create_pipeline.pipeline.commands) == 1
    assert create_pipeline.pipeline.commands[0].command_text == "Get-Service"
    assert create_pipeline.pipeline.no_input is False
    assert s_pipeline.runspace_pool == server
    assert s_pipeline.state == PSInvocationState.NotStarted
    assert len(server.pipeline_table) == 1
    assert server.pipeline_table[s_pipeline.pipeline_id] == s_pipeline

    s_pipeline.start()
    server.data_to_send()

    c_pipeline.send("input 1")
    c_pipeline.send("input 2")
    c_pipeline.send(3)
    server.receive_data(client.data_to_send())

    input1 = server.next_event()
    input2 = server.next_event()
    input3 = server.next_event()

    assert server.next_event() is None
    assert isinstance(input1, psrpcore.PipelineInputEvent)
    assert repr(input1) == (
        f"<PipelineInputEvent runspace_pool_id={client.runspace_pool_id!r} "
        f"pipeline_id={c_pipeline.pipeline_id!r} data='input 1'>"
    )
    assert isinstance(input1.data, PSString)
    assert input1.data == "input 1"
    assert isinstance(input2, psrpcore.PipelineInputEvent)
    assert isinstance(input2.data, PSString)
    assert input2.data == "input 2"
    assert isinstance(input3, psrpcore.PipelineInputEvent)
    assert isinstance(input3.data, PSInt)
    assert input3.data == 3

    c_pipeline.send_eof()
    server.receive_data(client.data_to_send())
    end_of_input = server.next_event()
    assert isinstance(end_of_input, psrpcore.EndOfPipelineInputEvent)
    assert (
        repr(end_of_input) == f"<EndOfPipelineInputEvent runspace_pool_id={client.runspace_pool_id!r} "
        f"pipeline_id={c_pipeline.pipeline_id!r}>"
    )

    s_pipeline.write_output("output")
    s_pipeline.write_output(None)
    s_pipeline.write_debug("debug")
    s_pipeline.write_error(NETException("error"))
    s_pipeline.write_verbose("verbose")
    s_pipeline.write_warning("warning")
    s_pipeline.write_information("information", "source")
    s_pipeline.write_progress("activity", 1, "description")
    s_pipeline.complete()
    client.receive_data(server.data_to_send())

    output_event = client.next_event()
    assert isinstance(output_event, psrpcore.PipelineOutputEvent)
    assert repr(output_event) == (
        f"<PipelineOutputEvent runspace_pool_id={client.runspace_pool_id!r} "
        f"pipeline_id={c_pipeline.pipeline_id!r} data='output'>"
    )
    assert isinstance(output_event.data, PSString)
    assert output_event.data == "output"

    output_event = client.next_event()
    assert output_event.data is None

    debug_event = client.next_event()
    assert isinstance(debug_event, psrpcore.DebugRecordEvent)
    assert (
        repr(debug_event) == f"<DebugRecordEvent runspace_pool_id={client.runspace_pool_id!r} "
        f"pipeline_id={c_pipeline.pipeline_id!r} record='debug'>"
    )
    assert isinstance(debug_event.record, DebugRecord)
    assert debug_event.record.InvocationInfo is None
    assert debug_event.record.Message == "debug"
    assert debug_event.record.PipelineIterationInfo is None

    error_event = client.next_event()
    assert isinstance(error_event, psrpcore.ErrorRecordEvent)
    assert (
        repr(error_event) == f"<ErrorRecordEvent runspace_pool_id={client.runspace_pool_id!r} "
        f"pipeline_id={c_pipeline.pipeline_id!r} record='error'>"
    )
    assert isinstance(error_event.record, ErrorRecord)
    assert str(error_event.record) == "error"
    assert isinstance(error_event.record.Exception, NETException)
    assert error_event.record.Exception.Message == "error"
    assert isinstance(error_event.record.CategoryInfo, ErrorCategoryInfo)
    assert str(error_event.record.CategoryInfo), "NotSpecified (:) [], "
    assert error_event.record.CategoryInfo.Category == ErrorCategory.NotSpecified
    assert error_event.record.CategoryInfo.Reason is None
    assert error_event.record.CategoryInfo.TargetName is None
    assert error_event.record.CategoryInfo.TargetType is None
    assert error_event.record.ErrorDetails is None
    assert error_event.record.InvocationInfo is None
    assert error_event.record.PipelineIterationInfo is None
    assert error_event.record.ScriptStackTrace is None
    assert error_event.record.TargetObject is None

    verbose_event = client.next_event()
    assert isinstance(verbose_event, psrpcore.VerboseRecordEvent)
    assert (
        repr(verbose_event) == f"<VerboseRecordEvent runspace_pool_id={client.runspace_pool_id!r} "
        f"pipeline_id={c_pipeline.pipeline_id!r} record='verbose'>"
    )
    assert isinstance(verbose_event.record, VerboseRecord)
    assert verbose_event.record.InvocationInfo is None
    assert verbose_event.record.Message == "verbose"
    assert verbose_event.record.PipelineIterationInfo is None

    warning_event = client.next_event()
    assert isinstance(warning_event, psrpcore.WarningRecordEvent)
    assert (
        repr(warning_event) == f"<WarningRecordEvent runspace_pool_id={client.runspace_pool_id!r} "
        f"pipeline_id={c_pipeline.pipeline_id!r} record='warning'>"
    )
    assert isinstance(warning_event.record, WarningRecord)
    assert warning_event.record.InvocationInfo is None
    assert warning_event.record.Message == "warning"
    assert warning_event.record.PipelineIterationInfo is None

    info_event = client.next_event()
    assert isinstance(info_event, psrpcore.InformationRecordEvent)
    assert (
        repr(info_event) == f"<InformationRecordEvent runspace_pool_id={client.runspace_pool_id!r} "
        f"pipeline_id={c_pipeline.pipeline_id!r} record='information'>"
    )
    assert isinstance(info_event.record, InformationRecord)
    assert info_event.record.Computer is not None
    assert info_event.record.ManagedThreadId == 0
    assert info_event.record.MessageData == "information"
    if hasattr(threading, "get_native_id"):
        assert info_event.record.NativeThreadId > 0
    else:
        assert info_event.record.NativeThreadId == 0
    assert info_event.record.ProcessId > 0
    assert info_event.record.Source == "source"
    assert info_event.record.Tags == []
    assert info_event.record.TimeGenerated is not None
    assert info_event.record.User is not None

    progress_event = client.next_event()
    assert isinstance(progress_event, psrpcore.ProgressRecordEvent)
    assert (
        repr(progress_event) == f"<ProgressRecordEvent runspace_pool_id={client.runspace_pool_id!r} "
        f"pipeline_id={c_pipeline.pipeline_id!r}>"
    )
    assert isinstance(progress_event.record, ProgressRecord)
    assert progress_event.record.Activity == "activity"
    assert progress_event.record.ActivityId == 1
    assert progress_event.record.CurrentOperation is None
    assert progress_event.record.ParentActivityId == -1
    assert progress_event.record.PercentComplete == -1
    assert progress_event.record.SecondsRemaining == -1
    assert progress_event.record.StatusDescription == "description"
    assert progress_event.record.RecordType == ProgressRecordType.Processing

    state_event = client.next_event()
    assert isinstance(state_event, psrpcore.PipelineStateEvent)
    assert repr(state_event) == (
        f"<PipelineStateEvent runspace_pool_id={client.runspace_pool_id!r} pipeline_id={c_pipeline.pipeline_id!r} "
        f"state=<PSInvocationState.Completed: 4> reason=None>"
    )
    assert state_event.state == PSInvocationState.Completed
    assert client.next_event() is None


def test_pipeline_stop():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientPowerShell(client, no_input=False)
    assert c_pipeline.state == PSInvocationState.NotStarted

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.Running, PSInvocationState.Stopping' to begin stopping a "
        "pipeline, current state is PSInvocationState.NotStarted"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        c_pipeline.begin_stop()

    c_pipeline.add_script("script")
    c_pipeline.start()
    assert c_pipeline.state == PSInvocationState.Running
    c_pipeline.begin_stop()
    assert c_pipeline.state == PSInvocationState.Stopping

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()
    s_pipeline.start()
    server.data_to_send()

    s_pipeline.stop()
    assert s_pipeline.state == PSInvocationState.Stopped
    assert server.pipeline_table == {s_pipeline.pipeline_id: s_pipeline}

    client.receive_data(server.data_to_send())
    state = client.next_event()

    assert client.next_event() is None
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert isinstance(state.reason, ErrorRecord)
    assert state.state == PSInvocationState.Stopped
    assert str(state.reason) == "The pipeline has been stopped."
    assert str(state.reason.CategoryInfo) == "OperationStopped (:) [], PipelineStoppedException"
    assert state.reason.CategoryInfo.Category == ErrorCategory.OperationStopped
    assert state.reason.CategoryInfo.Reason == "PipelineStoppedException"
    assert state.reason.Exception.Message == "The pipeline has been stopped."
    assert state.reason.Exception.HResult == -2146233087
    assert state.reason.FullyQualifiedErrorId == "PipelineStopped"
    assert state.reason.InvocationInfo is None
    assert state.reason.PipelineIterationInfo is None
    assert state.reason.ScriptStackTrace is None
    assert state.reason.TargetObject is None
    assert c_pipeline.state == PSInvocationState.Stopped
    assert client.pipeline_table == {c_pipeline.pipeline_id: c_pipeline}

    s_pipeline.close()
    assert server.pipeline_table == {}

    c_pipeline.close()
    assert client.pipeline_table == {}


def test_pipeline_host_call():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientPowerShell(client)
    c_pipeline.add_script("$host.UI.WriteLine('line'); $host.UI.ReadLine()")
    c_pipeline.start()

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()
    s_pipeline.start()
    server.data_to_send()

    s_host = psrpcore.ServerHostRequestor(s_pipeline)
    actual_ci = s_host.write_line("line")
    assert actual_ci is None

    client.receive_data(server.data_to_send())
    host_call = client.next_event()
    assert isinstance(host_call, psrpcore.PipelineHostCallEvent)
    assert repr(host_call) == (
        f"<PipelineHostCallEvent runspace_pool_id={client.runspace_pool_id!r} pipeline_id={c_pipeline.pipeline_id!r} "
        f"ci=-100 method_identifier=<HostMethodIdentifier.WriteLine2: 16> method_parameters=['line']>"
    )
    assert host_call.pipeline_id == c_pipeline.pipeline_id
    assert host_call.ci == -100
    assert host_call.method_identifier == HostMethodIdentifier.WriteLine2
    assert host_call.method_parameters == ["line"]

    actual_ci = s_host.read_line()
    client.receive_data(server.data_to_send())
    host_call = client.next_event()
    assert isinstance(host_call, psrpcore.PipelineHostCallEvent)
    assert host_call.ci == actual_ci
    assert host_call.method_identifier == HostMethodIdentifier.ReadLine
    assert host_call.method_parameters == []

    error = ErrorRecord(
        Exception=NETException("ReadLine error"),
        CategoryInfo=ErrorCategoryInfo(
            Reason="Exception",
        ),
        FullyQualifiedErrorId="RemoteHostExecutionException",
    )
    c_pipeline.host_response(actual_ci, error_record=error)
    server.receive_data(client.data_to_send())
    host_resp = server.next_event()

    assert isinstance(host_resp, psrpcore.PipelineHostResponseEvent)
    assert repr(host_resp) == (
        f"<PipelineHostResponseEvent runspace_pool_id={client.runspace_pool_id!r} "
        f"pipeline_id={c_pipeline.pipeline_id!r} ci={actual_ci} method_identifier=<HostMethodIdentifier.ReadLine: 11> "
        f"result=None error='ReadLine error'>"
    )
    assert host_call.pipeline_id == c_pipeline.pipeline_id
    assert host_resp.ci == 1
    assert host_resp.method_identifier == HostMethodIdentifier.ReadLine
    assert isinstance(host_resp.error, ErrorRecord)
    assert str(host_resp.error) == "ReadLine error"
    assert host_resp.error.Exception.Message == "ReadLine error"
    assert host_resp.error.FullyQualifiedErrorId == "RemoteHostExecutionException"
    assert host_resp.error.CategoryInfo.Reason == "Exception"


def test_command_metadata():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientGetCommandMetadata(client, "Invoke*")
    c_pipeline.start()

    create_data = client.data_to_send()
    server.receive_data(create_data)
    with pytest.raises(psrpcore.PSRPCoreError, match="Failed to find pipeline for incoming event"):
        server.next_event()

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(create_data)
    command_meta = server.next_event()
    assert isinstance(command_meta, psrpcore.GetCommandMetadataEvent)
    assert repr(command_meta) == (
        f"<GetCommandMetadataEvent runspace_pool_id={client.runspace_pool_id!r} "
        f"pipeline_id={c_pipeline.pipeline_id!r} "
        f"pipeline=<GetMetadata name=['Invoke*'] command_type=<CommandTypes.All: 383> namespace=None arguments=None>>"
    )
    assert isinstance(command_meta.pipeline, psrpcore.GetMetadata)

    s_pipeline.start()
    server.data_to_send()

    s_pipeline.write_output(
        PSCustomObject(PSTypeName="Selected.Microsoft.PowerShell.Commands.GenericMeasureInfo", Count=1)
    )
    s_pipeline.write_output(
        PSCustomObject(
            PSTypeName="Selected.System.Management.Automation.CmdletInfo",
            CommandType=CommandTypes.Cmdlet,
            Name="Invoke-Expression",
            Namespace="namespace",
            HelpUri="",
            OutputType=[],
            Parameters={},
            ResolvedCommandName=None,
        )
    )
    s_pipeline.complete()

    assert s_pipeline.state == PSInvocationState.Completed
    assert server.pipeline_table == {s_pipeline.pipeline_id: s_pipeline}

    client.receive_data(server.data_to_send())
    count = client.next_event()
    iex = client.next_event()
    state = client.next_event()

    assert client.next_event() is None
    assert c_pipeline.state == PSInvocationState.Completed
    assert client.pipeline_table == {c_pipeline.pipeline_id: c_pipeline}

    s_pipeline.close()
    assert server.pipeline_table == {}

    c_pipeline.close()
    assert client.pipeline_table == {}

    assert isinstance(count, psrpcore.PipelineOutputEvent)
    assert count.data.Count == 1
    assert isinstance(iex, psrpcore.PipelineOutputEvent)
    assert iex.data.Name == "Invoke-Expression"
    assert iex.data.Namespace == "namespace"
    assert iex.data.HelpUri == ""
    assert iex.data.OutputType == []
    assert iex.data.Parameters == {}
    assert iex.data.ResolvedCommandName is None
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == PSInvocationState.Completed


def test_exchange_key_client():
    client, server = get_runspace_pair()

    client.exchange_key()
    server.receive_data(client.data_to_send())
    public_key = server.next_event()
    assert isinstance(public_key, psrpcore.PublicKeyEvent)
    assert repr(public_key) == f"<PublicKeyEvent runspace_pool_id={client.runspace_pool_id!r} pipeline_id=None>"

    client.receive_data(server.data_to_send())
    enc_key = client.next_event()
    assert isinstance(enc_key, psrpcore.EncryptedSessionKeyEvent)
    assert repr(enc_key) == f"<EncryptedSessionKeyEvent runspace_pool_id={client.runspace_pool_id!r} pipeline_id=None>"

    c_pipeline = psrpcore.ClientPowerShell(client)
    c_pipeline.add_script("command")
    c_pipeline.add_argument(PSSecureString("my secret"))
    c_pipeline.start()
    c_pipeline_data = client.data_to_send()
    assert b"my_secret" not in c_pipeline_data.data

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(c_pipeline_data)
    create_pipeline = server.next_event()
    assert isinstance(create_pipeline, psrpcore.CreatePipelineEvent)
    assert len(s_pipeline.metadata.commands) == 1
    assert s_pipeline.metadata.commands[0].command_text == "command"
    assert s_pipeline.metadata.commands[0].parameters[0][0] is None
    assert isinstance(s_pipeline.metadata.commands[0].parameters[0][1], PSSecureString)
    assert str(s_pipeline.metadata.commands[0].parameters[0][1]) != "my secret"
    assert s_pipeline.metadata.commands[0].parameters[0][1].decrypt() == "my secret"

    s_pipeline.start()
    server.data_to_send()

    s_pipeline.write_output(PSSecureString("secret output"))
    s_pipeline.complete()
    s_output = server.data_to_send()
    assert s_pipeline.state == PSInvocationState.Completed
    assert server.pipeline_table == {s_pipeline.pipeline_id: s_pipeline}
    assert b"secret output" not in s_output

    client.receive_data(s_output)
    out = client.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert isinstance(out.data, PSSecureString)
    assert str(out.data) != "secret output"
    assert out.data.decrypt() == "secret output"

    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == PSInvocationState.Completed

    assert c_pipeline.state == PSInvocationState.Completed
    assert client.pipeline_table == {c_pipeline.pipeline_id: c_pipeline}

    s_pipeline.close()
    assert server.pipeline_table == {}

    c_pipeline.close()
    assert client.pipeline_table == {}


def test_write_exchange_key_without_request():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientPowerShell(client)
    c_pipeline.add_script("command")
    c_pipeline.start()

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()
    s_pipeline.start()
    server.data_to_send()

    s_pipeline.write_output(PSSecureString("secret"))
    s_pipeline.complete()

    client.receive_data(server.data_to_send())
    out = client.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert isinstance(out.data, PSSecureString)
    with pytest.raises(psrpcore.MissingCipherError):
        out.data.decrypt()

    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == PSInvocationState.Completed
    assert c_pipeline.state == PSInvocationState.Completed
    assert client.pipeline_table == {c_pipeline.pipeline_id: c_pipeline}

    c_pipeline.close()
    assert client.pipeline_table == {}

    client.exchange_key()
    server.receive_data(client.data_to_send())

    # Won't generate once we've sent the request once
    client.exchange_key()
    assert client.data_to_send() is None

    key = server.next_event()
    assert isinstance(key, psrpcore.PublicKeyEvent)

    client.receive_data(server.data_to_send())
    assert server.data_to_send() is None

    enc_key = client.next_event()
    assert isinstance(enc_key, psrpcore.EncryptedSessionKeyEvent)

    # Now the session key is encrypted we can decrypt the value.
    assert out.data.decrypt() == "secret"

    client.exchange_key()
    assert client.data_to_send() is None
    server.request_key()
    assert server.data_to_send() is None


def test_exchange_key_request():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientPowerShell(client)
    c_pipeline.add_script("command")
    c_pipeline.start()

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()
    s_pipeline.start()
    server.data_to_send()

    s_pipeline.write_output(PSSecureString("secret"))
    s_pipeline.complete()
    out_data = server.data_to_send()
    assert b"secret" not in out_data
    client.receive_data(out_data)

    out = client.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    with pytest.raises(psrpcore.MissingCipherError):
        out.data.decrypt()

    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)

    server.request_key()
    client.receive_data(server.data_to_send())
    pub_key_req = client.next_event()
    assert isinstance(pub_key_req, psrpcore.PublicKeyRequestEvent)
    assert repr(pub_key_req) == f"<PublicKeyRequestEvent runspace_pool_id={client.runspace_pool_id!r} pipeline_id=None>"

    with pytest.raises(psrpcore.MissingCipherError):
        out.data.decrypt()

    server.receive_data(client.data_to_send())
    pub_key = server.next_event()
    assert isinstance(pub_key, psrpcore.PublicKeyEvent)

    client.receive_data(server.data_to_send())
    enc_key = client.next_event()
    assert isinstance(enc_key, psrpcore.EncryptedSessionKeyEvent)

    assert out.data.decrypt() == "secret"

    # Subsequent calls shouldn't do anything
    server.request_key()
    assert server.data_to_send() is None

    client.exchange_key()
    assert client.data_to_send() is None


def test_pipeline_with_mixed_next_event():
    client, server = get_runspace_pair()
    c_pipeline = psrpcore.ClientPowerShell(client)
    c_pipeline.add_script("command")
    c_pipeline.start()

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()
    s_pipeline.start()
    server.data_to_send()
    s_pipeline.write_output(PSString("data"))

    s_host = psrpcore.ServerHostRequestor(server)
    s_host.read_line()
    s_pipeline.complete()

    output_data = server.data_to_send()
    assert output_data is not None
    assert output_data.pipeline_id == s_pipeline.pipeline_id
    assert output_data.stream_type == psrpcore.StreamType.default

    host_data = server.data_to_send()
    assert host_data is not None
    assert host_data.pipeline_id is None
    assert host_data.stream_type == psrpcore.StreamType.prompt_response

    state_data = server.data_to_send()
    assert state_data is not None
    assert state_data.pipeline_id == s_pipeline.pipeline_id
    assert state_data.stream_type == psrpcore.StreamType.default

    client.receive_data(output_data)
    client.receive_data(host_data)
    client.receive_data(state_data)

    out = client.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert out.data == "data"

    host = client.next_event()
    assert isinstance(host, psrpcore.RunspacePoolHostCallEvent)
    assert host.ci == 1
    assert host.method_identifier == psrpcore.types.HostMethodIdentifier.ReadLine
    assert host.method_parameters == []

    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == PSInvocationState.Completed

    c_host = psrpcore.ClientHostResponder(client)
    c_host.read_line(1, "line to read")
    server.receive_data(client.data_to_send())
    host_resp = server.next_event()
    assert isinstance(host_resp, psrpcore.RunspacePoolHostResponseEvent)
    assert host_resp.ci == 1
    assert host_resp.method_identifier == psrpcore.types.HostMethodIdentifier.ReadLine
    assert host_resp.result == "line to read"


def test_pipeline_with_secure_string_parameter():
    client, server = get_runspace_pair()
    c_pipeline = psrpcore.ClientPowerShell(client)
    c_pipeline.add_command("command").add_parameter("Secret", PSSecureString("secret"))

    with pytest.raises(psrpcore.MissingCipherError):
        c_pipeline.start()

    client.exchange_key()
    server.receive_data(client.data_to_send())
    server.next_event()
    client.receive_data(server.data_to_send())
    client.next_event()

    c_pipeline.start()

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()
    s_pipeline.start()
    server.data_to_send()
    s_pipeline.write_output(s_pipeline.metadata.commands[0].parameters[0][1])
    s_pipeline.complete()

    client.receive_data(server.data_to_send())

    out = client.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert isinstance(out.data, PSSecureString)
    assert out.data.decrypt() == "secret"

    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == PSInvocationState.Completed
