# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import base64
import collections
import enum
import struct
import typing
import uuid

from psrpcore.types._psrp_messages import (
    PSRPMessageType,
)

EMPTY_UUID = uuid.UUID(bytes=b"\x00" * 16)

Fragment = collections.namedtuple("Fragment", ["object_id", "fragment_id", "start", "end", "data"])
"""PSRP Fragment.

A PSRP fragment containing all or part of a PSRP message.

Attributes:
    object_id (int): The full object the fragment is part of.
    fragment_id (int): The number fragment that comprises the object.
    start (bool): Whether this fragment is the start fragment.
    end (bool): Whether this fragment is the end fragment.
    data (bytearray): The fragment data.
"""

Message = collections.namedtuple("Message", ["destination", "message_type", "rpid", "pid", "data"])
"""PSRP Message.

A PSRP message containing a PSRP payload to send.

Attributes:
    destination (int): The destination identifier of the message.
    message_type (PSRPMessageType): The type of PSRP payload.
    rpid (typing.Optional[uuid.UUID]): The Runspace Pool ID.
    pid (typing.Optional[uuid.UUID]): The Pipeline ID.
    data (bytearray): The PSRP payload.
"""

PSRPPayload = collections.namedtuple("PSRPPayload", ["data", "stream_type", "pipeline_id"])
"""PSRP Data payload.

The PSRP data payload that is exchanged between the client and server.

Attributes:
    data (bytes): The raw data to be exchanged with the client and server.
    stream_type (StreamType): The type of data that is contained.
    pipeline_id (typing.Optional[uuid.UUID]): The pipeline id if the data
        related to a Pipeline or `None if it's for the Runspace Pool.
"""


class StreamType(enum.Enum):
    """PSRP Message stream type.

    The PSRP message stream type that defines the priority of a PSRP message.
    It is up to the connection to interpret these options and convey the
    priority to the peer in the proper fashion.
    """

    default = enum.auto()  #: The default type used for the majority of PSRP messages.
    prompt_response = enum.auto()  #: Used for host call/responses PSRP messages.


class PSRPMessage:
    """PSRP Message in the outgoing queue.

    Represents a PSRP message to send to the peer or a defragmented object
    from the peer.

    Args:
        message_type: The PSRP message type the fragment is for.
        data: The PSRP message fragment.
        runspace_pool_id: The Runspace Pool ID the message is for.
        pipeline_id: The pipeline the message is targeted towards or `None` to
            target the RunspacePool.
        object_id: The data fragment object id.
        stream_type: The StreamType associated with the message.
    """

    def __init__(
        self,
        message_type: PSRPMessageType,
        data: bytearray,
        runspace_pool_id: uuid.UUID,
        pipeline_id: typing.Optional[uuid.UUID],
        object_id: int,
        stream_type: StreamType = StreamType.default,
    ):
        self.message_type = message_type
        self.runspace_pool_id = runspace_pool_id
        self.pipeline_id = pipeline_id
        self.object_id = object_id
        self.stream_type = stream_type
        self._data = bytearray(data)
        self._fragment_counter: int = 0

    def __len__(self) -> int:
        return len(self._data)

    @property
    def data(self) -> bytes:
        """The internal buffer as a byte string."""
        return bytes(self._data)

    @property
    def fragment_counter(
        self,
    ) -> int:
        """Get the next fragment ID for the message fragments."""
        fragment_id = self._fragment_counter
        self._fragment_counter += 1
        return fragment_id

    def fragment(
        self,
        length: int,
    ) -> bytes:
        """Create a fragment with a maximum length."""
        data = self._data[:length]
        self._data = self._data[length:]
        fragment_id = self.fragment_counter
        end = len(self) == 0

        return create_fragment(self.object_id, fragment_id, data, end)


def create_message(
    client: bool,
    message_type: PSRPMessageType,
    data: bytes,
    runspace_pool_id: uuid.UUID,
    pipeline_id: typing.Optional[uuid.UUID] = None,
) -> bytes:
    """Create a PSRP message.

    Creates a PSRP message that encapsulates a PSRP message object. The
    message structure is defined in
    `MS-PSRP 2.2.1 PowerShell Remoting Protocol Message`_.

    Args:
        client: The message is from the client (True) or not (False).
        message_type: The type of message specified by `data`.
        data: The serialized PSRP message data.
        runspace_pool_id: The RunspacePool instance ID.
        pipeline_id: The Pipeline instance ID if the message is targeted
            towards a pipeline.

    .. _MS-PSRP 2.2.1 PowerShell Remoting Protocol Message:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/497ac440-89fb-4cb3-9cc1-3434c1aa74c3
    """
    destination = 0x00000002 if client else 0x00000001

    return b"".join(
        [
            struct.pack("<i", destination),
            struct.pack("<I", message_type.value),
            # .NET serializes uuids/guids in bytes in the little endian form.
            runspace_pool_id.bytes_le,
            (pipeline_id or EMPTY_UUID).bytes_le,
            data,
        ]
    )


