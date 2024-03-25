# Copyright: (c) 2024, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import base64
import os
import subprocess

import pytest

import psrpcore

from ..conftest import PWSH_PATH, ClientTransport, FakeCryptoProvider, run_pipeline


def test_deserialize_process_clixml() -> None:
    cmd = r"""
"string" | Add-Member -NotePropertyName MyProp -NotePropertyValue foo -PassThru
1
[PSCustomObject]@{
    PSTypeName = 'MyType'
    Prop1 = $true
    Prop2 = [Int64]2
}
"""

    enc_cmd = base64.b64encode(cmd.encode("utf-16-le")).decode()
    res = subprocess.run(
        [PWSH_PATH or "pwsh", "-OutputFormat", "xml", "-EncodedCommand", enc_cmd],
        capture_output=True,
        text=True,
    )

    actual = psrpcore.types.deserialize_clixml(res.stdout, FakeCryptoProvider())
    assert isinstance(actual, list)
    assert len(actual) == 3
    assert actual[0] == "string"
    assert isinstance(actual[0], psrpcore.types.PSString)
    assert actual[0].MyProp == "foo"
    assert actual[1] == 1
    assert isinstance(actual[1], psrpcore.types.PSInt)
    assert isinstance(actual[2], psrpcore.types.PSObject)
    assert actual[2].PSTypeNames == [
        "Deserialized.MyType",
        "Deserialized.System.Management.Automation.PSCustomObject",
        "Deserialized.System.Object",
    ]
    assert actual[2].Prop1 is True
    assert actual[2].Prop2 == 2
    assert isinstance(actual[2].Prop2, psrpcore.types.PSInt64)


def test_deserialize_process_clixml_preserve_streams() -> None:
    cmd = r"""
$VerbosePreference = 'Continue'
$WarningPreference = 'Continue'
$DebugPreference = 'Continue'

"string" | Add-Member -NotePropertyName MyProp -NotePropertyValue foo -PassThru
Write-Warning warning-as-output *>&1

Write-Error error
Write-Verbose verbose
Write-Warning warning
Write-Debug debug
Write-Information 1
"""

    enc_cmd = base64.b64encode(cmd.encode("utf-16-le")).decode()
    res = subprocess.run(
        [PWSH_PATH or "pwsh", "-OutputFormat", "xml", "-EncodedCommand", enc_cmd],
        capture_output=True,
        text=True,
    )

    actual_stdout = psrpcore.types.deserialize_clixml(
        res.stdout,
        FakeCryptoProvider(),
        preserve_streams=True,
    )
    assert isinstance(actual_stdout, list)
    assert len(actual_stdout) == 2

    assert isinstance(actual_stdout[0], tuple)
    assert len(actual_stdout[0]) == 2
    assert isinstance(actual_stdout[0][0], psrpcore.types.PSString)
    assert actual_stdout[0][0] == "string"
    assert actual_stdout[0][1] == psrpcore.types.ClixmlStream.OUTPUT

    assert isinstance(actual_stdout[1], tuple)
    assert len(actual_stdout[1]) == 2
    assert isinstance(actual_stdout[1][0], psrpcore.types.WarningRecord)
    assert actual_stdout[1][0].Message == "warning-as-output"
    assert actual_stdout[1][1] == psrpcore.types.ClixmlStream.OUTPUT

    actual_stderr = psrpcore.types.deserialize_clixml(
        res.stderr,
        FakeCryptoProvider(),
        preserve_streams=True,
    )
    assert isinstance(actual_stderr, list)
    assert len(actual_stderr) == 5

    assert isinstance(actual_stderr[0], tuple)
    assert len(actual_stderr[0]) == 2
    assert isinstance(actual_stderr[0][0], psrpcore.types.ErrorRecord)
    assert actual_stderr[0][0].Exception.Message == "error"
    assert actual_stderr[0][1] == psrpcore.types.ClixmlStream.ERROR

    assert isinstance(actual_stderr[1], tuple)
    assert len(actual_stderr[1]) == 2
    assert isinstance(actual_stderr[1][0], psrpcore.types.PSString)
    assert actual_stderr[1][0] == "verbose"
    assert actual_stderr[1][1] == psrpcore.types.ClixmlStream.VERBOSE

    assert isinstance(actual_stderr[2], tuple)
    assert len(actual_stderr[2]) == 2
    assert isinstance(actual_stderr[2][0], psrpcore.types.PSString)
    assert actual_stderr[2][0] == "warning"
    assert actual_stderr[2][1] == psrpcore.types.ClixmlStream.WARNING

    assert isinstance(actual_stderr[3], tuple)
    assert len(actual_stderr[3]) == 2
    assert isinstance(actual_stderr[3][0], psrpcore.types.PSString)
    assert actual_stderr[3][0] == "debug"
    assert actual_stderr[3][1] == psrpcore.types.ClixmlStream.DEBUG

    assert isinstance(actual_stderr[4], tuple)
    assert len(actual_stderr[4]) == 2
    assert isinstance(actual_stderr[4][0], psrpcore.types.InformationRecord)
    assert actual_stderr[4][0].MessageData == 1
    assert actual_stderr[4][1] == psrpcore.types.ClixmlStream.INFORMATION


