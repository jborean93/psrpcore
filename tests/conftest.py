# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import base64
import collections
import contextlib
import os
import queue
import socket
import subprocess
import threading
import typing
import uuid
from xml.etree import ElementTree

import pytest
from xmldiff import main as _xmldiff

if os.name == "nt":
    import win32api
    import win32event
    import win32file
    import win32pipe
    import winerror

import psrpcore

BUFFER_SIZE = 327681

# Contains control characters, non-ascii chars, and chars that are surrogate pairs in UTF-16
COMPLEX_STRING = "treble clef\n _x0000_ _X0000_ %s café" % b"\xF0\x9D\x84\x9E".decode("utf-8")
COMPLEX_ENCODED_STRING = "treble clef_x000A_ _x005F_x0000_ _x005F_X0000_ _xD834__xDD1E_ café"

T = typing.TypeVar("T", psrpcore.ClientRunspacePool, psrpcore.ServerRunspacePool)

OutOfProcPacket = collections.namedtuple("OutOfProcPacket", ["action", "ps_guid", "data"])


def which(program: str) -> typing.Optional[str]:
    for path in os.environ.get("PATH", "").split(os.pathsep):
        exe = os.path.join(path, program)
        if os.path.isfile(exe) and os.access(exe, os.X_OK):
            return exe

    return


PWSH_PATH = which("pwsh.exe" if os.name == "nt" else "pwsh")


class FakeCryptoProvider(psrpcore.types.PSCryptoProvider):
    def decrypt(self, value: bytes) -> bytes:
        return value

    def encrypt(self, value: bytes) -> bytes:
        return value

    def register_key(self, key: bytes) -> None:
        pass


class OutOfProcTransport(typing.Generic[T]):
    def __init__(self, runspace: T) -> None:
        self.runspace = runspace
        self._incoming: queue.Queue[typing.Union[Exception, OutOfProcPacket]] = queue.Queue()
        self._listen_task = threading.Thread(target=self._read_task)
        self._wait = threading.Condition()
        self._wait_set = set()

    def __enter__(self) -> "OutOfProcTransport":
        self._open()
        self._listen_task.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._close()
        self._listen_task.join()

    def next_payload(self) -> OutOfProcPacket:
        # No long running tests, anything taking more than 60 seconds is a failure
        payload = self._incoming.get(timeout=60)
        if isinstance(payload, Exception):
            raise payload

        return payload

    def next_event(self) -> psrpcore.PSRPEvent:
        while True:
            event = self.runspace.next_event()
            if event:
                return event

            payload = self.next_payload()
            if payload.action != "Data":
                continue

            self.runspace.receive_data(payload.data)

    def close(
        self,
        pipeline_id: typing.Optional[uuid.UUID] = None,
    ) -> None:
        with self._wait_ack("Close", pipeline_id):
            self._send(ps_guid_packet("Close", pipeline_id))

    def close_ack(
        self,
        pipeline_id: typing.Optional[uuid.UUID] = None,
    ) -> None:
        self._send(ps_guid_packet("CloseAck", pipeline_id))

    def command(
        self,
        pipeline_id: typing.Optional[uuid.UUID] = None,
    ) -> None:
        with self._wait_ack("Command", pipeline_id):
            self._send(ps_guid_packet("Command", pipeline_id))

    def command_ack(
        self,
        pipeline_id: typing.Optional[uuid.UUID] = None,
    ) -> None:
        self._send(ps_guid_packet("CommandAck", pipeline_id))

    def data(
        self,
        wait_ack: bool = True,
    ) -> bool:
        data = self.runspace.data_to_send()
        if not data:
            return False

        with self._wait_ack("Data" if wait_ack else None, data.pipeline_id):
            self._send(ps_data_packet(*data))

        return True

    def data_ack(
        self,
        pipeline_id: typing.Optional[uuid.UUID] = None,
    ) -> None:
        self._send(ps_guid_packet("DataAck", pipeline_id))

    def signal(
        self,
        pipeline_id: typing.Optional[uuid.UUID] = None,
    ) -> None:
        with self._wait_ack("Signal", pipeline_id):
            self._send(ps_guid_packet("Signal", pipeline_id))

    def signal_ack(
        self,
        pipeline_id: typing.Optional[uuid.UUID] = None,
    ) -> None:
        self._send(ps_guid_packet("SignalAck", pipeline_id))

    def _read_task(self):
        try:
            self._read()

        except Exception as e:
            self._incoming.put(e)

        finally:
            with self._wait:
                for key in list(self._wait_set):
                    self._wait_set.remove(key)
                self._wait.notify_all()

    def _read(self) -> None:
        buffer = bytearray()
        while True:
            try:
                end_idx = buffer.index(b"\n")
            except ValueError:
                # Don't have enough data - wait for more to arrive.
                read_data = self._recv()
                if not read_data:
                    break

                buffer += read_data
                continue

            raw_element = bytes(buffer[:end_idx])
            buffer = buffer[end_idx + 1 :]

            element = ElementTree.fromstring(raw_element)
            ps_guid = uuid.UUID(element.attrib["PSGuid"].upper())
            if ps_guid == uuid.UUID(int=0):
                ps_guid = None

            if element.tag == "Data":
                psrp_data = base64.b64decode(element.text) if element.text else b""
                stream_type = (
                    psrpcore.StreamType.prompt_response
                    if element.attrib.get("Stream", "") == "PromptResponse"
                    else psrpcore.StreamType.default
                )
                payload = psrpcore.PSRPPayload(psrp_data, stream_type, ps_guid)
                self._incoming.put(OutOfProcPacket("Data", ps_guid, payload))

            elif element.tag.endswith("Ack"):
                pipeline = str(ps_guid) if ps_guid else ""
                with self._wait:
                    self._wait_set.remove(f"{element.tag}:{pipeline.upper()}")
                    self._wait.notify_all()

            else:
                self._incoming.put(OutOfProcPacket(element.tag, ps_guid, None))

    def _open(self) -> None:
        raise NotImplementedError()

    def _close(self) -> None:
        raise NotImplementedError()

    def _recv(self) -> typing.Optional[bytes]:
        raise NotImplementedError()

    def _send(self, data: bytes) -> None:
        raise NotImplementedError()

    @contextlib.contextmanager
    def _wait_ack(
        self,
        action: typing.Optional[str],
        pipeline_id: typing.Optional[uuid.UUID] = None,
    ):
        if not action:
            yield
            return

        pipeline = str(pipeline_id) if pipeline_id else ""
        key = f"{action}Ack:{pipeline.upper()}"
        with self._wait:
            self._wait_set.add(key)
            yield
            self._wait.wait_for(lambda: key not in self._wait_set)


