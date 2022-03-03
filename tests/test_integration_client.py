# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import datetime
import time

import pytest

import psrpcore

from .conftest import COMPLEX_STRING, ClientTransport, run_pipeline


def open_runspace(client_pwsh: ClientTransport):
    client_pwsh.runspace.open()
    client_pwsh.data()
    while client_pwsh.runspace.state == psrpcore.types.RunspacePoolState.Opening:
        client_pwsh.next_event()


def test_client_runspace_open_close(client_pwsh: ClientTransport):
    runspace = client_pwsh.runspace
    runspace.open()

    client_pwsh.data()

    session_cap = client_pwsh.next_event()
    assert isinstance(session_cap, psrpcore.SessionCapabilityEvent)

    app_private = client_pwsh.next_event()
    assert isinstance(app_private, psrpcore.ApplicationPrivateDataEvent)

    state = client_pwsh.next_event()
    assert isinstance(state, psrpcore.RunspacePoolStateEvent)
    assert runspace.state == psrpcore.types.RunspacePoolState.Opened

    client_pwsh.close()

    state = client_pwsh.next_event()
    assert isinstance(state, psrpcore.RunspacePoolStateEvent)
    assert runspace.state == psrpcore.types.RunspacePoolState.Closing

    state = client_pwsh.next_event()
    assert isinstance(state, psrpcore.RunspacePoolStateEvent)
    assert runspace.state == psrpcore.types.RunspacePoolState.Closed


def test_runspace_application_arguments(client_pwsh: ClientTransport):
    runspace = client_pwsh.runspace
    runspace.application_arguments = {"arg1": "value", "testing": "test"}
    open_runspace(client_pwsh)

    res = run_pipeline(client_pwsh, "$PSSenderInfo.ApplicationArguments")
    assert len(res) == 2
    assert isinstance(res[0], psrpcore.PipelineOutputEvent)
    assert isinstance(res[0].data, dict)
    assert res[0].data["testing"] == "test"
    assert res[0].data["arg1"] == "value"
    assert isinstance(res[1], psrpcore.PipelineStateEvent)

    runspace.close()
    client_pwsh.close()


