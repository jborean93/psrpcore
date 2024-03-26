# Copyright: (c) 2024, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

from __future__ import annotations

import base64
import os
import pathlib
import subprocess

import pytest

import psrpcore

from .conftest import PWSH_PATH, ClientTransport, run_pipeline


def test_clixml_shell(client_pwsh: ClientTransport) -> None:
    client_pwsh.runspace.open()
    client_pwsh.data()
    while client_pwsh.runspace.state == psrpcore.types.RunspacePoolState.Opening:
        client_pwsh.next_event()

    clixml_script = str(pathlib.Path(__file__).parent / "clixml_shell_runner.py")
    cmd = f"& python '{clixml_script}' | ForEach-Object {{ $_ }}"
    res = run_pipeline(client_pwsh, cmd)

    assert len(res) == 13

    assert isinstance(res[0], psrpcore.PipelineOutputEvent)
    assert isinstance(res[0].data, psrpcore.types.PSString)
    assert res[0].data == "string"

    assert isinstance(res[1], psrpcore.PipelineOutputEvent)
    assert isinstance(res[1].data, psrpcore.types.PSObject)
    assert res[1].data.other == "foo"
    assert res[1].data.value == 123

    assert isinstance(res[2], psrpcore.PipelineOutputEvent)
    assert isinstance(res[2].data, psrpcore.types.PSObject)
    assert res[2].data.InformationalRecord_Message == "warning as output"

    assert isinstance(res[3], psrpcore.ErrorRecordEvent)
    assert res[3].record.Exception.Message == "error as string"
    assert res[3].record.CategoryInfo.Category == psrpcore.types.ErrorCategory.NotSpecified

    assert isinstance(res[4], psrpcore.ErrorRecordEvent)
    assert res[4].record.Exception.Message == "error as record"
    assert res[4].record.CategoryInfo.Category == psrpcore.types.ErrorCategory.DeviceError

    assert isinstance(res[5], psrpcore.DebugRecordEvent)
    assert res[5].record.Message == "debug"

    assert isinstance(res[6], psrpcore.VerboseRecordEvent)
    assert res[6].record.Message == "verbose"

    assert isinstance(res[7], psrpcore.WarningRecordEvent)
    assert res[7].record.Message == "warning"

    assert isinstance(res[8], psrpcore.InformationRecordEvent)
    assert res[8].record.MessageData == "information as string"
    assert res[8].record.Source is None

    assert isinstance(res[9], psrpcore.InformationRecordEvent)
    assert res[9].record.MessageData == "information as record"
    assert res[9].record.Source == "my source"
    assert res[9].record.TimeGenerated == psrpcore.types.PSDateTime(1970, 1, 1)

    assert isinstance(res[10], psrpcore.ProgressRecordEvent)
    assert res[10].record.Activity == "progress"

    assert isinstance(res[11], psrpcore.PipelineOutputEvent)
    assert res[11].data == "final"

    assert isinstance(res[12], psrpcore.PipelineStateEvent)
    assert res[12].state == psrpcore.types.PSInvocationState.Completed


def test_clixml_shell_securestring(client_pwsh: ClientTransport) -> None:
    client_pwsh.runspace.open()

    client_pwsh.data()
    while client_pwsh.runspace.state == psrpcore.types.RunspacePoolState.Opening:
        client_pwsh.next_event()

    client_pwsh.runspace.exchange_key()
    client_pwsh.data()
    client_pwsh.next_event()

    cmd = f"""
& python -c @'
import sys
import psrpcore

shell = psrpcore.ClixmlShell()

shell.write_output(psrpcore.types.PSSecureString('secret'))
sys.stdout.write(shell.data_to_send())
'@ | ForEach-Object {{ $_ }}
"""
    res = run_pipeline(client_pwsh, cmd)

    assert len(res) == 2

    assert isinstance(res[0], psrpcore.PipelineOutputEvent)
    assert isinstance(res[0].data, psrpcore.types.PSSecureString)
    assert res[0].data.decrypt() == "secret"

    assert isinstance(res[1], psrpcore.PipelineStateEvent)
    assert res[1].state == psrpcore.types.PSInvocationState.Completed


def test_clixml_shell_with_no_buffer() -> None:
    shell = psrpcore.ClixmlShell()
    shell.write_output("foo")
    out1 = shell.data_to_send()

    assert out1.startswith("#< CLIXML")

    out2 = shell.data_to_send()
    assert out2 == ""