class ClientTransport(OutOfProcTransport[psrpcore.ClientRunspacePool]):
    def __init__(self, runspace: psrpcore.ClientRunspacePool, executable: str) -> None:
        super().__init__(runspace)
        self._executable = executable
        self._process = None

    def _open(self) -> None:
        pipe = subprocess.PIPE
        self._process = subprocess.Popen([self._executable, "-NoLogo", "-s"], stdin=pipe, stdout=pipe, stderr=pipe)

    def _close(self) -> None:
        if self._process.poll() is None:
            self._process.kill()
            self._process.wait()

    def _recv(self) -> typing.Optional[bytes]:
        stdout = self._process.stdout.readline()
        if not stdout:
            stdout, stderr = self._process.communicate()
            if stderr:
                raise Exception(stderr.decode())

        return stdout

    def _send(self, data: bytes) -> None:
        self._process.stdin.write(data)
        self._process.stdin.flush()


class ServerTransport(OutOfProcTransport[psrpcore.ServerRunspacePool]):
    def __init__(self, runspace: psrpcore.ServerRunspacePool, pipe_name: str) -> None:
        super().__init__(runspace)
        self.pipe_name = pipe_name

    def data(
        self,
        wait_ack: bool = False,
    ) -> bool:
        return super().data(wait_ack=wait_ack)


class UnixDomainSocket(ServerTransport):
    def __init__(self, runspace: psrpcore.ServerRunspacePool, pipe_name: str) -> None:
        super().__init__(runspace, pipe_name)
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._conn: typing.Optional[socket.socket] = None
        self._sock_lock = threading.Lock()

    def _open(self) -> None:
        self._sock.bind(self.pipe_name)
        self._sock.listen(1)

    def _close(self) -> None:
        if self._conn:
            self._conn.shutdown(socket.SHUT_RDWR)
            self._conn.close()

        self._conn = None

        self._sock.shutdown(socket.SHUT_RDWR)
        self._sock.close()

    def _recv(self) -> typing.Optional[bytes]:
        return self._get_sock().recv(BUFFER_SIZE)

    def _send(self, data: bytes) -> None:
        self._get_sock().sendall(data)

    def _get_sock(self) -> socket.socket:
        with self._sock_lock:
            if not self._conn:
                self._conn = self._sock.accept()[0]

            return self._conn


