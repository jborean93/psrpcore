# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import enum
import struct
import typing
import uuid

from psrpcore.types import PSObject, PSRPMessageType, PSVersion, add_note_property

EMPTY_UUID = uuid.UUID(int=0)


class Fragment(typing.NamedTuple):
    """A PSRP fragment containing all or part of a PSRP message."""

    object_id: int  #: The full object the fragment is part of.
    fragment_id: int  #: The number fragment that comprises the object.
    start: bool  #: Whether this fragment is the starting fragment.
    end: bool  #: Whether this fragment is the ending fragment.
    data: bytearray  #: The fragment data.


class Message(typing.NamedTuple):
    """A PSRP message containing a PSRP payload to send."""

    destination: int  #: The destination identifier of the message.
    message_type: PSRPMessageType  #: The type of PSRP payload.
    rpid: uuid.UUID  #: The Runspace Pool ID.
    pid: typing.Optional[uuid.UUID]  #: The Pipeline ID.
    data: bytearray  #: The PSRP payload.


class PSRPPayload(typing.NamedTuple):
    """The PSRP data payload that is exchanged between the client and server."""

    data: bytes  #: The raw data to be exchanged with the client and server.
    stream_type: "StreamType"  #: The type of data that is contained.
    pipeline_id: typing.Optional[
        uuid.UUID
    ]  #: The pipeline id if the data is related to a Pipeline or `None` for a Runspace Pool.


class ProtocolVersion(enum.Enum):
    """PSRP Protocol versions

    This lists the known PSRP protocol versions. The psrpcore library
    understands the 2.3 version and thus supports anything the PowerShell side
    does.

    These are the known differences between the protocol versions.

    Win7RC:
        * No native support for GetCommandMetadata
        * Client instead should send a CreatePipeline that calls `Get-Command`

    Pwsh2:
        * First official release that was shipped with PowerShell v2.

    Pwsh3:
        * Shipped with PowerShell v3
        * Support merging warning, verbose, debug to output or null when
            creating a command to run on a pipeline
        * Supports batch invocations on 1 pipeline using mutliple statements
            # TODO Verify
        * Server stopped sending the PublicKeyRequest message, must be done by
            the client
        * WSMan stack added Support for disconnect operations
        * On the WSMan stack the default envelope size increased from 150KiB to
            500KiB

    Pwsh5:
        * Shipped with PowerShell v5
        * Information stream
        * Reset Runspace Pool
    """

    Win7RC = PSVersion("2.0")  #: Win7RC - pwsh v2 but for the Windows 7 Beta
    Pwsh2 = PSVersion("2.1")  #: Win7RTM - pwsh v2
    Pwsh3 = PSVersion("2.2")  #: Win8RTM - pwsh v3
    Pwsh5 = PSVersion("2.3")  #: Win10RTM - pwsh v5


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
    ) -> Fragment:
        """Create a fragment with a maximum length."""
        data = self._data[:length]
        self._data = self._data[length:]
        fragment_id = self.fragment_counter
        end = len(self) == 0

        return Fragment(self.object_id, fragment_id, fragment_id == 0, end, data)


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
    rpid: uuid.UUID = uuid.UUID(bytes_le=bytes(data[8:24]))
    pid: typing.Optional[uuid.UUID] = uuid.UUID(bytes_le=bytes(data[24:40]))

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


def dict_to_psobject(**kwargs: typing.Any) -> PSObject:
    """Builds a PSObject with note properties set by the kwargs."""
    obj = PSObject()
    obj.PSObject.type_names = []
    for key, value in kwargs.items():
        add_note_property(obj, key, value)

    return obj