def test_runspace_with_pipeline_output(client_pwsh: ClientTransport):
    open_runspace(client_pwsh)

    runspace = client_pwsh.runspace

    ps = psrpcore.ClientPowerShell(runspace)
    ps.add_script(
        """$VerbosePreference = 'Continue'
$DebugPreference = 'Continue'
$WarningPreference = 'Continue'

$complexString = "treble clef\n _x0000_ _X0000_ $([Char]::ConvertFromUtf32(0x0001D11E)) café"

# Test out the streams
"output"
Write-Verbose -Message "verbose"
Write-Debug -Message "debug"
Write-Warning -Message "warning"
Write-Information "information"

# Test out different objects
$complexString
[char]"é"
$true
# Ticks for EPOCH (1970-01-01)
[DateTime]::new(621355968000000000, 'Utc')
[TimeSpan]::new(131249435)
[Byte]129
[SByte]-29
[UInt16]2393
[Int16]-2393
[UInt32]2147383648
[Int32]-2147383648
[UInt64]9223036854775808
[Int64]-9223036854775808
[Single]11020.101
[Double]129320202.223
[Decimal]1291921.101291
,[Text.Encoding]::UTF8.GetBytes("abcdef")
[Guid]::Empty
[Uri]"https://github.com"
$null
[Version]"1.2.3.4"
[xml]"<obj>test</obj>"
{ echo "scriptblock" }
ConvertTo-SecureString -AsPlainText -Force -String "test"
[IO.FileMode]::Open

$obj = [PSCustomObject]@{
    Property = 'value'
    OtherProp = 1
    Recursive = $null
}
$obj.Recursive = $obj
$obj

@{hash = "value"}

$dict = [System.Collections.Generic.Dictionary[[string], [int]]]::new()
$dict["key"] = 1
$dict

,@(1, "string")

,[System.Collections.Generic.List[Object]]@(2, "string")

[System.Management.Automation.ProgressRecord]::new(
    10,
    ($complexString + " - activity"),
    ($complexString + " - status")
)

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;

public class PSRPCore
{
    public static IEnumerable<int> MyEnumerable(int max)
    {
        for(int i = 0; i < max; i++)
            yield return i;
    }
}
'@

,[PSRPCore]::MyEnumerable(5)
"""
    )
    ps.start()

    client_pwsh.command(ps.pipeline_id)
    client_pwsh.data()
    events = []
    while ps.state == psrpcore.types.PSInvocationState.Running:
        events.append(client_pwsh.next_event())

    assert ps.state == psrpcore.types.PSInvocationState.Completed
    assert len(events) == 38

    assert isinstance(events[0], psrpcore.PipelineOutputEvent)
    assert events[0].data == "output"

    assert isinstance(events[1], psrpcore.VerboseRecordEvent)
    assert isinstance(events[1].record, psrpcore.types.VerboseRecord)
    assert events[1].record.Message == "verbose"

    assert isinstance(events[2], psrpcore.DebugRecordEvent)
    assert isinstance(events[2].record, psrpcore.types.DebugRecord)
    assert events[2].record.Message == "debug"

    assert isinstance(events[3], psrpcore.WarningRecordEvent)
    assert isinstance(events[3].record, psrpcore.types.WarningRecord)
    assert events[3].record.Message == "warning"

    assert isinstance(events[4], psrpcore.InformationRecordEvent)
    assert isinstance(events[4].record, psrpcore.types.InformationRecord)
    assert events[4].record.MessageData == "information"
    assert events[4].record.Source == "Write-Information"
    assert events[4].record.Tags == []

    assert isinstance(events[5], psrpcore.PipelineOutputEvent)
    assert isinstance(events[5].data, psrpcore.types.PSString)
    assert events[5].data == COMPLEX_STRING

    assert isinstance(events[6], psrpcore.PipelineOutputEvent)
    assert isinstance(events[6].data, psrpcore.types.PSChar)
    assert events[6].data == 233
    assert str(events[6].data) == "é"

    assert isinstance(events[7], psrpcore.PipelineOutputEvent)
    assert events[7].data is True

    assert isinstance(events[8], psrpcore.PipelineOutputEvent)
    assert isinstance(events[8].data, psrpcore.types.PSDateTime)
    assert events[8].data == psrpcore.types.PSDateTime(1970, 1, 1, 0, 0, tzinfo=datetime.timezone.utc, nanosecond=0)

    assert isinstance(events[9], psrpcore.PipelineOutputEvent)
    assert isinstance(events[9].data, psrpcore.types.PSDuration)
    events[9].data == psrpcore.types.PSDuration(seconds=13, microseconds=124943, nanoseconds=500)

    assert isinstance(events[10], psrpcore.PipelineOutputEvent)
    assert isinstance(events[10].data, psrpcore.types.PSByte)
    assert events[10].data == 129

    assert isinstance(events[11], psrpcore.PipelineOutputEvent)
    assert isinstance(events[11].data, psrpcore.types.PSSByte)
    assert events[11].data == -29

    assert isinstance(events[12], psrpcore.PipelineOutputEvent)
    assert isinstance(events[12].data, psrpcore.types.PSUInt16)
    assert events[12].data == 2393

    assert isinstance(events[13], psrpcore.PipelineOutputEvent)
    assert isinstance(events[13].data, psrpcore.types.PSInt16)
    assert events[13].data == -2393

    assert isinstance(events[14], psrpcore.PipelineOutputEvent)
    assert isinstance(events[14].data, psrpcore.types.PSUInt)
    assert events[14].data == 2147383648

    assert isinstance(events[15], psrpcore.PipelineOutputEvent)
    assert isinstance(events[15].data, psrpcore.types.PSInt)
    assert events[15].data == -2147383648

    assert isinstance(events[16], psrpcore.PipelineOutputEvent)
    assert isinstance(events[16].data, psrpcore.types.PSUInt64)
    assert events[16].data == 9223036854775808

    assert isinstance(events[17], psrpcore.PipelineOutputEvent)
    assert isinstance(events[17].data, psrpcore.types.PSInt64)
    assert events[17].data == -9223036854775808

    assert isinstance(events[18], psrpcore.PipelineOutputEvent)
    assert isinstance(events[18].data, psrpcore.types.PSSingle)
    assert events[18].data == psrpcore.types.PSSingle(11020.101)

    assert isinstance(events[19], psrpcore.PipelineOutputEvent)
    assert isinstance(events[19].data, psrpcore.types.PSDouble)
    assert events[19].data == psrpcore.types.PSDouble(129320202.223)

    assert isinstance(events[20], psrpcore.PipelineOutputEvent)
    assert isinstance(events[20].data, psrpcore.types.PSDecimal)
    assert events[20].data == psrpcore.types.PSDecimal("1291921.101291")

    assert isinstance(events[21], psrpcore.PipelineOutputEvent)
    assert isinstance(events[21].data, psrpcore.types.PSByteArray)
    assert events[21].data == b"abcdef"

    assert isinstance(events[22], psrpcore.PipelineOutputEvent)
    assert isinstance(events[22].data, psrpcore.types.PSGuid)
    assert events[22].data == psrpcore.types.PSGuid(int=0)

    assert isinstance(events[23], psrpcore.PipelineOutputEvent)
    assert isinstance(events[23].data, psrpcore.types.PSUri)
    assert events[23].data == "https://github.com/"

    assert isinstance(events[24], psrpcore.PipelineOutputEvent)
    assert events[24].data is None

    assert isinstance(events[25], psrpcore.PipelineOutputEvent)
    assert isinstance(events[25].data, psrpcore.types.PSVersion)
    assert events[25].data == psrpcore.types.PSVersion("1.2.3.4")

    assert isinstance(events[26], psrpcore.PipelineOutputEvent)
    assert isinstance(events[26].data, psrpcore.types.PSXml)
    assert events[26].data == "<obj>test</obj>"

    assert isinstance(events[27], psrpcore.PipelineOutputEvent)
    assert isinstance(events[27].data, psrpcore.types.PSScriptBlock)
    assert events[27].data == ' echo "scriptblock" '

    assert isinstance(events[28], psrpcore.PipelineOutputEvent)
    assert isinstance(events[28].data, psrpcore.types.PSSecureString)
    with pytest.raises(psrpcore.MissingCipherError):
        events[28].data.decrypt()

    assert isinstance(events[29], psrpcore.PipelineOutputEvent)
    assert isinstance(events[29].data, psrpcore.types.PSInt)
    assert events[29].data == 3
    assert str(events[29].data) == "Open"

    assert isinstance(events[30], psrpcore.PipelineOutputEvent)
    assert isinstance(events[30].data, psrpcore.types.PSCustomObject)
    assert events[30].data["Property"] == "value"
    assert events[30].data["OtherProp"] == 1

    assert isinstance(events[31], psrpcore.PipelineOutputEvent)
    assert isinstance(events[31].data, psrpcore.types.PSDict)
    assert events[31].data.PSTypeNames[0] == "System.Collections.Hashtable"
    assert events[31].data["hash"] == "value"

    assert isinstance(events[32], psrpcore.PipelineOutputEvent)
    assert isinstance(events[32].data, psrpcore.types.PSDict)
    assert events[32].data.PSTypeNames[0].startswith("Deserialized.System.Collections.Generic.Dictionary`2")
    assert events[32].data["key"] == 1

    assert isinstance(events[33], psrpcore.PipelineOutputEvent)
    assert isinstance(events[33].data, psrpcore.types.PSList)
    assert events[33].data.PSTypeNames[0] == "Deserialized.System.Object[]"
    assert events[33].data == [1, "string"]

    assert isinstance(events[34], psrpcore.PipelineOutputEvent)
    assert isinstance(events[34].data, psrpcore.types.PSList)
    assert events[34].data.PSTypeNames[0].startswith("Deserialized.System.Collections.Generic.List`1")
    assert events[34].data == [2, "string"]

    assert isinstance(events[35], psrpcore.PipelineOutputEvent)
    assert isinstance(events[35].data, psrpcore.types.ProgressRecord)
    assert events[35].data.Activity == COMPLEX_STRING + " - activity"
    assert events[35].data.ActivityId == 10
    assert events[35].data.CurrentOperation is None
    assert events[35].data.ParentActivityId == -1
    assert events[35].data.PercentComplete == -1
    assert events[35].data.RecordType == psrpcore.types.ProgressRecordType.Processing
    assert events[35].data.SecondsRemaining == -1
    assert events[35].data.StatusDescription == COMPLEX_STRING + " - status"

    assert isinstance(events[36], psrpcore.PipelineOutputEvent)
    assert isinstance(events[36].data, psrpcore.types.PSIEnumerable)
    assert events[36].data == [0, 1, 2, 3, 4]

    assert isinstance(events[37], psrpcore.PipelineStateEvent)
    assert events[37].state == psrpcore.types.PSInvocationState.Completed
    assert ps.state == psrpcore.types.PSInvocationState.Completed

    runspace.exchange_key()
    client_pwsh.data()
    enc_key = client_pwsh.next_event()
    assert isinstance(enc_key, psrpcore.EncryptedSessionKeyEvent)
    assert events[28].data.decrypt() == "test"

    with pytest.raises(psrpcore.PSRPCoreError, match="Must close existing pipelines before closing the pool"):
        runspace.close()

    ps.close()
    assert ps.state == psrpcore.types.PSInvocationState.Completed
    client_pwsh.close(ps.pipeline_id)

    runspace.close()
    assert runspace.state == psrpcore.types.RunspacePoolState.Closed
    client_pwsh.close()


