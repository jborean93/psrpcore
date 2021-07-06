# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import re

import pytest

import psrpcore
from psrpcore.types import RunspacePoolState

from .conftest import get_runspace_pair


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
    assert connect.runspace_pool_id == client.runspace_pool_id
    assert client.state == RunspacePoolState.Connecting
    assert server.state == RunspacePoolState.Opened

    client.receive_data(server.data_to_send())
    init = client.next_event()
    assert isinstance(init, psrpcore.RunspacePoolInitDataEvent)
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
    assert set_max.ps_object.ci == ci
    assert set_max.ps_object.MaxRunspaces == 5
    assert server.max_runspaces == 5

    client.receive_data(server.data_to_send())
    resp = client.next_event()
    assert isinstance(resp, psrpcore.SetRunspaceAvailabilityEvent)
    assert resp.ps_object.ci == ci
    assert resp.ps_object.SetMinMaxRunspacesResponse
    assert client.max_runspaces == 5


def test_set_min_runspaces():
    client, server = get_runspace_pair(max_runspaces=2)

    ci = client.set_min_runspaces(2)
    assert ci is not None
    assert client.min_runspaces == 1

    server.receive_data(client.data_to_send())
    set_max = server.next_event()
    assert isinstance(set_max, psrpcore.SetMinRunspacesEvent)
    assert set_max.ps_object.ci == ci
    assert set_max.ps_object.MinRunspaces == 2
    assert server.min_runspaces == 2

    client.receive_data(server.data_to_send())
    resp = client.next_event()
    assert isinstance(resp, psrpcore.SetRunspaceAvailabilityEvent)
    assert resp.ps_object.ci == ci
    assert resp.ps_object.SetMinMaxRunspacesResponse
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
