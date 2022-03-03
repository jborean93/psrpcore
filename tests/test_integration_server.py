# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import os
import queue
import shutil
import threading
import typing

import pytest

import psrpcore

from .conftest import COMPLEX_STRING, ClientTransport, ServerTransport


def open_runspace(server_pwsh: ServerTransport) -> None:
    while server_pwsh.runspace.state in [
        psrpcore.types.RunspacePoolState.BeforeOpen,
        psrpcore.types.RunspacePoolState.Opening,
    ]:
        data = server_pwsh.next_payload()
        server_pwsh.runspace.receive_data(data.data)
        while True:
            if not server_pwsh.runspace.next_event():
                break

    while server_pwsh.data():
        pass
    server_pwsh.data_ack()


class BackgroundPipeline(threading.Thread):
    def __init__(
        self,
        client: ClientTransport,
        cmd: str,
        **kwargs: typing.Any,
    ) -> None:
        self.client = client
        self.events = queue.Queue()
        self.pipeline = psrpcore.ClientPowerShell(client.runspace)
        self.pipeline.add_script(cmd)
        if kwargs:
            self.pipeline.add_parameters(**kwargs)

        super().__init__(daemon=True)

    @property
    def remaining_events(self) -> typing.List[psrpcore.PSRPEvent]:
        event_list = []
        while True:
            try:
                event_list.append(self.events.get_nowait())
            except queue.Empty:
                break

        return event_list

    def run(self) -> None:
        self.pipeline.start()
        self.client.command(self.pipeline.pipeline_id)
        self.client.data()

        while self.pipeline.state == psrpcore.types.PSInvocationState.Running:
            e = self.client.next_event()
            if isinstance(e, psrpcore.PipelineOutputEvent) and isinstance(e.data, psrpcore.types.PSSecureString):
                self.client.runspace.exchange_key()
                self.client.data()
                self.client.next_event()

            self.events.put(e)

    def __enter__(self) -> "BackgroundPipeline":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Not ideal but ending the test closes the process and thus cleans up the resource. Because this pipeline is
        # probably connected to the test server trying to actually stop/close if it's still running will hang so just
        # rely on the client closing the entire process.
        if self.pipeline.state != psrpcore.types.PSInvocationState.Running:
            self.pipeline.close()
            self.client.close(self.pipeline.pipeline_id)
            self.join()


def test_open_and_close(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspacePool = [RunspaceFactory]::CreateRunspacePool(1, 1, $connInfo)
    $runspacePool.Open()
    $runspacePool.Dispose()
    """

    runspace = server_pwsh.runspace
    assert runspace.state == psrpcore.types.RunspacePoolState.BeforeOpen

    with BackgroundPipeline(client_opened_pwsh, cmd, Name=server_pwsh.pipe_name):
        connect = server_pwsh.next_payload()
        assert connect.action == "Data"
        assert connect.ps_guid is None

        runspace.receive_data(connect.data)
        assert runspace.state == psrpcore.types.RunspacePoolState.Opening

        session_cap = runspace.next_event()
        assert isinstance(session_cap, psrpcore.SessionCapabilityEvent)
        assert session_cap.ps_version == runspace.their_capability.PSVersion
        assert session_cap.protocol_version == runspace.their_capability.protocolversion
        assert session_cap.serialization_version == runspace.their_capability.SerializationVersion
        assert runspace.state == psrpcore.types.RunspacePoolState.Opening

        init_runspace = runspace.next_event()
        assert isinstance(init_runspace, psrpcore.InitRunspacePoolEvent)
        assert init_runspace.max_runspaces == 1
        assert init_runspace.min_runspaces == 1
        assert init_runspace.ps_thread_options == psrpcore.types.PSThreadOptions.Default
        assert init_runspace.apartment_state == psrpcore.types.ApartmentState.Unknown
        assert init_runspace.host_info.IsHostNull is True
        assert init_runspace.host_info.IsHostUINull is True
        assert init_runspace.host_info.IsHostRawUINull is True
        assert init_runspace.host_info.UseRunspaceHost is False
        assert init_runspace.host_info.HostDefaultData is None
        assert "PSVersionTable" in init_runspace.application_arguments

        assert runspace.state == psrpcore.types.RunspacePoolState.Opened
        assert runspace.max_runspaces == 1
        assert runspace.min_runspaces == 1
        assert runspace.thread_options == init_runspace.ps_thread_options
        assert runspace.apartment_state == init_runspace.apartment_state
        assert runspace.host.IsHostNull is True
        assert runspace.host.IsHostUINull is True
        assert runspace.host.IsHostRawUINull is True
        assert runspace.host.UseRunspaceHost is False
        assert runspace.host.HostDefaultData is None
        assert runspace.application_arguments == init_runspace.application_arguments
        assert runspace.next_event() is None

        server_pwsh.data()
        server_pwsh.data_ack()

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid is None
        server_pwsh.close_ack()


def test_rp_app_args(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param (
        [String]$Name,
        [Hashtable]$Arguments
    )

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspacePool = [RunspaceFactory]::CreateRunspacePool(1, 1, $connInfo, $null, $null, $Arguments)
    $runspacePool.Open()
    $runspacePool.Dispose()
    """

    runspace = server_pwsh.runspace
    assert runspace.state == psrpcore.types.RunspacePoolState.BeforeOpen

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
        Arguments={
            "test1": 1,
            "test2": "2",
        },
    ):
        connect = server_pwsh.next_payload()
        assert connect.action == "Data"
        assert connect.ps_guid is None

        runspace.receive_data(connect.data)
        session_cap = runspace.next_event()
        assert isinstance(session_cap, psrpcore.SessionCapabilityEvent)

        init_runspace = runspace.next_event()
        assert isinstance(init_runspace, psrpcore.InitRunspacePoolEvent)
        assert init_runspace.application_arguments["test1"] == 1
        assert init_runspace.application_arguments["test2"] == "2"

        assert runspace.state == psrpcore.types.RunspacePoolState.Opened
        assert runspace.application_arguments == init_runspace.application_arguments
        assert runspace.next_event() is None

        server_pwsh.data()
        server_pwsh.data_ack()
        server_pwsh.next_payload()
        server_pwsh.close_ack()


