# Copyright: (c) 2024, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

from __future__ import annotations

import base64
import ctypes
import dataclasses
import sys
import typing as t

from psrpcore.types import (
    ClixmlStream,
    DebugRecord,
    ErrorCategory,
    ErrorCategoryInfo,
    ErrorRecord,
    InformationRecord,
    NETException,
    ProgressRecord,
    PSCryptoProvider,
    PSInt64,
    PSObject,
    VerboseRecord,
    WarningRecord,
    add_note_property,
    deserialize_clixml,
    serialize_clixml,
)

crypt_protect_data: t.Callable[[bytes], bytes] | None = None
crypt_unprotect_data: t.Callable[[bytes], bytes] | None = None
if sys.platform == "win32":
    CRYPTPROTECT_UI_FORBIDDEN = 0x01

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.c_int32),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    def errcheck(result, func, args):  # type: ignore[no-untyped-def] # Uses internal sig types
        if result == 0:
            raise ctypes.WinError()
        return result

    CryptProtectData = ctypes.windll.crypt32.CryptProtectData
    CryptProtectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_wchar_p,
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int32,
        ctypes.POINTER(DATA_BLOB),
    ]
    CryptProtectData.restype = ctypes.c_int32
    CryptProtectData.errcheck = errcheck

    CryptUnprotectData = ctypes.windll.crypt32.CryptUnprotectData
    CryptUnprotectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_wchar_p,
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int32,
        ctypes.POINTER(DATA_BLOB),
    ]
    CryptUnprotectData.restype = ctypes.c_int32
    CryptUnprotectData.errcheck = errcheck

    def crypt_protect_data(
        value: bytes,
    ) -> bytes:
        value_buffer = ctypes.create_string_buffer(value)
        blob_in = DATA_BLOB(len(value), value_buffer)
        blob_out = DATA_BLOB()

        CryptProtectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(blob_out),
        )

        enc_data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)

        return enc_data

    def crypt_unprotect_data(
        value: bytes,
    ) -> bytes:
        # Windows the value is encrypted in memory. Non-Windows doesn't
        # have any encryption.
        value_buffer = ctypes.create_string_buffer(value)
        blob_in = DATA_BLOB(len(value), value_buffer)
        blob_out = DATA_BLOB()

        CryptUnprotectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(blob_out),
        )

        dec_data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.memset(blob_out.pbData, 0, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)

        return dec_data


class LocalCryptoProvider(PSCryptoProvider):
    """Crypto provider for local crypto exchanges."""

    def decrypt(
        self,
        value: str,
    ) -> str:
        b_value = base64.b16decode(value.upper())

        if crypt_unprotect_data is not None:
            b_value = crypt_unprotect_data(b_value)

        return b_value.decode("utf-16-le", errors="surrogatepass")

    def encrypt(
        self,
        value: str,
    ) -> str:
        b_value = value.encode("utf-16-le", errors="surrogatepass")

        if crypt_protect_data is not None:
            b_value = crypt_protect_data(b_value)

        return base64.b16encode(b_value).decode()


@dataclasses.dataclass(frozen=True)
class ClixmlOutput:
    """CLIXML output collection.

    Helper class that can be used to parse raw CLIXML strings into separated
    object collections.

    An example of how this can be used to get objects back from PowerShell:

    .. code-block:: python

        import subprocess

        import psrpcore

        res = subprocess.run(
            ['pwsh', '-OutputFormat', 'xml', '-Command', 'Get-Process -Id $pid'],
            text=True,
            capture_output=True,
            check=True,
        )
        out = psrpcore.ClixmlOutput.from_clixml([res.stdout, res.stderr])

        for obj in out.output:
            print(obj.Name)
    """

    output: list[t.Any] = dataclasses.field(default_factory=list)
    """Objects from the output stream."""

    error: list[ErrorRecord] = dataclasses.field(default_factory=list)
    """Objects from the error stream."""

    debug: list[DebugRecord] = dataclasses.field(default_factory=list)
    """Objects from the debug stream."""

    verbose: list[VerboseRecord] = dataclasses.field(default_factory=list)
    """Objects from the verbose stream."""

    warning: list[WarningRecord] = dataclasses.field(default_factory=list)
    """Objects from the warning stream."""

    progress: list[ProgressRecord] = dataclasses.field(default_factory=list)
    """Objects from the progress stream."""

    information: list[InformationRecord] = dataclasses.field(default_factory=list)
    """Objects fr om the information stream."""

    @classmethod
    def from_clixml(
        cls,
        clixml: str | list[str],
    ) -> ClixmlOutput:
        """Parse the CLIXML string into objects.

        Parsed the provided CLIXML string into their various strings and
        process well known output formats for each stream into a canonical
        type.

        Args:
            clixml: The raw CLIXML string to parse. This can be a list of
                strings if the CLIXML comes from multiple sources like
                stdout and stderr.

        Returns:
            ClixmlOutput: The processed CLIXML objects and the streams they
                were associated with.
        """
        out = ClixmlOutput()

        if not isinstance(clixml, list):
            clixml = [clixml]

        crypto_provider = LocalCryptoProvider()
        for xml in clixml:
            if not xml:
                continue

            raw = deserialize_clixml(xml, crypto_provider, preserve_streams=True)
            for obj, stream in raw:
                if stream == ClixmlStream.ERROR:
                    if isinstance(obj, ErrorRecord):
                        out.error.append(obj)
                    else:
                        out.error.append(
                            ErrorRecord(
                                Exception=NETException(Message=str(obj)),
                                CategoryInfo=ErrorCategoryInfo(
                                    Category=ErrorCategory.NotSpecified,
                                ),
                                FullyQualifiedErrorId="NativeCommandError",
                            ),
                        )

                elif stream == ClixmlStream.DEBUG:
                    out.debug.append(DebugRecord(Message=str(obj)))

                elif stream == ClixmlStream.VERBOSE:
                    out.verbose.append(VerboseRecord(Message=str(obj)))

                elif stream == ClixmlStream.WARNING:
                    out.warning.append(WarningRecord(Message=str(obj)))

                elif stream == ClixmlStream.PROGRESS:
                    out.progress.append(obj.Record)

                elif stream == ClixmlStream.INFORMATION:
                    out.information.append(obj)

                else:
                    out.output.append(obj)

        return out