class NamedPipe(ServerTransport):
    def __init__(self, runspace: psrpcore.ServerRunspacePool, pipe_name: str) -> None:
        super().__init__(runspace, pipe_name)
        self._pipe = win32pipe.CreateNamedPipe(
            "\\\\.\\pipe\\" + pipe_name,
            win32pipe.PIPE_ACCESS_DUPLEX | win32file.FILE_FLAG_OVERLAPPED,
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            1,
            BUFFER_SIZE,
            BUFFER_SIZE,
            0,
            None,
        )
        self._connected = False
        self._end_event = win32event.CreateEvent(None, True, 0, None)
        self._write_requested = win32event.CreateEvent(None, True, 0, None)
        self._pipe_lock = threading.Lock()
        self._write_lock = threading.Lock()

    def _open(self) -> None:
        pass

    def _close(self) -> None:
        win32event.SetEvent(self._end_event)
        with self._pipe_lock:
            if self._connected:
                win32pipe.DisconnectNamedPipe(self._pipe)
                self._connected = False

            if self._pipe:
                win32file.CloseHandle(self._pipe)
                self._pipe = None

    def _recv(self) -> typing.Optional[bytes]:
        buffer = win32file.AllocateReadBuffer(BUFFER_SIZE)
        overlapped = win32file.OVERLAPPED()
        overlapped.hEvent = win32event.CreateEvent(None, True, 0, None)

        while True:
            with self._write_lock:
                pass

            with self._pipe_lock:
                self._connect()
                res = win32file.ReadFile(self._pipe, buffer, overlapped)[0]

                if res == winerror.ERROR_SUCCESS:
                    bytes_read = win32file.GetOverlappedResult(self._pipe, overlapped, True)
                    return bytes(buffer[:bytes_read])

                elif res != winerror.ERROR_IO_PENDING:
                    msg = win32api.FormatMessage(res)
                    raise Exception(f"Named pipe read failed 0x{res:08X} - {msg}")

                wait_idx = win32event.WaitForMultipleObjects(
                    (overlapped.hEvent, self._end_event, self._write_requested),
                    False,
                    win32event.INFINITE,
                )

                if wait_idx != win32event.WAIT_OBJECT_0:
                    win32file.CancelIo(self._pipe)

                try:
                    bytes_read = win32file.GetOverlappedResult(self._pipe, overlapped, True)
                except win32file.error as err:
                    if err.winerror != winerror.ERROR_OPERATION_ABORTED:
                        raise
                    bytes_read = 0

                if bytes_read:
                    data = bytes(buffer[:bytes_read])
                    return data

                elif wait_idx == win32event.WAIT_OBJECT_0 + 1:
                    return

    def _send(self, data: bytes) -> None:
        with self._write_lock:
            win32event.SetEvent(self._write_requested)

            with self._pipe_lock:
                buffer = bytearray(data)
                offset = 0
                self._connect()

                while offset < len(data):
                    res, bytes_written = win32file.WriteFile(self._pipe, buffer[offset:])
                    if res != winerror.ERROR_SUCCESS:
                        msg = win32api.FormatMessage(res)
                        raise Exception(f"Named pipe write failed 0x{res:08X} - {msg}")

                    offset += bytes_written
                    win32file.FlushFileBuffers(self._pipe)

                win32event.ResetEvent(self._write_requested)

    def _connect(self):
        if not self._connected:
            overlapped = win32file.OVERLAPPED()
            overlapped.hEvent = win32event.CreateEvent(None, True, 0, None)

            res = win32pipe.ConnectNamedPipe(self._pipe, overlapped)

            if res == winerror.ERROR_IO_PENDING:
                wait_idx = win32event.WaitForMultipleObjects(
                    (overlapped.hEvent, self._end_event),
                    False,
                    win32event.INFINITE,
                )
                if wait_idx != win32event.WAIT_OBJECT_0:
                    raise Exception("Failed while waiting for client connection")

            elif res != winerror.ERROR_SUCCESS:
                msg = win32api.FormatMessage(res)
                raise Exception(f"Named pipe connect failed 0x{res:08X} - {msg}")

            self._connected = True


def get_runspace_pair(
    min_runspaces: int = 1, max_runspaces: int = 1
) -> typing.Tuple[psrpcore.ClientRunspacePool, psrpcore.ServerRunspacePool]:
    client = psrpcore.ClientRunspacePool(min_runspaces=min_runspaces, max_runspaces=max_runspaces)
    server = psrpcore.ServerRunspacePool()

    client.open()
    server.receive_data(client.data_to_send())
    server.next_event()
    server.next_event()
    client.receive_data(server.data_to_send())
    client.next_event()
    client.next_event()
    client.next_event()

    return client, server