def test_pipeline_merge_unclaimed_error(client_pwsh: ClientTransport):
    open_runspace(client_pwsh)
    runspace = client_pwsh.runspace

    ps = psrpcore.ClientPowerShell(runspace)

    cmd1 = psrpcore.Command("Write-Error")
    cmd1.add_parameter("Message", "error")
    cmd2 = psrpcore.Command("Write-Output")

    ps.add_command(cmd1).add_command(cmd2)
    ps.start()
    client_pwsh.command(ps.pipeline_id)
    client_pwsh.data()

    err = client_pwsh.next_event()
    assert isinstance(err, psrpcore.ErrorRecordEvent)
    assert isinstance(err.record, psrpcore.types.ErrorRecord)
    assert err.record.Exception.Message == "error"

    state = client_pwsh.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == psrpcore.types.PSInvocationState.Completed
    assert ps.state == psrpcore.types.PSInvocationState.Completed

    client_pwsh.close(ps.pipeline_id)

    cmd2.merge_unclaimed = True
    ps.start()
    client_pwsh.command(ps.pipeline_id)
    client_pwsh.data()

    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert isinstance(err.record, psrpcore.types.ErrorRecord)
    assert err.record.Exception.Message == "error"

    state = client_pwsh.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == psrpcore.types.PSInvocationState.Completed
    assert ps.state == psrpcore.types.PSInvocationState.Completed

    ps.close()
    client_pwsh.close(ps.pipeline_id)

    runspace.close()
    client_pwsh.close()