class ClixmlShell:
    """Helper class for PowerShell minishell.

    This is a helper class that can be used to collect streams inside Python
    and emit the final CLIXML string for stdout/stderr that PowerShell can
    read. It is useful for exchanging richer objects between PowerShell and
    Python processes.

    The :meth:`data_to_send` function can be used to get the stream values as
    a CLIXML string to write to stdout. While this can be called multiple times
    PowerShell won't emit the records until the process ends.

    .. code-block:: python

        import sys

        import psrpcore

        class MyObj:
            def __init__(self) -> None:
                self.value = 123
                self.other = "foo"

        shell = psrpcore.ClixmlShell()
        shell.write_output("foo")
        shell.write_output({"foo": "bar"})
        shell.write_output(MyObj())

        sys.stdout.write(shell.data_to_send())

    In PowerShell the above Python script can be called with:

    .. code-block:: powershell

        $out = python my_script.py
        $out[0]  # foo
        $out[1].foo  # bar
        $out[2].value  # 123
        $out[2].other  # foo

    The PowerShell process must be capturing the output in some way, for
    example through a variable or redirection/pipelining.
    """

    def __init__(self) -> None:
        self._cipher = LocalCryptoProvider()
        self._stdout: list[tuple[t.Any, ClixmlStream]] = []
        self._written_marker = False

    def data_to_send(self) -> str:
        """Gets the CLIXML output string.

        Returns the string that should be written to stdout. This string is
        CLIXML string that contains the serialized streams provided to this
        shell.

        Returns:
            str: The string to write to stdout.
        """
        if self._written_marker:
            prefix = "\n"
        else:
            prefix = "#< CLIXML\n"
            self._written_marker = True

        stdout = ""
        if self._stdout:
            stdout = f"{prefix}{serialize_clixml(self._stdout, self._cipher)}"
            self._stdout = []

        return stdout

    def write_output(
        self,
        value: t.Any | None,
    ) -> None:
        """Write to output stream.

        Writes the value to the output stream. The value can be any object that
        is automatically translated according to the psrpcore
        serialization rules.

        Args:
            value: The value to write to the output stream.
        """
        self._stdout.append((value, ClixmlStream.OUTPUT))

    def write_error(
        self,
        value: str | ErrorRecord,
    ) -> None:
        """Write to error stream.

        Writes the string or :class:`psrpcore.types.ErrorRecord` to the error
        stream.

        Args:
            value: The string or ErrorRecord to write.
        """
        self._stdout.append((value, ClixmlStream.ERROR))

    def write_debug(
        self,
        value: str,
    ) -> None:
        """Write to debug stream.

        Writes the string to the debug stream. The emitted value is written
        in PowerShell through ``$host.UI.WriteDebugLine($value)`` and not as
        an actual DebugRecord.

        Args:
            value: The string to write.
        """
        self._stdout.append((value, ClixmlStream.DEBUG))

    def write_verbose(
        self,
        value: str,
    ) -> None:
        """Write to verbose stream.

        Writes the string to the verbose stream. The emitted value is written
        in PowerShell through ``$host.UI.WriteVerboseLine($value)`` and not as
        an actual VerboseRecord.

        Args:
            value: The string to write.
        """
        self._stdout.append((value, ClixmlStream.VERBOSE))

    def write_warning(
        self,
        value: str,
    ) -> None:
        """Write to warning stream.

        Writes the string to the warning stream. The emitted value is written
        in PowerShell through ``$host.UI.WriteWarningLine($value)`` and not as
        an actual WarningRecord.

        Args:
            value: The string to write.
        """
        self._stdout.append((value, ClixmlStream.WARNING))

    def write_progress(
        self,
        source_id: int,
        value: ProgressRecord,
    ) -> None:
        """Write to progress stream.

        Writes the :class:`psrpcore.types.ProcessRecord` to the progress
        stream. The emitted value is written in PowerShell through
        ``$host.UI.WriteProgress($sourceId, $value)`` and not as an actual
        ProgressRecord.

        Args:
            source_id: Unique identifier of the source of the record.
            value: The ProgressRecord to write.
        """
        obj = PSObject()
        add_note_property(obj, "SourceId", PSInt64(source_id))
        add_note_property(obj, "Record", value)
        self._stdout.append((obj, ClixmlStream.PROGRESS))

    def write_information(
        self,
        value: str | InformationRecord,
    ) -> None:
        """Write to information stream.

        Writes the string or :class:`psrpcore.types.InformationRecord` to the
        error information stream.

        Args:
            value: The string or InformationRecord to write.
        """
        self._stdout.append((value, ClixmlStream.INFORMATION))