def test_pipe_output(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name, [String]$Script)

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspacePool = [RunspaceFactory]::CreateRunspacePool(1, 1, $connInfo)
    $runspacePool.Open()
    try {
        $ps = [PowerShell]::Create()
        $ps.RunspacePool = $runspacePool
        [void]$ps.AddScript($Script)
        $ps.Invoke()
    }
    finally {
        $runspacePool.Dispose()
    }
    """

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
        Script="my script",
    ) as ps:

        runspace = server_pwsh.runspace
        open_runspace(server_pwsh)

        command = server_pwsh.next_payload()
        assert command.action == "Command"
        assert command.ps_guid is not None
        server_pwsh.command_ack(command.ps_guid)

        s_ps = psrpcore.ServerPipeline(runspace, command.ps_guid)
        create_pipe = server_pwsh.next_event()
        assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
        assert isinstance(create_pipe.pipeline, psrpcore.PowerShell)
        assert create_pipe.pipeline_id == s_ps.pipeline_id
        assert create_pipe.pipeline.no_input is True
        assert len(create_pipe.pipeline.commands) == 1
        assert create_pipe.pipeline.commands[0].command_text == "my script"

        s_ps.start()
        s_ps.write_output(COMPLEX_STRING)
        s_ps.write_output(psrpcore.types.PSSecureString("secret"))
        s_ps.complete()
        server_pwsh.data()

        pub_key = server_pwsh.next_event()
        assert isinstance(pub_key, psrpcore.PublicKeyEvent)
        server_pwsh.data()

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid == s_ps.pipeline_id
        server_pwsh.close_ack(close.ps_guid)

        out = ps.events.get()
        assert isinstance(out, psrpcore.PipelineOutputEvent)
        assert out.data == COMPLEX_STRING

        out = ps.events.get()
        assert isinstance(out, psrpcore.PipelineOutputEvent)
        assert isinstance(out.data, psrpcore.types.PSSecureString)
        assert out.data.decrypt() == "secret"

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid is None
        server_pwsh.close_ack()


def test_merge_unclaimed(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspacePool = [RunspaceFactory]::CreateRunspacePool(1, 1, $connInfo)
    $runspacePool.Open()
    try {
        $ps = [PowerShell]::Create()
        $ps.RunspacePool = $runspacePool
        [void]$ps.AddCommand("Write-Error").AddParameter("Message", "Error").AddCommand("Write-Output")
        $ps.Commands.Commands[1].MergeUnclaimedPreviousCommandResults = 'Output, Error'
        $ps.Invoke()
    }
    finally {
        $runspacePool.Dispose()
    }
    """

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
    ):

        runspace = server_pwsh.runspace
        open_runspace(server_pwsh)

        command = server_pwsh.next_payload()
        assert command.action == "Command"
        server_pwsh.command_ack(command.ps_guid)

        s_ps = psrpcore.ServerPipeline(runspace, command.ps_guid)
        create_pipe = server_pwsh.next_event()
        assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
        assert isinstance(create_pipe.pipeline, psrpcore.PowerShell)
        assert create_pipe.pipeline_id == s_ps.pipeline_id
        assert len(create_pipe.pipeline.commands) == 2
        assert create_pipe.pipeline.no_input is True

        cmd1 = create_pipe.pipeline.commands[0]
        assert cmd1.command_text == "Write-Error"
        assert cmd1.parameters == [("Message", "Error")]
        assert cmd1.end_of_statement is False
        assert cmd1.is_script is False
        assert cmd1.merge_unclaimed is False
        assert cmd1.merge_my == psrpcore.types.PipelineResultTypes.none
        assert cmd1.merge_to == psrpcore.types.PipelineResultTypes.none
        assert cmd1.merge_error == psrpcore.types.PipelineResultTypes.none
        assert cmd1.merge_warning == psrpcore.types.PipelineResultTypes.none
        assert cmd1.merge_verbose == psrpcore.types.PipelineResultTypes.none
        assert cmd1.merge_debug == psrpcore.types.PipelineResultTypes.none
        assert cmd1.merge_information == psrpcore.types.PipelineResultTypes.none

        cmd2 = create_pipe.pipeline.commands[1]
        assert cmd2.command_text == "Write-Output"
        assert cmd2.parameters == []
        assert cmd2.end_of_statement is True
        assert cmd2.is_script is False
        assert cmd2.merge_unclaimed is True
        assert cmd2.merge_my == psrpcore.types.PipelineResultTypes.none
        assert cmd2.merge_to == psrpcore.types.PipelineResultTypes.none
        assert cmd2.merge_error == psrpcore.types.PipelineResultTypes.none
        assert cmd2.merge_warning == psrpcore.types.PipelineResultTypes.none
        assert cmd2.merge_verbose == psrpcore.types.PipelineResultTypes.none
        assert cmd2.merge_debug == psrpcore.types.PipelineResultTypes.none
        assert cmd2.merge_information == psrpcore.types.PipelineResultTypes.none

        s_ps.start()
        s_ps.write_output("Error")
        s_ps.complete()
        server_pwsh.data()

        close = server_pwsh.next_payload()
        server_pwsh.close_ack(close.ps_guid)
        server_pwsh.next_payload()
        server_pwsh.close_ack(None)