def assert_xml_diff(actual: str, expected: str):
    # We don't care that the XML text is the exact same but rather if they represent the same object. Python versions
    # vary on how they order attributes of an element whereas xmldiff doesn't care.
    diff = _xmldiff.diff_texts(actual, expected)
    if len(diff) != 0:
        # The assertion for diff_texts isn't pretty and it's easier to see what the diff is by comparing the text.
        assert actual == expected


def serialize(value: typing.Any, **kwargs: typing.Any) -> ElementTree.Element:
    return psrpcore.types.serialize(value, FakeCryptoProvider(), **kwargs)


def deserialize(value: ElementTree.Element, **kwargs: typing.Any):
    return psrpcore.types.deserialize(value, FakeCryptoProvider(), **kwargs)


def ps_data_packet(
    data: bytes,
    stream_type: psrpcore.StreamType = psrpcore.StreamType.default,
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
    ps_guid = ps_guid or uuid.UUID(int=0)
    stream_name = b"Default" if stream_type == psrpcore.StreamType.default else b"PromptResponse"
    return b"<Data Stream='%s' PSGuid='%s'>%s</Data>\n" % (
        stream_name,
        str(ps_guid).lower().encode(),
        base64.b64encode(data),
    )


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
    ps_guid = ps_guid or uuid.UUID(int=0)
    return b"<%s PSGuid='%s' />\n" % (element.encode(), str(ps_guid).lower().encode())


def run_pipeline(
    client_pwsh: ClientTransport,
    script: str,
    host: typing.Optional[psrpcore.types.HostInfo] = None,
) -> typing.List[psrpcore.PSRPEvent]:
    ps = psrpcore.ClientPowerShell(client_pwsh.runspace, host=host)
    ps.add_script(script)
    ps.start()
    client_pwsh.command(ps.pipeline_id)
    client_pwsh.data()
    events = []
    while ps.state == psrpcore.types.PSInvocationState.Running:
        events.append(client_pwsh.next_event())
    ps.close()
    client_pwsh.close(ps.pipeline_id)

    return events


@pytest.fixture(scope="function")
def client_pwsh():
    """Creates an unopened Runspace Pool against a pwsh process."""
    if not PWSH_PATH:
        pytest.skip("Integration test requires pwsh")

    runspace = psrpcore.ClientRunspacePool()
    with ClientTransport(runspace, PWSH_PATH) as conn:
        yield conn


@pytest.fixture(scope="function")
def client_opened_pwsh():
    """Creates an Opened Runspace Pool against a pwsh process."""
    if not PWSH_PATH:
        pytest.skip("Integration test requires pwsh")

    host = psrpcore.types.HostInfo(
        IsHostNull=False,
        IsHostUINull=False,
        IsHostRawUINull=False,
        UseRunspaceHost=False,
        HostDefaultData=psrpcore.types.HostDefaultData(
            ForegroundColor=psrpcore.types.ConsoleColor.Blue,
            BackgroundColor=psrpcore.types.ConsoleColor.Red,
            CursorPosition=psrpcore.types.Coordinates(X=10, Y=20),
            WindowPosition=psrpcore.types.Coordinates(X=30, Y=40),
            CursorSize=5,
            BufferSize=psrpcore.types.Size(Width=60, Height=120),
            WindowSize=psrpcore.types.Size(Width=60, Height=120),
            MaxWindowSize=psrpcore.types.Size(Width=60, Height=120),
            MaxPhysicalWindowSize=psrpcore.types.Size(Width=60, Height=120),
            WindowTitle="My Window",
        ),
    )

    runspace = psrpcore.ClientRunspacePool(host=host)
    with ClientTransport(runspace, PWSH_PATH) as pwsh:
        pwsh.runspace.open()
        pwsh.data()
        while pwsh.runspace.state == psrpcore.types.RunspacePoolState.Opening:
            pwsh.next_event()

        yield pwsh


@pytest.fixture(scope="function")
def server_pwsh(tmp_path):
    """Creates a pipe PSRP server that can be called in pwsh."""
    if not PWSH_PATH:
        pytest.skip("Integration test requires pwsh")

    pipe_name = f"psrpcore-{str(uuid.uuid4()).upper()}"

    runspace = psrpcore.ServerRunspacePool()
    try:
        if os.name == "nt":
            transport = NamedPipe(runspace, pipe_name)

        else:
            pipe_name = str(tmp_path / pipe_name)
            transport = UnixDomainSocket(runspace, pipe_name)

        with transport:
            yield transport

    finally:
        if os.name != "nt":
            try:
                os.unlink(pipe_name)
            except FileNotFoundError:
                pass