def test_clixml_output() -> None:
    cmd = r"""
$DebugPreference = 'Continue'
$VerbosePreference = 'Continue'
$WarningPreference = 'Continue'
$InformationPreference = 'Continue'

"string" | Add-Member -NotePropertyName MyProp -NotePropertyValue foo -PassThru
1
[PSCustomObject]@{
    PSTypeName = 'MyType'
    Prop1 = $true
    Prop2 = [Int64]2
}

$host.UI.WriteLine('output as stderr')
Write-Host host

$host.UI.WriteErrorLine('error as string')
Write-Error 'error as record'

$host.UI.WriteDebugLine('debug as string')
Write-Debug 'debug as record'

$host.UI.WriteVerboseLine('verbose as string')
Write-Verbose 'verbose as record'

$host.UI.WriteWarningLine('warning as string')
Write-Warning 'warning as record'

$host.UI.WriteInformation([System.Management.Automation.InformationRecord]::new(
    'information from host',
    'host'
))
Write-Information 'information as record'
"""

    enc_cmd = base64.b64encode(cmd.encode("utf-16-le")).decode()
    res = subprocess.run(
        [PWSH_PATH or "pwsh", "-OutputFormat", "xml", "-EncodedCommand", enc_cmd],
        capture_output=True,
        text=True,
        check=True,
    )

    actual = psrpcore.ClixmlOutput.from_clixml([res.stdout, res.stderr])

    assert len(actual.output) == 9
    assert isinstance(actual.output[0], psrpcore.types.PSString)
    assert actual.output[0] == "string"

    assert isinstance(actual.output[1], psrpcore.types.PSInt)
    assert actual.output[1] == 1

    assert isinstance(actual.output[2], psrpcore.types.PSObject)
    assert actual.output[2].PSTypeNames[0] == "Deserialized.MyType"
    assert actual.output[2].Prop1 is True
    assert isinstance(actual.output[2].Prop2, psrpcore.types.PSInt64)
    assert actual.output[2].Prop2 == 2

    assert actual.output[3] == "output as stderr"
    assert actual.output[4] == os.linesep
    assert actual.output[5] == "host"
    assert actual.output[6] == os.linesep
    assert actual.output[7] == "information as record"
    assert actual.output[8] == os.linesep

    assert len(actual.error) == 2

    assert isinstance(actual.error[0], psrpcore.types.ErrorRecord)
    assert isinstance(actual.error[0].Exception, psrpcore.types.NETException)
    assert actual.error[0].Exception.Message == f"error as string{os.linesep}"
    assert actual.error[0].FullyQualifiedErrorId == "NativeCommandError"
    assert actual.error[0].CategoryInfo.Category == psrpcore.types.ErrorCategory.NotSpecified

    assert isinstance(actual.error[1], psrpcore.types.ErrorRecord)
    assert isinstance(actual.error[1], psrpcore.types.ErrorRecord)
    assert isinstance(actual.error[1].Exception, psrpcore.types.PSObject)
    assert actual.error[1].Exception.Message == "error as record"
    assert actual.error[1].FullyQualifiedErrorId == "Microsoft.PowerShell.Commands.WriteErrorException"
    assert actual.error[1].CategoryInfo.Category == psrpcore.types.ErrorCategory.NotSpecified

    assert len(actual.debug) == 2
    assert isinstance(actual.debug[0], psrpcore.types.DebugRecord)
    assert actual.debug[0].Message == "debug as string"
    assert isinstance(actual.debug[1], psrpcore.types.DebugRecord)
    assert actual.debug[1].Message == "debug as record"

    assert len(actual.verbose) == 2
    assert isinstance(actual.verbose[0], psrpcore.types.VerboseRecord)
    assert actual.verbose[0].Message == "verbose as string"
    assert isinstance(actual.verbose[1], psrpcore.types.VerboseRecord)
    assert actual.verbose[1].Message == "verbose as record"

    assert len(actual.warning) == 2
    assert isinstance(actual.warning[0], psrpcore.types.WarningRecord)
    assert actual.warning[0].Message == "warning as string"
    assert isinstance(actual.warning[1], psrpcore.types.WarningRecord)
    assert actual.warning[1].Message == "warning as record"

    assert actual.progress == []

    assert len(actual.information) == 2
    assert isinstance(actual.information[0], psrpcore.types.InformationRecord)
    assert isinstance(actual.information[0].MessageData, psrpcore.types.PSObject)
    assert actual.information[0].MessageData.Message == "host"
    assert actual.information[0].Tags == ["PSHOST"]

    assert isinstance(actual.information[1], psrpcore.types.InformationRecord)
    assert isinstance(actual.information[1].MessageData, psrpcore.types.PSString)
    assert actual.information[1].MessageData == "information as record"
    assert actual.information[1].Tags == []


def test_clixml_output_securestring() -> None:
    res = subprocess.run(
        [PWSH_PATH or "pwsh", "-OutputFormat", "xml", "-Command", "ConvertTo-SecureString -Force -AsPlainText secret"],
        capture_output=True,
        text=True,
        check=True,
    )

    actual = psrpcore.ClixmlOutput.from_clixml([res.stdout, res.stderr])
    assert len(actual.output) == 1
    assert isinstance(actual.output[0], psrpcore.types.PSSecureString)
    assert actual.output[0].decrypt() == "secret"


def test_clixml_output_progress() -> None:
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

    actual = psrpcore.ClixmlOutput.from_clixml(res.stderr)

    assert len(actual.progress) == 1
    assert isinstance(actual.progress[0], psrpcore.types.ProgressRecord)
    assert actual.progress[0].Activity == "progress"


def test_climxl_output_empty_string() -> None:
    actual = psrpcore.ClixmlOutput.from_clixml("")
    assert actual.output == []
    assert actual.error == []
    assert actual.debug == []
    assert actual.verbose == []
    assert actual.warning == []
    assert actual.progress == []
    assert actual.information == []


def test_climxl_output_empty_list_of_strings() -> None:
    actual = psrpcore.ClixmlOutput.from_clixml(["", ""])
    assert actual.output == []
    assert actual.error == []
    assert actual.debug == []
    assert actual.verbose == []
    assert actual.warning == []
    assert actual.progress == []
    assert actual.information == []


@pytest.mark.skipif(os.name != "nt", reason="Uses Windows specific code")
def test_clixml_decrypt_failure() -> None:
    clixml = '<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><SS>0001</SS></Objs>'

    actual = psrpcore.ClixmlOutput.from_clixml(clixml)
    assert len(actual.output) == 1
    assert isinstance(actual.output[0], psrpcore.types.PSSecureString)

    with pytest.raises(OSError):
        actual.output[0].decrypt()