def test_deserialize_process_clixml_progress() -> None:
    # Pwsh won't emit ProgressRecords even in CLIXML output if stdout is
    # redirected. As pytest will redirect stdout we use a tty to mock stdout
    # not being redirected. This is *nix only so we skip if we cannot use
    # pty. This should be removed if the below PR is ever accepted.
    # https://github.com/PowerShell/PowerShell/pull/21373
    pty = pytest.importorskip("pty")

    stdout_parent, stdout_child = pty.openpty()
    try:
        cmd = "Write-Progress -Activity progress"

        enc_cmd = base64.b64encode(cmd.encode("utf-16-le")).decode()
        res = subprocess.run(
            [PWSH_PATH or "pwsh", "-OutputFormat", "xml", "-EncodedCommand", enc_cmd],
            text=True,
            stdout=stdout_parent,
            stderr=subprocess.PIPE,
        )
    finally:
        os.close(stdout_parent)
        os.close(stdout_child)

    actual_stderr = psrpcore.types.deserialize_clixml(
        res.stderr,
        FakeCryptoProvider(),
        preserve_streams=True,
    )
    assert isinstance(actual_stderr, list)
    assert len(actual_stderr) == 1

    assert isinstance(actual_stderr[0], tuple)
    assert len(actual_stderr[0]) == 2
    assert isinstance(actual_stderr[0][0], psrpcore.types.PSCustomObject)
    assert actual_stderr[0][0].SourceId == 0
    assert isinstance(actual_stderr[0][0].Record, psrpcore.types.ProgressRecord)
    assert actual_stderr[0][0].Record.Activity == "progress"
    assert actual_stderr[0][1] == psrpcore.types.ClixmlStream.PROGRESS


def test_serialize_process_clixml(client_pwsh: ClientTransport) -> None:
    obj1 = psrpcore.types.PSString("string")
    obj1.PSObject.extended_properties.append(psrpcore.types.PSNoteProperty("MyProp", "foo"))
    obj2 = psrpcore.types.PSCustomObject(
        PSTypeName="MyType",
        Prop1=True,
        Prop2=psrpcore.types.PSInt64(2),
    )
    clixml = psrpcore.types.serialize_clixml([obj1, 1, obj2], FakeCryptoProvider())

    client_pwsh.runspace.open()
    client_pwsh.data()
    while client_pwsh.runspace.state == psrpcore.types.RunspacePoolState.Opening:
        client_pwsh.next_event()

    cmd = rf"""
$data = @'
{clixml}
'@

[System.Management.Automation.PSSerializer]::Deserialize($data)
"""
    res = run_pipeline(client_pwsh, cmd)
    assert len(res) == 4
    assert isinstance(res[0], psrpcore.PipelineOutputEvent)
    assert isinstance(res[0].data, psrpcore.types.PSString)
    assert res[0].data == "string"
    assert res[0].data.MyProp == "foo"

    assert isinstance(res[1], psrpcore.PipelineOutputEvent)
    assert isinstance(res[1].data, psrpcore.types.PSInt)
    assert res[1].data == 1

    assert isinstance(res[2], psrpcore.PipelineOutputEvent)
    assert isinstance(res[2].data, psrpcore.types.PSObject)
    assert res[2].data.PSTypeNames == [
        "Deserialized.Deserialized.MyType",
        "Deserialized.Deserialized.System.Management.Automation.PSCustomObject",
        "Deserialized.Deserialized.System.Object",
    ]
    assert res[2].data.Prop1 is True
    assert res[2].data.Prop2 == 2
    assert isinstance(res[2].data.Prop2, psrpcore.types.PSInt64)

    assert isinstance(res[3], psrpcore.PipelineStateEvent)
    assert res[3].state == psrpcore.types.PSInvocationState.Completed