def test_merge_pipe_out(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspacePool = [RunspaceFactory]::CreateRunspacePool(1, 1, $connInfo)
    $runspacePool.Open()
    try {
        $ps = [PowerShell]::Create()
        $ps.RunspacePool = $runspacePool
        [void]$ps.AddScript(@'
$VerbosePreference = 'Continue'
$DebugPreference = 'Continue'
$WarningPreference = 'Continue'

"output"
Write-Error -Message "error"
Write-Verbose -Message "verbose"
Write-Debug -Message "debug"
Write-Warning -Message "warning"
Write-Information -MessageData "information"
'@)
        $ps.Commands.Commands[0].MergeMyResults("All", "Output")
        $ps.Invoke()
    }
    finally {
        $runspacePool.Dispose()
    }
    """

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
    ):

        runspace = server_pwsh.runspace
        open_runspace(server_pwsh)

        command = server_pwsh.next_payload()
        assert command.action == "Command"
        server_pwsh.command_ack(command.ps_guid)

        s_ps = psrpcore.ServerPipeline(runspace, command.ps_guid)
        create_pipe = server_pwsh.next_event()
        assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
        assert isinstance(create_pipe.pipeline, psrpcore.PowerShell)
        assert create_pipe.pipeline_id == s_ps.pipeline_id
        assert len(create_pipe.pipeline.commands) == 1
        assert create_pipe.pipeline.no_input is True

        cmd1 = create_pipe.pipeline.commands[0]
        assert cmd1.parameters == []
        assert cmd1.end_of_statement is True
        assert cmd1.is_script is True
        assert cmd1.merge_unclaimed is False
        assert cmd1.merge_my == psrpcore.types.PipelineResultTypes.none
        assert cmd1.merge_to == psrpcore.types.PipelineResultTypes.none
        assert cmd1.merge_error == psrpcore.types.PipelineResultTypes.Output
        assert cmd1.merge_warning == psrpcore.types.PipelineResultTypes.Output
        assert cmd1.merge_verbose == psrpcore.types.PipelineResultTypes.Output
        assert cmd1.merge_debug == psrpcore.types.PipelineResultTypes.Output
        assert cmd1.merge_information == psrpcore.types.PipelineResultTypes.Output

        s_ps.start()
        s_ps.complete()
        server_pwsh.data()

        close = server_pwsh.next_payload()
        server_pwsh.close_ack(close.ps_guid)
        server_pwsh.next_payload()
        server_pwsh.close_ack(None)


def test_progress_record(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspacePool = [RunspaceFactory]::CreateRunspacePool(1, 1, $connInfo)
    $runspacePool.Open()
    try {
        $ps = [PowerShell]::Create()
        $ps.RunspacePool = $runspacePool
        [void]$ps.AddCommand("Write-Progress").AddParameters([Ordered]@{
            Activity = "act"
            Status = "status"
            Id = 10
            PercentComplete = 34
            SecondsRemaining = 102
            CurrentOperation = "currentOp"
            ParentId = 9
        })
        $ps.Invoke()
        $ps.Streams.Progress
    }
    finally {
        $runspacePool.Dispose()
    }
    """

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
    ) as ps:

        runspace = server_pwsh.runspace
        open_runspace(server_pwsh)

        command = server_pwsh.next_payload()
        assert command.action == "Command"
        server_pwsh.command_ack(command.ps_guid)

        s_ps = psrpcore.ServerPipeline(runspace, command.ps_guid)
        create_pipe = server_pwsh.next_event()
        assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
        assert isinstance(create_pipe.pipeline, psrpcore.PowerShell)
        assert create_pipe.pipeline_id == s_ps.pipeline_id
        assert len(create_pipe.pipeline.commands) == 1
        assert create_pipe.pipeline.no_input is True

        cmd1 = create_pipe.pipeline.commands[0]
        assert cmd1.command_text == "Write-Progress"
        assert cmd1.is_script is False
        assert cmd1.end_of_statement is True
        assert cmd1.parameters == [
            ("Activity", "act"),
            ("Status", "status"),
            ("Id", 10),
            ("PercentComplete", 34),
            ("SecondsRemaining", 102),
            ("CurrentOperation", "currentOp"),
            ("ParentId", 9),
        ]

        s_ps.start()
        s_ps.write_progress(
            activity="act",
            activity_id=10,
            status_description="status",
            current_operation="currentOp",
            parent_activity_id=9,
            percent_complete=34,
            seconds_remaining=102,
        )
        s_ps.complete()
        server_pwsh.data()

        close = server_pwsh.next_payload()
        server_pwsh.close_ack(close.ps_guid)

        progress_record = ps.events.get()
        assert isinstance(progress_record, psrpcore.PipelineOutputEvent)
        assert isinstance(progress_record.data, psrpcore.types.ProgressRecord)
        assert progress_record.data.Activity == "act"
        assert progress_record.data.ActivityId == 10
        assert progress_record.data.CurrentOperation == "currentOp"
        assert progress_record.data.ParentActivityId == 9
        assert progress_record.data.PercentComplete == 34
        assert progress_record.data.RecordType == psrpcore.types.ProgressRecordType.Processing
        assert progress_record.data.SecondsRemaining == 102
        assert progress_record.data.StatusDescription == "status"

        server_pwsh.next_payload()
        server_pwsh.close_ack(None)


def test_pipe_input_data(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspacePool = [RunspaceFactory]::CreateRunspacePool(1, 1, $connInfo)
    $runspacePool.Open()
    try {
        $ps = [PowerShell]::Create()
        $ps.RunspacePool = $runspacePool
        [void]$ps.AddScript('$input')
        $ps.Invoke(@(1, '2'))
    }
    finally {
        $runspacePool.Dispose()
    }
    """

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
    ):

        runspace = server_pwsh.runspace
        open_runspace(server_pwsh)

        command = server_pwsh.next_payload()
        assert command.action == "Command"
        server_pwsh.command_ack(command.ps_guid)

        s_ps = psrpcore.ServerPipeline(runspace, command.ps_guid)
        create_pipe = server_pwsh.next_event()
        assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
        assert isinstance(create_pipe.pipeline, psrpcore.PowerShell)
        assert create_pipe.pipeline_id == s_ps.pipeline_id
        assert len(create_pipe.pipeline.commands) == 1
        assert create_pipe.pipeline.no_input is False

        cmd1 = create_pipe.pipeline.commands[0]
        assert cmd1.command_text == "$input"
        assert cmd1.is_script is True
        assert cmd1.end_of_statement is True
        assert cmd1.parameters == []

        server_pwsh.data_ack(s_ps.pipeline_id)
        s_ps.start()

        in_data = server_pwsh.next_event()
        assert isinstance(in_data, psrpcore.PipelineInputEvent)
        assert in_data.data == 1

        in_data = server_pwsh.next_event()
        assert isinstance(in_data, psrpcore.PipelineInputEvent)
        assert in_data.data == "2"

        in_end = server_pwsh.next_event()
        assert isinstance(in_end, psrpcore.EndOfPipelineInputEvent)

        server_pwsh.data_ack(s_ps.pipeline_id)
        s_ps.complete()
        server_pwsh.data()

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        server_pwsh.close_ack(close.ps_guid)

        server_pwsh.next_payload()
        server_pwsh.close_ack(None)


@pytest.mark.skipif(os.name == "nt", reason="Very rare issue when the client fails to connect - no idea why.")
def test_stop_pipe(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspacePool = [RunspaceFactory]::CreateRunspacePool(1, 1, $connInfo)
    $runspacePool.Open()
    try {
        $ps = [PowerShell]::Create()
        $ps.RunspacePool = $runspacePool

        $out = [System.Management.Automation.PSDataCollection[PSObject]]::new()
        $in = [System.Management.Automation.PSDataCollection[PSObject]]::new(1)
        $in.Add(1)
        $in.Complete()

        Register-ObjectEvent -InputObject $out -EventName DataAdded -SourceIdentifier 'PSRPCore.Wait'

        [void]$ps.AddScript("echo 'out'; sleep 60")
        $task = $ps.BeginInvoke($in, $out)

        # Wait until the first object has been received back before sending the stop signal
        $null = Wait-Event -SourceIdentifier 'PSRPCore.Wait'
        $ps.Stop()

        $ps.EndInvoke($task)
    }
    finally {
        $runspacePool.Dispose()
    }
    """

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
    ) as ps:

        runspace = server_pwsh.runspace
        open_runspace(server_pwsh)

        command = server_pwsh.next_payload()
        assert command.action == "Command"
        server_pwsh.command_ack(command.ps_guid)

        s_ps = psrpcore.ServerPipeline(runspace, command.ps_guid)

        create_pipe = server_pwsh.next_event()
        assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
        assert isinstance(create_pipe.pipeline, psrpcore.PowerShell)
        assert create_pipe.pipeline_id == s_ps.pipeline_id
        assert len(create_pipe.pipeline.commands) == 1
        server_pwsh.data_ack(s_ps.pipeline_id)

        cmd1 = create_pipe.pipeline.commands[0]
        assert cmd1.command_text == "echo 'out'; sleep 60"
        assert cmd1.is_script is True
        assert cmd1.end_of_statement is True
        assert cmd1.parameters == []

        s_ps.start()
        server_pwsh.data()

        # Get the input to know the pipeline has fully started on the client side
        input = server_pwsh.next_event()
        assert isinstance(input, psrpcore.PipelineInputEvent)
        assert input.pipeline_id == s_ps.pipeline_id
        assert input.data == 1

        eof = server_pwsh.next_event()
        assert isinstance(eof, psrpcore.EndOfPipelineInputEvent)
        server_pwsh.data_ack(s_ps.pipeline_id)

        # Send the output so the client knows it's fully started here
        s_ps.write_output("output")
        server_pwsh.data()

        # Now wait for the stop signal.
        signal = server_pwsh.next_payload()
        assert signal.action == "Signal"
        assert signal.ps_guid == s_ps.pipeline_id

        s_ps.stop()
        server_pwsh.data()

        server_pwsh.signal_ack(s_ps.pipeline_id)

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid == s_ps.pipeline_id
        server_pwsh.close_ack(close.ps_guid)

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid is None
        server_pwsh.close_ack(None)

        stop_record = ps.events.get()
        assert isinstance(stop_record, psrpcore.ErrorRecordEvent)
        assert (
            str(stop_record.record)
            == 'Exception calling "EndInvoke" with "1" argument(s): "The pipeline has been stopped."'
        )


def test_set_rp_count(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspacePool = [RunspaceFactory]::CreateRunspacePool(2, 5, $connInfo)
    $runspacePool.Open()
    try {
        $runspacePool.SetMaxRunspaces(1)  # $false
        $runspacePool.SetMaxRunspaces(5)  # $false

        $runspacePool.SetMaxRunspaces(4)  # $false - resp from server
        $runspacePool.SetMaxRunspaces(4)  # $true

        $runspacePool.SetMinRunspaces(6)  # $false - weird it sends it as 4 to the server
        $runspacePool.SetMinRunspaces(2)  # $false

        $runspacePool.SetMinRunspaces(4)  # $false - resp from server
        $runspacePool.SetMinRunspaces(4)  # $true

        $runspacePool.GetAvailableRunspaces()  # 3
    }
    finally {
        $runspacePool.Dispose()
    }
    """

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
    ) as ps:
        open_runspace(server_pwsh)

        assert server_pwsh.runspace.min_runspaces == 2
        assert server_pwsh.runspace.max_runspaces == 5

        res = ps.events.get()
        assert isinstance(res, psrpcore.PipelineOutputEvent)
        assert res.data is False

        res = ps.events.get()
        assert isinstance(res, psrpcore.PipelineOutputEvent)
        assert res.data is False

        set_max = server_pwsh.next_event()
        assert isinstance(set_max, psrpcore.SetMaxRunspacesEvent)
        assert set_max.count == 4
        server_pwsh.data_ack()

        server_pwsh.runspace.runspace_availability_response(set_max.ci, False)
        server_pwsh.data()
        res = ps.events.get()
        assert isinstance(res, psrpcore.PipelineOutputEvent)
        assert res.data is False
        assert server_pwsh.runspace.max_runspaces == 5

        set_max = server_pwsh.next_event()
        assert isinstance(set_max, psrpcore.SetMaxRunspacesEvent)
        assert set_max.count == 4
        server_pwsh.data_ack()

        server_pwsh.runspace.runspace_availability_response(set_max.ci, True)
        server_pwsh.data()
        res = ps.events.get()
        assert isinstance(res, psrpcore.PipelineOutputEvent)
        assert res.data is True
        assert server_pwsh.runspace.max_runspaces == 4

        res = ps.events.get()
        assert isinstance(res, psrpcore.PipelineOutputEvent)
        assert res.data is False

        res = ps.events.get()
        assert isinstance(res, psrpcore.PipelineOutputEvent)
        assert res.data is False

        set_min = server_pwsh.next_event()
        assert isinstance(set_min, psrpcore.SetMinRunspacesEvent)
        assert set_min.count == 4
        server_pwsh.data_ack()

        server_pwsh.runspace.runspace_availability_response(set_min.ci, False)
        server_pwsh.data()
        res = ps.events.get()
        assert isinstance(res, psrpcore.PipelineOutputEvent)
        assert res.data is False
        assert server_pwsh.runspace.min_runspaces == 2

        set_min = server_pwsh.next_event()
        assert isinstance(set_min, psrpcore.SetMinRunspacesEvent)
        assert set_min.count == 4
        server_pwsh.data_ack()

        server_pwsh.runspace.runspace_availability_response(set_min.ci, True)
        server_pwsh.data()
        res = ps.events.get()
        assert isinstance(res, psrpcore.PipelineOutputEvent)
        assert res.data is True
        assert server_pwsh.runspace.min_runspaces == 4

        get_avail = server_pwsh.next_event()
        assert isinstance(get_avail, psrpcore.GetAvailableRunspacesEvent)
        server_pwsh.data_ack()

        server_pwsh.runspace.runspace_availability_response(get_avail.ci, 3)
        server_pwsh.data()

        res = ps.events.get()
        assert isinstance(res, psrpcore.PipelineOutputEvent)
        assert res.data == 3

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        server_pwsh.close_ack()


@pytest.mark.skipif(os.name == "nt", reason="Very rare issue when the client fails to connect - no idea why.")
def test_reset_rp(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    $ErrorActionPreference = 'Stop'

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspace = [RunspaceFactory]::CreateRunspace($connInfo)
    $runspace.Open()
    try {
        $runspace.ResetRunspaceState()
        $runspace.ResetRunspaceState()
    }
    finally {
        $runspace.Dispose()
    }
    """

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
    ) as ps:
        open_runspace(server_pwsh)

        reset = server_pwsh.next_event()
        assert isinstance(reset, psrpcore.ResetRunspaceStateEvent)
        server_pwsh.runspace.runspace_availability_response(reset.ci, True)
        server_pwsh.data()
        server_pwsh.data_ack()

        reset = server_pwsh.next_event()
        assert isinstance(reset, psrpcore.ResetRunspaceStateEvent)
        server_pwsh.runspace.runspace_availability_response(reset.ci, False)
        server_pwsh.data()
        server_pwsh.data_ack()

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        server_pwsh.close_ack()

        state = ps.events.get()

        assert isinstance(state, psrpcore.PipelineStateEvent)
        assert isinstance(state.reason, psrpcore.types.ErrorRecord)
        assert state.state == psrpcore.types.RunspacePoolState.Broken
        assert '"ResetRunspaceState" is not valid' in str(state.reason)


def test_pipe_host_call(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspacePool = [RunspaceFactory]::CreateRunspacePool(1, 1, $connInfo, $Host)
    $runspacePool.Open()
    try {
        $ps = [PowerShell]::Create()
        $ps.RunspacePool = $runspacePool
        [void]$ps.AddScript(@'
$host.UI.WriteLine("line")
$host.UI.ReadLineAsSecureString()
'@)

        $ps.Invoke()
    }
    finally {
        $runspacePool.Dispose()
    }
    """

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
    ) as ps:
        open_runspace(server_pwsh)
        runspace = server_pwsh.runspace

        command = server_pwsh.next_payload()
        assert command.action == "Command"
        server_pwsh.command_ack(command.ps_guid)

        s_ps = psrpcore.ServerPipeline(runspace, command.ps_guid)
        create_pipe = server_pwsh.next_event()
        assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
        assert isinstance(create_pipe.pipeline, psrpcore.PowerShell)
        assert create_pipe.pipeline_id == s_ps.pipeline_id
        server_pwsh.data_ack(s_ps.pipeline_id)
        s_ps.start()
        server_pwsh.data()

        s_host = psrpcore.ServerHostRequestor(s_ps)
        ci = s_host.write_line("line")
        assert ci is None
        server_pwsh.data()

        ci = s_host.read_line_as_secure_string()
        assert ci == 1
        server_pwsh.data()

        call1 = ps.events.get()
        assert isinstance(call1, psrpcore.PipelineHostCallEvent)
        assert call1.ci == -100
        assert call1.method_identifier == psrpcore.types.HostMethodIdentifier.WriteLine2
        assert call1.method_parameters == ["line"]

        record = ps.events.get()
        assert isinstance(record, psrpcore.WarningRecordEvent)
        assert "is asking to read a line securely" in record.record.Message

        call2 = ps.events.get()
        assert isinstance(call2, psrpcore.PipelineHostCallEvent)
        assert call2.ci == -100
        assert call2.method_identifier == psrpcore.types.HostMethodIdentifier.WriteWarningLine
        assert call2.method_parameters == [record.record.Message]

        call3 = ps.events.get()
        assert isinstance(call3, psrpcore.PipelineHostCallEvent)
        assert call3.ci == 1
        assert call3.method_identifier == psrpcore.types.HostMethodIdentifier.ReadLineAsSecureString
        assert call3.method_parameters == []

        client_opened_pwsh.runspace.exchange_key()
        client_opened_pwsh.data()
        enc_key = ps.events.get()
        assert isinstance(enc_key, psrpcore.EncryptedSessionKeyEvent)

        c_host = psrpcore.ClientHostResponder(ps.pipeline)
        c_host.read_line_as_secure_string(call3.ci, psrpcore.types.PSSecureString("secret"))
        client_opened_pwsh.data()

        pub_key = server_pwsh.next_event()
        assert isinstance(pub_key, psrpcore.PublicKeyEvent)
        server_pwsh.data()

        resp = server_pwsh.next_event()
        assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
        assert resp.ci == 1
        assert resp.method_identifier == psrpcore.types.HostMethodIdentifier.ReadLineAsSecureString
        assert isinstance(resp.result, psrpcore.types.PSSecureString)
        assert resp.result.decrypt() == "secret"

        s_ps.complete()
        server_pwsh.data()

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid == s_ps.pipeline_id
        server_pwsh.close_ack(close.ps_guid)
        s_ps.close()
        server_pwsh.data()

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid is None
        server_pwsh.close_ack()


def test_rp_host_call(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspacePool = [RunspaceFactory]::CreateRunspacePool(1, 1, $connInfo, $Host)
    $runspacePool.Open()
    try {
        $ps = [PowerShell]::Create()
        $ps.RunspacePool = $runspacePool
        [void]$ps.AddScript(@'
$rs = [Runspace]::DefaultRunspace
$rsHost = $rs.GetType().GetProperty("Host", 60).GetValue($rs)
$rsHost.UI.WriteWarningLine("test")
'@)

        $ps.Invoke()
    }
    finally {
        $runspacePool.Dispose()
    }
    """

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
    ) as ps:
        open_runspace(server_pwsh)
        runspace = server_pwsh.runspace

        command = server_pwsh.next_payload()
        assert command.action == "Command"
        server_pwsh.command_ack(command.ps_guid)

        s_ps = psrpcore.ServerPipeline(runspace, command.ps_guid)
        create_pipe = server_pwsh.next_event()
        assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
        assert isinstance(create_pipe.pipeline, psrpcore.PowerShell)
        assert create_pipe.pipeline_id == s_ps.pipeline_id
        server_pwsh.data_ack(s_ps.pipeline_id)
        s_ps.start()
        server_pwsh.data()

        s_host = psrpcore.ServerHostRequestor(runspace)
        ci = s_host.write_warning_line("test")
        assert ci is None
        server_pwsh.data()

        # By the time it reaches our client (one controlling the pssession) it has turned into a warning record and
        # pipeline host call.
        record = ps.events.get()
        assert isinstance(record, psrpcore.WarningRecordEvent)
        assert record.record.Message == "test"
        call1 = ps.events.get()
        assert isinstance(call1, psrpcore.PipelineHostCallEvent)
        assert call1.ci == -100
        assert call1.method_identifier == psrpcore.types.HostMethodIdentifier.WriteWarningLine
        assert call1.method_parameters == ["test"]

        s_ps.complete()
        server_pwsh.data()

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid == s_ps.pipeline_id
        server_pwsh.close_ack(close.ps_guid)
        s_ps.close()
        server_pwsh.data()

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid is None
        server_pwsh.close_ack()


def test_cmd_meta(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    [System.Management.Automation.Platform]::SelectProductNameForDirectory('USER_MODULES')

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspace = [RunspaceFactory]::CreateRunspace($connInfo)
    $runspace.Open()
    try {
        $cstr = [Management.Automation.Runspaces.PSSession].GetConstructor(
            'NonPublic, Instance', $null, [type[]]$runspace.GetType(), $null)
        $session = $cstr.Invoke(@($runspace))

        $exportParams = @{
            Session = $session
            OutputModule = 'psrpcore-testing'
            CommandName = 'Get-*Item'
            CommandType = 'Cmdlet'
            ArgumentList = 'env:'
            Force = $true
        }
        Export-PSSession @exportParams
    }
    finally {
        $runspace.Dispose()
    }
    """

    module_path = None
    try:
        with BackgroundPipeline(
            client_opened_pwsh,
            cmd,
            Name=server_pwsh.pipe_name,
        ) as ps:
            module_path = ps.events.get().data

            open_runspace(server_pwsh)
            runspace = server_pwsh.runspace

            command = server_pwsh.next_payload()
            assert command.action == "Command"
            server_pwsh.command_ack(command.ps_guid)

            s_ps = psrpcore.ServerPipeline(runspace, command.ps_guid)
            cmd_meta = server_pwsh.next_event()
            assert isinstance(cmd_meta, psrpcore.GetCommandMetadataEvent)
            assert isinstance(cmd_meta.pipeline, psrpcore.GetMetadata)
            assert cmd_meta.pipeline_id == s_ps.pipeline_id
            assert cmd_meta.pipeline.name == ["Get-*Item"]
            assert cmd_meta.pipeline.command_type == psrpcore.types.CommandTypes.Cmdlet
            assert cmd_meta.pipeline.namespace == []
            assert cmd_meta.pipeline.arguments == ["env:"]

            server_pwsh.data_ack(s_ps.pipeline_id)
            s_ps.start()
            server_pwsh.data()

            s_ps.write_output(
                psrpcore.types.PSCustomObject(
                    PSTypeName="Selected.Microsoft.PowerShell.Commands.GenericMeasureInfo",
                    Count=2,
                )
            )
            server_pwsh.data()

            s_ps.write_output(
                psrpcore.types.PSCustomObject(
                    PSTypeName="Selected.System.Management.Automation.CmdletInfo",
                    Name="Get-ChildItem",
                    Namespace="Microsoft.PowerShell.Management",
                    HelpUri="https://go.microsoft.com/fwlink/?LinkID=2096492",
                    CommandType=psrpcore.types.CommandTypes.Cmdlet,
                    ResolvedCommandName=None,
                    OutputType=["System.IO.FileInfo", "System.IO.DirectoryInfo"],
                    Parameters={},
                )
            )
            server_pwsh.data()

            s_ps.write_output(
                psrpcore.types.PSCustomObject(
                    PSTypeName="Selected.System.Management.Automation.CmdletInfo",
                    Name="Get-Item",
                    Namespace="Microsoft.PowerShell.Management",
                    HelpUri="https://go.microsoft.com/fwlink/?LinkID=2096492",
                    CommandType=psrpcore.types.CommandTypes.Cmdlet,
                    ResolvedCommandName=None,
                    OutputType=["System.IO.FileInfo", "System.Boolean", "System.String"],
                    Parameters={},
                )
            )
            server_pwsh.data()

            s_ps.complete()
            server_pwsh.data()

            close = server_pwsh.next_payload()
            assert close.action == "Close"
            assert close.ps_guid == s_ps.pipeline_id
            server_pwsh.close_ack(close.ps_guid)
            s_ps.close()
            server_pwsh.data()

            close = server_pwsh.next_payload()
            assert close.action == "Close"
            assert close.ps_guid is None
            server_pwsh.close_ack()

    finally:
        if not module_path:
            return

        exported_path = os.path.join(module_path, "psrpcore-testing")
        if os.path.exists(exported_path):
            shutil.rmtree(exported_path)


def test_user_event(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspace = [RunspaceFactory]::CreateRunspace($Host, $connInfo)
    $runspace.Open()
    try {
        $eventParams = @{
            InputObject = $runspace.Events.ReceivedEvents
            EventName = "PSEventReceived"
            SourceIdentifier = "PSRPCore.UserEvent"
        }
        $null = Register-ObjectEvent @eventParams

        $ps = [PowerShell]::Create()
        $ps.Runspace = $runspace
        [void]$ps.AddScript(@'
$null = $Host.Runspace.Events.SubscribeEvent(
    $null,
    "PSRPCoreEvent",
    "PSRPCoreEvent",
    $null,
    $null,
    $true,
    $true)
$null = $Host.Runspace.Events.GenerateEvent(
    "PSRPCoreEvent",
    "sender",
    @("my", "args"),
    "extra data")
'@)
        $ps.Invoke()

        Wait-Event -SourceIdentifier $eventParams.SourceIdentifier | Select *
    }
    finally {
        $runspace.Dispose()
    }
    """

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
    ) as ps:
        open_runspace(server_pwsh)
        runspace = server_pwsh.runspace

        command = server_pwsh.next_payload()
        assert command.action == "Command"
        server_pwsh.command_ack(command.ps_guid)

        s_ps = psrpcore.ServerPipeline(runspace, command.ps_guid)
        create_pipe = server_pwsh.next_event()
        assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
        assert isinstance(create_pipe.pipeline, psrpcore.PowerShell)
        assert create_pipe.pipeline_id == s_ps.pipeline_id

        server_pwsh.data_ack(s_ps.pipeline_id)
        s_ps.start()
        server_pwsh.data()

        runspace.send_event(
            event_identifier=1,
            source_identifier="PSRPCoreEvent",
            sender="sender",
            source_args=["my 1", "args 2"],
            message_data="extra data",
        )
        server_pwsh.data()

        s_ps.complete()
        server_pwsh.data()

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid == s_ps.pipeline_id
        server_pwsh.close_ack(close.ps_guid)

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid is None
        server_pwsh.close_ack()

        event = ps.events.get()
        assert isinstance(event, psrpcore.PipelineOutputEvent)
        assert event.data.EventIdentifier == 1
        assert event.data.SourceIdentifier == "PSRPCore.UserEvent"

        source_event = event.data.SourceEventArgs
        assert source_event.EventIdentifier == 1
        assert source_event.MessageData == "extra data"
        assert source_event.Sender == "sender"
        assert source_event.SourceArgs == ["my 1", "args 2"]
        assert source_event.SourceEventArgs is None
        assert source_event.SourceIdentifier == "PSRPCoreEvent"


def test_set_buffer_call(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspace = [RunspaceFactory]::CreateRunspace($Host, $connInfo)
    $runspace.Open()
    try {
        $ps = [PowerShell]::Create()
        $ps.Runspace = $runspace
        [void]$ps.AddScript(@'
$coordinates = [System.Management.Automation.Host.Coordinates]::new(0, 1)
$cell = [System.Management.Automation.Host.BufferCell]::new('a', 'White', 'Gray', 'Complete')
$cells = $Host.UI.RawUI.NewBufferCellArray(3, 4, $cell)
$host.UI.RawUI.SetBufferContents($coordinates, $cells)
'@)
        $ps.Invoke()
    }
    finally {
        $runspace.Dispose()
    }
    """

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
    ) as ps:
        open_runspace(server_pwsh)
        runspace = server_pwsh.runspace

        command = server_pwsh.next_payload()
        assert command.action == "Command"
        server_pwsh.command_ack(command.ps_guid)

        s_ps = psrpcore.ServerPipeline(runspace, command.ps_guid)
        create_pipe = server_pwsh.next_event()
        assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
        assert isinstance(create_pipe.pipeline, psrpcore.PowerShell)
        assert create_pipe.pipeline_id == s_ps.pipeline_id
        server_pwsh.data_ack(s_ps.pipeline_id)

        s_ps.start()
        server_pwsh.data()

        s_host = psrpcore.ServerHostRequestor(s_ps)
        cell = psrpcore.types.BufferCell(
            "a",
            psrpcore.types.ConsoleColor.White,
            psrpcore.types.ConsoleColor.Black,
            psrpcore.types.BufferCellType.Complete,
        )
        contents = [
            [cell, cell, cell],
            [cell, cell, cell],
            [cell, cell, cell],
            [cell, cell, cell],
        ]
        ci = s_host.set_buffer_contents(0, 1, contents)
        # ci = s_host.set_buffer_cells(0, 1, 4, 5, "a")
        assert ci is None
        server_pwsh.data()

        s_ps.complete()
        server_pwsh.data()

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid == s_ps.pipeline_id
        server_pwsh.close_ack(close.ps_guid)

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid is None
        server_pwsh.close_ack()

        host_call = ps.events.get()
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
                assert cell.BackgroundColor == psrpcore.types.ConsoleColor.Black
                assert isinstance(cell.BackgroundColor, psrpcore.types.ConsoleColor)
                assert cell.BufferCellType == psrpcore.types.BufferCellType.Complete


def test_pipeline_extra_cmds(server_pwsh: ServerTransport, client_opened_pwsh: ClientTransport):
    cmd = """[CmdletBinding()]
    param ([String]$Name)

    $connInfo = [System.Management.Automation.Runspaces.NamedPipeConnectionInfo]::new($Name)
    $runspace = [RunspaceFactory]::CreateRunspace($Host, $connInfo)
    $runspace.Open()
    try {
        $ps = [PowerShell]::Create()
        $ps.Runspace = $runspace

        [void]$ps.AddCommand("Set-Variable").AddParameters([Ordered]@{
            Name = "string"
            Value = "foo"
        }).AddStatement()

        [void]$ps.AddCommand("Get-Variable").AddParameter("Name", "string")
        [void]$ps.AddCommand("Select-Object").AddParameter("Property", @("Name", "Value"))
        [void]$ps.AddStatement()

        [void]$ps.AddCommand("Get-Variable").AddArgument("string").AddParameter("ValueOnly", $true)
        [void]$ps.AddCommand("Select-Object")
        [void]$ps.AddStatement()

        [void]$ps.AddScript('[PSCustomObject]@{ Value = $string }')
        [void]$ps.AddScript('process { $_ | Select-Object -Property @{N="Test"; E={ $_.Value }} }')
        [void]$ps.AddStatement()

        $ps.Invoke()
    }
    finally {
        $runspace.Dispose()
    }
    """

    with BackgroundPipeline(
        client_opened_pwsh,
        cmd,
        Name=server_pwsh.pipe_name,
    ) as ps:
        open_runspace(server_pwsh)
        runspace = server_pwsh.runspace

        command = server_pwsh.next_payload()
        assert command.action == "Command"
        server_pwsh.command_ack(command.ps_guid)

        s_ps = psrpcore.ServerPipeline(runspace, command.ps_guid)
        create_pipe = server_pwsh.next_event()
        assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
        assert isinstance(create_pipe.pipeline, psrpcore.PowerShell)
        assert create_pipe.pipeline_id == s_ps.pipeline_id
        assert len(s_ps.metadata.commands) == 7
        assert s_ps.metadata.commands[0].command_text == "Set-Variable"
        assert s_ps.metadata.commands[0].parameters == [("Name", "string"), ("Value", "foo")]
        assert s_ps.metadata.commands[0].end_of_statement
        assert s_ps.metadata.commands[0].is_script is False

        assert s_ps.metadata.commands[1].command_text == "Get-Variable"
        assert s_ps.metadata.commands[1].parameters == [("Name", "string")]
        assert s_ps.metadata.commands[1].end_of_statement is False
        assert s_ps.metadata.commands[1].is_script is False

        assert s_ps.metadata.commands[2].command_text == "Select-Object"
        assert s_ps.metadata.commands[2].parameters == [("Property", ["Name", "Value"])]
        assert s_ps.metadata.commands[2].end_of_statement
        assert s_ps.metadata.commands[2].is_script is False

        assert s_ps.metadata.commands[3].command_text == "Get-Variable"
        assert s_ps.metadata.commands[3].parameters == [(None, "string"), ("ValueOnly", True)]
        assert s_ps.metadata.commands[3].end_of_statement is False
        assert s_ps.metadata.commands[3].is_script is False

        assert s_ps.metadata.commands[4].command_text == "Select-Object"
        assert s_ps.metadata.commands[4].parameters == []
        assert s_ps.metadata.commands[4].end_of_statement
        assert s_ps.metadata.commands[4].is_script is False

        assert s_ps.metadata.commands[5].command_text == "[PSCustomObject]@{ Value = $string }"
        assert s_ps.metadata.commands[5].parameters == []
        assert s_ps.metadata.commands[5].end_of_statement is False
        assert s_ps.metadata.commands[5].is_script

        assert (
            s_ps.metadata.commands[6].command_text
            == 'process { $_ | Select-Object -Property @{N="Test"; E={ $_.Value }} }'
        )
        assert s_ps.metadata.commands[6].parameters == []
        assert s_ps.metadata.commands[6].end_of_statement is True
        assert s_ps.metadata.commands[6].is_script

        server_pwsh.data_ack(s_ps.pipeline_id)
        s_ps.start()
        server_pwsh.data()

        s_ps.complete()
        server_pwsh.data()

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid == s_ps.pipeline_id
        server_pwsh.close_ack(close.ps_guid)

        close = server_pwsh.next_payload()
        assert close.action == "Close"
        assert close.ps_guid is None
        server_pwsh.close_ack()
