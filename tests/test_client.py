# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import re

import pytest

import psrpcore
from psrpcore.types import RunspacePoolState

from .conftest import get_runspace_pair


def test_connect_with_already_opened_client():
    client = get_runspace_pair()[0]
    client.connect()

    assert client.data_to_send() is None


def test_connect_fail_with_closed_runspace():
    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.BeforeOpen' to connect to Runspace Pool, current "
        "state is RunspacePoolState.Closing"
    )
    client = get_runspace_pair()[0]
    client.close()

    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        client.connect()


def test_disconnect_fail_not_opened():
    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Opened' to disconnect a Runspace Pool, current "
        "state is RunspacePoolState.BeforeOpen"
    )

    client = psrpcore.ClientRunspacePool()

    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        client.disconnect()


def test_disconnect_and_reconnect_runspace_pool():
    client, server = get_runspace_pair()

    assert client.state == RunspacePoolState.Opened
    assert server.state == RunspacePoolState.Opened

    client.disconnect()
    server.disconnect()

    assert client.state == RunspacePoolState.Disconnected
    assert server.state == RunspacePoolState.Disconnected

    client.reconnect()
    server.reconnect()

    assert client.state == RunspacePoolState.Opened
    assert client.state == RunspacePoolState.Opened


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
    assert server.state == RunspacePoolState.NegotiationSucceeded

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