def test_merge_pipeline_output(client_pwsh: ClientTransport):
    open_runspace(client_pwsh)
    runspace = client_pwsh.runspace

    cmd = psrpcore.Command(
        """$VerbosePreference = 'Continue'
$DebugPreference = 'Continue'
$WarningPreference = 'Continue'

"output"
Write-Error -Message "error"
Write-Verbose -Message "verbose"
Write-Debug -Message "debug"
Write-Warning -Message "warning"
Write-Information -MessageData "information"
    """,
        is_script=True,
    )
    cmd.redirect_all(psrpcore.types.PipelineResultTypes.Output)

    ps = psrpcore.ClientPowerShell(runspace)
    ps.add_command(cmd)
    ps.start()
    client_pwsh.command(ps.pipeline_id)
    client_pwsh.data()

    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert out.data == "output"

    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert isinstance(out.data, psrpcore.types.ErrorRecord)
    assert out.data.Exception.Message == "error"

    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert isinstance(out.data, psrpcore.types.VerboseRecord)
    assert out.data.Message == "verbose"

    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert isinstance(out.data, psrpcore.types.DebugRecord)
    assert out.data.Message == "debug"

    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert isinstance(out.data, psrpcore.types.WarningRecord)
    assert out.data.Message == "warning"

    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert isinstance(out.data, psrpcore.types.InformationRecord)
    assert out.data.MessageData == "information"

    state = client_pwsh.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == psrpcore.types.PSInvocationState.Completed
    assert ps.state == psrpcore.types.PSInvocationState.Completed

    ps.close()
    client_pwsh.close(ps.pipeline_id)

    runspace.close()
    client_pwsh.close()


def test_pipeline_progress_record(client_pwsh: ClientTransport):
    open_runspace(client_pwsh)

    cmd = (
        "Write-Progress -Activity act -Status status -Id 10 -PercentComplete 34 -SecondsRemaining 102 "
        "-CurrentOperation currentOp -ParentId 9"
    )
    res = run_pipeline(client_pwsh, cmd)
    assert len(res) == 2
    assert isinstance(res[0], psrpcore.ProgressRecordEvent)
    assert isinstance(res[0].record, psrpcore.types.ProgressRecord)
    assert res[0].record.Activity == "act"
    assert res[0].record.StatusDescription == "status"
    assert res[0].record.ActivityId == 10
    assert res[0].record.PercentComplete == 34
    assert res[0].record.SecondsRemaining == 102
    assert res[0].record.CurrentOperation == "currentOp"
    assert res[0].record.ParentActivityId == 9

    assert isinstance(res[1], psrpcore.PipelineStateEvent)
    assert res[1].state == psrpcore.types.PSInvocationState.Completed


