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
    assert actual.rpid == uuid.UUID(int=0)
    assert actual.pid is None
    assert actual.data == bytearray(b"abc")


def test_unpack_message_with_bom():
    actual = payload.unpack_message(
        bytearray(b"\x01\x00\x00\x00\x02\x00\x01\x00" + (b"\x00") * 32 + b"\xEF\xBB\xBFabc")
    )
    assert isinstance(actual, payload.Message)
    assert actual.destination == 1
    assert actual.message_type == PSRPMessageType.SessionCapability
    assert actual.rpid == uuid.UUID(int=0)
    assert actual.pid is None
    assert actual.data == bytearray(b"abc")