def create_fragment(
    object_id: int,
    fragment_id: int,
    data: bytes,
    end: bool = True,
) -> bytes:
    """Create a PSRP fragment.

    Creates a PSRP message fragment. The fragment structure is defined in
    `MS-PSRP 2.2.4 Packet Fragment`_.

    Args:
        object_id: The unique ID of the PSRP message to which the fragment
            belongs.
        fragment_id: Identifies where in the sequence of fragments this
            fragment falls.
        data: The PSRP message value to fragment.
        end: Whether this is the last fragment for the PSRP message (True) or
            not (False).

    Returns:
        (bytes): The PSRP fragment.

    .. _MS-PSRP 2.2.4 Packet Fragment:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/3610dae4-67f7-4175-82da-a3fab83af288
    """
    start_end_byte = 0
    if fragment_id == 0:
        start_end_byte |= 0x1
    if end:
        start_end_byte |= 0x2

    return b"".join(
        [
            struct.pack(">Q", object_id),
            struct.pack(">Q", fragment_id),
            struct.pack("B", start_end_byte),
            struct.pack(">I", len(data)),
            data,
        ]
    )


def unpack_message(
    data: bytearray,
) -> Message:
    """Unpack a PSRP message.

    Unpacks data into a PSRP message.

    Args:
        data: The data to unpack.

    Returns:
        Message: The PSRP message that was unpacked.
    """
    destination = struct.unpack("<I", data[0:4])[0]
    message_type = PSRPMessageType(struct.unpack("<I", data[4:8])[0])
    rpid = uuid.UUID(bytes_le=bytes(data[8:24]))
    pid = uuid.UUID(bytes_le=bytes(data[24:40]))

    if rpid == EMPTY_UUID:
        rpid = None
    if pid == EMPTY_UUID:
        pid = None

    data = data[40:]
    if data.startswith(b"\xEF\xBB\xBF"):
        data = data[3:]  # Handle UTF-8 BOM in data.

    return Message(destination, message_type, rpid, pid, data)


def unpack_fragment(
    data: bytearray,
) -> Fragment:
    """Unpack a PSRP fragment.

    Unpacks data into a PSRP fragment.

    Args:
        data: The data to unpack.

    Returns:
        Fragment: The PSRP fragment that was unpacked.
    """
    object_id = struct.unpack(">Q", data[0:8])[0]
    fragment_id = struct.unpack(">Q", data[8:16])[0]
    start_end_byte = struct.unpack("B", data[16:17])[0]
    start = start_end_byte & 0x1 == 0x1
    end = start_end_byte & 0x2 == 0x2
    length = struct.unpack(">I", data[17:21])[0]

    return Fragment(object_id, fragment_id, start, end, data[21 : length + 21])


def ps_data_packet(
    data: bytes,
    stream_type: StreamType = StreamType.default,
    ps_guid: typing.Optional[uuid.UUID] = None,
) -> bytes:
    """Data packet for PSRP fragments.

    This creates a data packet that is used to encode PSRP fragments when
    sending to the server.

    Args:
        data: The PSRP fragments to encode.
        stream_type: The stream type to target, Default or PromptResponse.
        ps_guid: Set to `None` or a 0'd UUID to target the RunspacePool,
            otherwise this should be the pipeline UUID.

    Returns:
        bytes: The encoded data XML packet.
    """
    ps_guid = ps_guid or EMPTY_UUID
    stream_name = b"Default" if stream_type == StreamType.default else b"PromptResponse"
    return b"<Data Stream='%s' PSGuid='%s'>%s</Data>\n" % (stream_name, str(ps_guid).encode(), base64.b64encode(data))


def ps_guid_packet(
    element: str,
    ps_guid: typing.Optional[uuid.UUID] = None,
) -> bytes:
    """Common PSGuid packet for PSRP message.

    This creates a PSGuid packet that is used to signal events and stages in
    the PSRP exchange. Unlike the data packet this does not contain any PSRP
    fragments.

    Args:
        element: The element type, can be DataAck, Command, CommandAck, Close,
            CloseAck, Signal, and SignalAck.
        ps_guid: Set to `None` or a 0'd UUID to target the RunspacePool,
            otherwise this should be the pipeline UUID.

    Returns:
        bytes: The encoded PSGuid packet.
    """
    ps_guid = ps_guid or EMPTY_UUID
    return b"<%s PSGuid='%s' />\n" % (element.encode(), str(ps_guid).encode())
