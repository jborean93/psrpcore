# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import re

import pytest

import psrpcore
from psrpcore.types import (
    ErrorCategoryInfo,
    ErrorRecord,
    NETException,
    RunspacePoolState,
)

from .conftest import get_runspace_pair


def test_close_with_begin():
    client, server = get_runspace_pair()

    server.begin_close()
    assert client.state == RunspacePoolState.Opened
    assert server.state == RunspacePoolState.Closing

    client.receive_data(server.data_to_send())
    state = client.next_event()
    assert isinstance(state, psrpcore.RunspacePoolStateEvent)
    assert state.state == RunspacePoolState.Closing
    assert state.reason is None
    assert client.state == RunspacePoolState.Closing
    assert server.state == RunspacePoolState.Closing

    server.close()
    assert client.state == RunspacePoolState.Closing
    assert server.state == RunspacePoolState.Closed

    client.receive_data(server.data_to_send())
    state = client.next_event()
    assert isinstance(state, psrpcore.RunspacePoolStateEvent)
    assert state.state == RunspacePoolState.Closed
    assert state.reason is None
    assert client.state == RunspacePoolState.Closed
    assert server.state == RunspacePoolState.Closed


def test_server_is_broken():
    client, server = get_runspace_pair()

    err = ErrorRecord(
        Exception=NETException(Message="exception message"),
        CategoryInfo=ErrorCategoryInfo(),
    )
    server.set_broken(err)
    assert client.state == RunspacePoolState.Opened
    assert server.state == RunspacePoolState.Broken

    client.receive_data(server.data_to_send())
    state = client.next_event()
    assert isinstance(state, psrpcore.RunspacePoolStateEvent)
    assert state.state == RunspacePoolState.Broken
    assert isinstance(state.reason, ErrorRecord)
    assert str(state.reason) == "exception message"
    assert client.state == RunspacePoolState.Broken
    assert server.state == RunspacePoolState.Broken
