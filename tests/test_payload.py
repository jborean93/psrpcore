# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import uuid

from psrpcore import _payload as payload
from psrpcore.types import PSRPMessageType


def test_unpack_message_without_bom():
    actual = payload.unpack_message(bytearray(b"\x01\x00\x00\x00\x02\x00\x01\x00" + (b"\x00") * 32 + b"abc"))
    assert isinstance(actual, payload.Message)
    assert actual.destination == 1
    assert actual.message_type == PSRPMessageType.SessionCapability
    assert actual.rpid is None
    assert actual.pid is None
    assert actual.data == bytearray(b"abc")


def test_unpack_message_with_bom():
    actual = payload.unpack_message(
        bytearray(b"\x01\x00\x00\x00\x02\x00\x01\x00" + (b"\x00") * 32 + b"\xEF\xBB\xBFabc")
    )
    assert isinstance(actual, payload.Message)
    assert actual.destination == 1
    assert actual.message_type == PSRPMessageType.SessionCapability
    assert actual.rpid is None
    assert actual.pid is None
    assert actual.data == bytearray(b"abc")


def test_create_ps_data_packet():
    actual = payload.ps_data_packet(b"abc")
    assert actual == b"<Data Stream='Default' PSGuid='00000000-0000-0000-0000-000000000000'>YWJj</Data>"


def test_create_ps_data_packet_pr():
    actual = payload.ps_data_packet(
        b"abc", payload.StreamType.prompt_response, uuid.UUID("00000000-0000-0000-0000-000000000001")
    )
    assert actual == b"<Data Stream='PromptResponse' PSGuid='00000000-0000-0000-0000-000000000001'>YWJj</Data>"


def test_create_ps_guid_packet():
    actual = payload.ps_guid_packet("Command")
    assert actual == b"<Command PSGuid='00000000-0000-0000-0000-000000000000' />"