def test_pipeline_input_data(client_pwsh: ClientTransport):
    open_runspace(client_pwsh)
    runspace = client_pwsh.runspace

    ps = psrpcore.ClientPowerShell(runspace, no_input=False)
    ps.add_script(
        """[CmdletBinding()]
param (
    [Parameter(Mandatory)]
    [String]
    $Name,

    [Parameter(ValueFromPipeline)]
    $InputObject,

    [Switch]
    $MySwitch
)

begin {
    "$($Name): begin $($MySwitch.IsPresent)"
}

process {
    "$($Name): process - $InputObject"
}

end {
    "$($Name): end"
}
    """,
    )
    ps.add_parameter("Name", "name value").add_parameter("MySwitch")
    ps.start()
    client_pwsh.command(ps.pipeline_id)
    client_pwsh.data()

    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert out.data == "name value: begin True"

    ps.send("input 1")
    ps.send("input 2")
    ps.send(None)
    client_pwsh.data()

    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert out.data == "name value: process - input 1"

    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert out.data == "name value: process - input 2"

    ps.send(b"ab")
    client_pwsh.data()
    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert out.data == "name value: process - 97 98"

    ps.send_eof()
    client_pwsh.data()
    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert out.data == "name value: end"

    state = client_pwsh.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == psrpcore.types.PSInvocationState.Completed
    assert ps.state == psrpcore.types.PSInvocationState.Completed

    ps.close()
    client_pwsh.close(ps.pipeline_id)

    runspace.close()
    client_pwsh.close()


def test_stop_pipeline(client_pwsh: ClientTransport):
    open_runspace(client_pwsh)
    runspace = client_pwsh.runspace

    ps = psrpcore.ClientPowerShell(runspace)
    ps.add_script("echo 'started'; sleep 10")
    ps.start()
    client_pwsh.command(ps.pipeline_id)
    client_pwsh.data()

    # Make sure the pipeline has started before we call stop. If the stop signal is received before the pipeline has
    # fully started it may not contain the error record under reason.
    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert out.data == "started"

    ps.begin_stop()
    assert ps.state == psrpcore.types.PSInvocationState.Stopping
    client_pwsh.signal(ps.pipeline_id)

    state = client_pwsh.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == psrpcore.types.PSInvocationState.Stopped
    assert ps.state == psrpcore.types.PSInvocationState.Stopped
    assert state.reason.FullyQualifiedErrorId == "PipelineStopped"

    ps.close()
    client_pwsh.close(ps.pipeline_id)

    runspace.close()
    client_pwsh.close()


def test_set_runspace_count(client_pwsh: ClientTransport):
    runspace = client_pwsh.runspace
    assert runspace.max_runspaces == 1
    assert runspace.min_runspaces == 1
    runspace.set_max_runspaces(5)
    runspace.set_min_runspaces(2)
    assert runspace.max_runspaces == 5
    assert runspace.min_runspaces == 2

    open_runspace(client_pwsh)

    runspace.set_max_runspaces(1)
    assert runspace.max_runspaces == 5
    client_pwsh.data()
    set_event = client_pwsh.next_event()
    assert isinstance(set_event, psrpcore.SetRunspaceAvailabilityEvent)
    assert set_event.success is False
    assert runspace.max_runspaces == 5

    runspace.set_max_runspaces(5)
    assert runspace.max_runspaces == 5
    assert runspace.data_to_send() is None

    runspace.set_max_runspaces(4)
    assert runspace.max_runspaces == 5
    client_pwsh.data()
    set_event = client_pwsh.next_event()
    assert isinstance(set_event, psrpcore.SetRunspaceAvailabilityEvent)
    assert set_event.success is True
    assert runspace.max_runspaces == 4

    runspace.set_min_runspaces(6)
    assert runspace.min_runspaces == 2
    client_pwsh.data()
    set_event = client_pwsh.next_event()
    assert isinstance(set_event, psrpcore.SetRunspaceAvailabilityEvent)
    assert set_event.success is False
    assert runspace.min_runspaces == 2

    runspace.set_min_runspaces(2)
    assert runspace.min_runspaces == 2
    assert runspace.data_to_send() is None

    runspace.set_min_runspaces(4)
    assert runspace.min_runspaces == 2
    client_pwsh.data()
    set_event = client_pwsh.next_event()
    assert isinstance(set_event, psrpcore.SetRunspaceAvailabilityEvent)
    assert set_event.success is True
    assert runspace.min_runspaces == 4

    runspace.get_available_runspaces()
    client_pwsh.data()
    get_event = client_pwsh.next_event()
    assert isinstance(get_event, psrpcore.GetRunspaceAvailabilityEvent)
    assert get_event.count == 4

    ps = psrpcore.ClientPowerShell(runspace)
    ps.add_script("sleep 60")
    ps.start()
    client_pwsh.command(ps.pipeline_id)
    client_pwsh.data()

    # Seems quite fragile - add a sleep in case the pipeline hadn't started yet
    time.sleep(0.5)

    runspace.get_available_runspaces()
    client_pwsh.data()
    get_event = client_pwsh.next_event()
    assert isinstance(get_event, psrpcore.GetRunspaceAvailabilityEvent)
    assert get_event.count == 3

    ps.begin_stop()
    assert ps.state == psrpcore.types.PSInvocationState.Stopping
    client_pwsh.signal(ps.pipeline_id)
    pipe_state = client_pwsh.next_event()
    assert pipe_state.state == psrpcore.types.PSInvocationState.Stopped
    assert ps.state == psrpcore.types.PSInvocationState.Stopped

    ps.close()
    client_pwsh.close(ps.pipeline_id)

    runspace.close()
    assert runspace.state == psrpcore.types.RunspacePoolState.Closed
    client_pwsh.close()


def test_reset_runspace_state(client_pwsh: ClientTransport):
    runspace = client_pwsh.runspace

    open_runspace(client_pwsh)

    run_pipeline(client_pwsh, "$global:test = 'value'")
    out = run_pipeline(client_pwsh, "$global:test")
    assert out[0].data == "value"

    runspace.reset_runspace_state()
    client_pwsh.data()
    set_event = client_pwsh.next_event()
    assert isinstance(set_event, psrpcore.SetRunspaceAvailabilityEvent)
    assert set_event.success is True

    out = run_pipeline(client_pwsh, "$global:test")
    assert out[0].data is None

    runspace.close()
    client_pwsh.close()


def test_pipeline_host_call(client_pwsh: ClientTransport):
    runspace_host = psrpcore.types.HostInfo(
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
    pipeline_host = psrpcore.types.HostInfo(UseRunspaceHost=False)
    runspace = client_pwsh.runspace
    runspace.host = runspace_host
    open_runspace(client_pwsh)

    res = run_pipeline(client_pwsh, "$host.UI.WriteLine('line')")
    assert isinstance(res[0], psrpcore.PipelineHostCallEvent)
    assert res[0].ci == -100
    assert res[0].method_identifier == psrpcore.types.HostMethodIdentifier.WriteLine2
    assert res[0].method_parameters == ["line"]

    res = run_pipeline(client_pwsh, "$host.UI.WriteLine('line')", host=pipeline_host)
    assert len(res) == 1
    assert isinstance(res[0], psrpcore.PipelineStateEvent)

    ps = psrpcore.ClientPowerShell(client_pwsh.runspace)
    ps.add_script("$host.UI.ReadLineAsSecureString(); $host.UI.RawUI.WindowTitle")
    ps.start()
    client_pwsh.command(ps.pipeline_id)
    client_pwsh.data()

    host_call = client_pwsh.next_event()
    assert isinstance(host_call, psrpcore.PipelineHostCallEvent)
    assert host_call.ci == 1
    assert host_call.method_identifier == psrpcore.types.HostMethodIdentifier.ReadLineAsSecureString
    assert host_call.method_parameters == []

    runspace.exchange_key()
    client_pwsh.data()
    client_pwsh.next_event()

    c_host = psrpcore.ClientHostResponder(ps)
    c_host.read_line_as_secure_string(host_call.ci, psrpcore.types.PSSecureString("secret"))
    client_pwsh.data()

    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert isinstance(out.data, psrpcore.types.PSSecureString)
    assert out.data.decrypt() == "secret"

    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert out.data == "My Window"

    state = client_pwsh.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == psrpcore.types.PSInvocationState.Completed
    assert ps.state == psrpcore.types.PSInvocationState.Completed

    ps.close()
    client_pwsh.close(ps.pipeline_id)

    runspace.close()
    client_pwsh.close()


def test_runspace_pool_host_call(client_pwsh: ClientTransport):
    runspace_host = psrpcore.types.HostInfo(
        IsHostNull=False,
        IsHostUINull=False,
    )
    runspace = client_pwsh.runspace
    runspace.host = runspace_host
    open_runspace(client_pwsh)

    res = run_pipeline(
        client_pwsh,
        """$rs = [Runspace]::DefaultRunspace
$rsHost = $rs.GetType().GetProperty("Host", 60).GetValue($rs)
$rsHost.UI.WriteWarningLine("test")""",
    )
    assert len(res) == 2
    assert isinstance(res[0], psrpcore.RunspacePoolHostCallEvent)
    assert res[0].ci == -100
    assert res[0].method_identifier == psrpcore.types.HostMethodIdentifier.WriteWarningLine
    assert res[0].method_parameters == ["test"]
    assert isinstance(res[1], psrpcore.PipelineStateEvent)

    runspace.exchange_key()
    client_pwsh.data()
    client_pwsh.next_event()

    ps = psrpcore.ClientPowerShell(runspace)
    ps.add_script(
        """$rs = [Runspace]::DefaultRunspace
$rsHost = $rs.GetType().GetProperty("Host", 60).GetValue($rs)

$rsHost.UI.PromptForCredential(
    "caption",
    "message",
    "username",
    "targetName",
    "Domain",
    "ReadOnlyUserName"
)"""
    )
    ps.start()

    client_pwsh.command(ps.pipeline_id)
    client_pwsh.data()
    host_call = client_pwsh.next_event()
    assert isinstance(host_call, psrpcore.RunspacePoolHostCallEvent)
    assert host_call.ci == 1
    assert host_call.method_identifier == psrpcore.types.HostMethodIdentifier.PromptForCredential2
    assert host_call.method_parameters == [
        "caption",
        "message",
        "username",
        "targetName",
        psrpcore.types.PSCredentialTypes.Domain.value,
        psrpcore.types.PSCredentialUIOptions.ReadOnlyUsername.value,
    ]

    c_host = psrpcore.ClientHostResponder(runspace)
    c_host.read_line_as_secure_string(
        host_call.ci, psrpcore.types.PSCredential("username", psrpcore.types.PSSecureString("password"))
    )
    client_pwsh.data()

    out = client_pwsh.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert isinstance(out.data, psrpcore.types.PSCredential)
    assert out.data.UserName == "username"
    assert isinstance(out.data.Password, psrpcore.types.PSSecureString)
    assert out.data.Password.decrypt() == "password"

    state = client_pwsh.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == psrpcore.types.PSInvocationState.Completed

    ps.close()
    client_pwsh.close(ps.pipeline_id)

    runspace.close()
    client_pwsh.close()


def test_get_command_metadata(client_pwsh: ClientTransport):
    open_runspace(client_pwsh)
    runspace = client_pwsh.runspace

    ps = psrpcore.ClientGetCommandMetadata(runspace, "*", command_type=psrpcore.types.CommandTypes.Cmdlet)
    ps.start()
    client_pwsh.command(ps.pipeline_id)
    client_pwsh.data()

    count = client_pwsh.next_event()
    assert isinstance(count, psrpcore.PipelineOutputEvent)
    assert isinstance(count.data, psrpcore.types.CommandMetadataCount)
    assert hasattr(count.data, "Count")
    res = []
    for _ in range(count.data.Count):
        event = client_pwsh.next_event()
        assert isinstance(event, psrpcore.PipelineOutputEvent)
        assert event.data.CommandType == psrpcore.types.CommandTypes.Cmdlet
        res.append(event)

    state = client_pwsh.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == psrpcore.types.PSInvocationState.Completed
    assert ps.state == psrpcore.types.PSInvocationState.Completed

    ps.close()
    client_pwsh.close(ps.pipeline_id)

    runspace.close()
    client_pwsh.close()


def test_user_event(client_pwsh: ClientTransport):
    open_runspace(client_pwsh)
    runspace = client_pwsh.runspace

    ps = psrpcore.ClientPowerShell(runspace)
    ps.add_script(
        """
        $null = $Host.Runspace.Events.SubscribeEvent(
            $null,
            "EventIdentifier",
            "EventIdentifier",
            $null,
            $null,
            $true,
            $true)
        $null = $Host.Runspace.Events.GenerateEvent(
            "EventIdentifier",
            "sender",
            @("my", "args"),
            "extra data")
        Start-Sleep -Milliseconds 500
        """
    )
    ps.start()
    client_pwsh.command(ps.pipeline_id)
    client_pwsh.data()

    event = client_pwsh.next_event()
    assert isinstance(event, psrpcore.UserEventEvent)
    assert isinstance(event.event, psrpcore.types.UserEvent)
    assert event.event.EventIdentifier == 1
    assert event.event.SourceIdentifier == "EventIdentifier"
    assert event.event.TimeGenerated is not None
    assert event.event.Sender == "sender"
    assert event.event.SourceArgs == ["my", "args"]
    assert event.event.MessageData == "extra data"
    assert event.event.ComputerName is None
    assert event.event.RunspaceId is not None

    state = client_pwsh.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == psrpcore.types.PSInvocationState.Completed
    assert ps.state == psrpcore.types.PSInvocationState.Completed

    ps.close()
    client_pwsh.close(ps.pipeline_id)

    runspace.close()
    client_pwsh.close()


def test_set_buffer_call(client_opened_pwsh: ClientTransport):
    runspace = client_opened_pwsh.runspace

    ps = psrpcore.ClientPowerShell(runspace)
    ps.add_script(
        """
        $coordinates = [System.Management.Automation.Host.Coordinates]::new(0, 1)
        $cell = [System.Management.Automation.Host.BufferCell]::new('a', 'White', 'Gray', 'Complete')
        $cells = $Host.UI.RawUI.NewBufferCellArray(3, 4, $cell)
        $host.UI.RawUI.SetBufferContents($coordinates, $cells)
    """
    )
    ps.start()
    client_opened_pwsh.command(ps.pipeline_id)
    client_opened_pwsh.data()

    host_call = client_opened_pwsh.next_event()
    assert isinstance(host_call, psrpcore.PipelineHostCallEvent)
    assert host_call.ci == -100
    assert host_call.method_identifier == psrpcore.types.HostMethodIdentifier.SetBufferContents2
    assert len(host_call.method_parameters) == 2

    coordinates = host_call.method_parameters[0]
    assert isinstance(coordinates, psrpcore.types.Coordinates)
    assert coordinates.X == 0
    assert coordinates.Y == 1

    contents = host_call.method_parameters[1]
    assert isinstance(contents, list)
    assert len(contents) == 4
    for row in contents:
        assert isinstance(row, list)
        assert len(row) == 3
        for cell in row:
            assert isinstance(cell, psrpcore.types.BufferCell)
            assert cell.Character == psrpcore.types.PSChar("a")
            assert cell.ForegroundColor == psrpcore.types.ConsoleColor.White
            assert isinstance(cell.ForegroundColor, psrpcore.types.ConsoleColor)
            assert cell.BackgroundColor == psrpcore.types.ConsoleColor.Gray
            assert isinstance(cell.BackgroundColor, psrpcore.types.ConsoleColor)
            assert cell.BufferCellType == psrpcore.types.BufferCellType.Complete


def test_pipeline_multiple_statements(client_opened_pwsh: ClientTransport):
    runspace = client_opened_pwsh.runspace

    ps = psrpcore.ClientPowerShell(runspace)
    ps.add_command("Set-Variable").add_parameters(Name="string", Value="foo")
    ps.add_statement()

    ps.add_command("Get-Variable").add_parameter("Name", "string")
    ps.add_command("Select-Object").add_parameter("Property", ["Name", "Value"])
    ps.add_statement()

    ps.add_command("Get-Variable").add_argument("string").add_parameter("ValueOnly", True)
    ps.add_command("Select-Object")
    ps.add_statement()

    ps.add_script("[PSCustomObject]@{ Value = $string }")
    ps.add_script("process { $_ | Select-Object -Property @{N='Test'; E={ $_.Value }} }")
    ps.start()

    client_opened_pwsh.command(ps.pipeline_id)
    client_opened_pwsh.data()
    events = []
    while ps.state == psrpcore.types.PSInvocationState.Running:
        events.append(client_opened_pwsh.next_event())

    assert ps.state == psrpcore.types.PSInvocationState.Completed
    assert len(events) == 4
    assert isinstance(events[0], psrpcore.PipelineOutputEvent)
    assert isinstance(events[0].data, psrpcore.types.PSObject)
    assert len(events[0].data.PSObject.extended_properties) == 2
    assert events[0].data.Name == "string"
    assert events[0].data.Value == "foo"

    assert isinstance(events[1], psrpcore.PipelineOutputEvent)
    assert events[1].data == "foo"

    assert isinstance(events[2], psrpcore.PipelineOutputEvent)
    assert len(events[2].data.PSObject.extended_properties) == 1
    assert events[2].data.Test == "foo"

    assert isinstance(events[3], psrpcore.PipelineStateEvent)
    assert events[3].state == psrpcore.types.PSInvocationState.Completed

    ps.close()
    assert ps.state == psrpcore.types.PSInvocationState.Completed
    client_opened_pwsh.close(ps.pipeline_id)
