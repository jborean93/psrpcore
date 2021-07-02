# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import re
import threading

import pytest

import psrpcore
from psrpcore.types import (
    ApartmentState,
    ConsoleColor,
    Coordinates,
    ErrorCategory,
    ErrorCategoryInfo,
    ErrorRecord,
    HostDefaultData,
    HostInfo,
    HostMethodIdentifier,
    InformationalRecord,
    NETException,
    PipelineResultTypes,
    ProgressRecordType,
    PSInt,
    PSInvocationState,
    PSSecureString,
    PSString,
    RemoteStreamOptions,
    Size,
)
from psrpcore.types._psrp import InformationRecord

from .conftest import get_runspace_pair


def test_create_pipeline():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientPowerShell(client)
    assert c_pipeline.state == PSInvocationState.NotStarted

    with pytest.raises(ValueError, match="A command is required to invoke a PowerShell pipeline"):
        c_pipeline.invoke()

    c_pipeline.add_script("testing")
    c_pipeline.invoke()
    assert c_pipeline.state == PSInvocationState.Running

    c_command = client.data_to_send()
    server.receive_data(c_command)
    create_pipeline = server.next_event()
    s_pipeline = create_pipeline.pipeline
    assert isinstance(create_pipeline, psrpcore.CreatePipelineEvent)
    assert isinstance(s_pipeline, psrpcore.ServerPowerShell)
    assert s_pipeline.add_to_history is False
    assert s_pipeline.apartment_state == ApartmentState.Unknown
    assert len(s_pipeline.commands) == 1
    assert s_pipeline.commands[0].command_text == "testing"
    assert s_pipeline.commands[0].end_of_statement is True
    assert s_pipeline.commands[0].is_script is True
    assert s_pipeline.commands[0].parameters == []
    assert s_pipeline.commands[0].use_local_scope is None
    assert s_pipeline.history is None
    assert isinstance(s_pipeline.host, HostInfo)
    assert s_pipeline.host.host_default_data is None
    assert s_pipeline.host.is_host_null is True
    assert s_pipeline.host.is_host_raw_ui_null is True
    assert s_pipeline.host.is_host_ui_null is True
    assert s_pipeline.host.use_runspace_host is True
    assert s_pipeline.is_nested is False
    assert s_pipeline.no_input is True
    assert s_pipeline.pipeline_id == c_pipeline.pipeline_id
    assert s_pipeline.redirect_shell_error_to_out is True
    assert s_pipeline.remote_stream_options == RemoteStreamOptions.none
    assert s_pipeline.runspace_pool == server
    assert s_pipeline.state == PSInvocationState.NotStarted
    assert len(server.pipeline_table) == 1
    assert server.pipeline_table[s_pipeline.pipeline_id] == s_pipeline

    s_pipeline.start()
    s_pipeline.write_output("output msg")
    s_pipeline.close()
    client.receive_data(server.data_to_send())
    out = client.next_event()
    assert server.pipeline_table == {}
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert out.ps_object == "output msg"

    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == PSInvocationState.Completed
    assert c_pipeline.state == PSInvocationState.Completed
    assert client.pipeline_table == {}


def test_create_pipeline_host_data():
    client, server = get_runspace_pair()

    c_host_data = HostDefaultData(
        foreground_color=ConsoleColor.Red,
        background_color=ConsoleColor.White,
        cursor_position=Coordinates(1, 2),
        window_position=Coordinates(3, 4),
        cursor_size=5,
        buffer_size=Size(6, 7),
        window_size=Size(8, 9),
        max_window_size=Size(10, 11),
        max_physical_window_size=Size(12, 13),
        window_title="Test Title",
    )
    c_host = HostInfo(
        use_runspace_host=False,
        is_host_null=False,
        is_host_ui_null=False,
        is_host_raw_ui_null=False,
        host_default_data=c_host_data,
    )

    c_pipeline = psrpcore.ClientPowerShell(client, host=c_host)
    c_pipeline.add_script("testing")
    c_pipeline.invoke()

    server.receive_data(client.data_to_send())
    create_pipeline = server.next_event()
    s_pipeline = create_pipeline.pipeline
    s_host = s_pipeline.host

    assert isinstance(s_host, HostInfo)
    assert s_host.is_host_null is False
    assert s_host.is_host_ui_null is False
    assert s_host.is_host_raw_ui_null is False
    assert s_host.use_runspace_host is False
    assert isinstance(s_host.host_default_data, HostDefaultData)
    assert s_host.host_default_data.foreground_color == ConsoleColor.Red
    assert s_host.host_default_data.background_color == ConsoleColor.White
    assert s_host.host_default_data.cursor_position.X == 1
    assert s_host.host_default_data.cursor_position.Y == 2
    assert s_host.host_default_data.window_position.X == 3
    assert s_host.host_default_data.window_position.Y == 4
    assert s_host.host_default_data.cursor_size == 5
    assert s_host.host_default_data.buffer_size.Width == 6
    assert s_host.host_default_data.buffer_size.Height == 7
    assert s_host.host_default_data.window_size.Width == 8
    assert s_host.host_default_data.window_size.Height == 9
    assert s_host.host_default_data.max_window_size.Width == 10
    assert s_host.host_default_data.max_window_size.Height == 11
    assert s_host.host_default_data.max_physical_window_size.Width == 12
    assert s_host.host_default_data.max_physical_window_size.Height == 13
    assert s_host.host_default_data.window_title == "Test Title"


def test_pipeline_multiple_commands():
    client, server = get_runspace_pair()
    c_pipeline = psrpcore.ClientPowerShell(client)

    c_pipeline.add_command("Get-ChildItem")
    c_pipeline.add_command("Select-Object", use_local_scope=True)
    complex_command = psrpcore.Command("Format-List", use_local_scope=False)
    complex_command.redirect_error(PipelineResultTypes.Output)
    c_pipeline.add_command(complex_command)

    with pytest.raises(TypeError, match="Cannot set use_local_scope with Command"):
        c_pipeline.add_command(complex_command, use_local_scope=False)

    c_pipeline.invoke()

    server.receive_data(client.data_to_send())
    create_pipe = server.next_event()
    s_pipeline = create_pipe.pipeline

    assert len(s_pipeline.commands) == 3
    assert str(s_pipeline.commands[0]) == "Get-ChildItem"
    assert repr(s_pipeline.commands[0]) == "Command(name='Get-ChildItem', is_script=False, use_local_scope=None)"
    assert s_pipeline.commands[0].command_text == "Get-ChildItem"
    assert s_pipeline.commands[0].end_of_statement is False
    assert s_pipeline.commands[0].use_local_scope is None
    assert s_pipeline.commands[0].merge_error == PipelineResultTypes.none
    assert s_pipeline.commands[0].merge_my == PipelineResultTypes.none
    assert s_pipeline.commands[0].merge_to == PipelineResultTypes.none
    assert str(s_pipeline.commands[1]) == "Select-Object"
    assert repr(s_pipeline.commands[1]) == "Command(name='Select-Object', is_script=False, use_local_scope=True)"
    assert s_pipeline.commands[1].command_text == "Select-Object"
    assert s_pipeline.commands[1].end_of_statement is False
    assert s_pipeline.commands[1].use_local_scope is True
    assert s_pipeline.commands[1].merge_error == PipelineResultTypes.none
    assert s_pipeline.commands[1].merge_my == PipelineResultTypes.none
    assert s_pipeline.commands[1].merge_to == PipelineResultTypes.none
    assert str(s_pipeline.commands[2]) == "Format-List"
    assert repr(s_pipeline.commands[2]) == "Command(name='Format-List', is_script=False, use_local_scope=False)"
    assert s_pipeline.commands[2].command_text == "Format-List"
    assert s_pipeline.commands[2].end_of_statement is True
    assert s_pipeline.commands[2].use_local_scope is False
    assert s_pipeline.commands[2].merge_error == PipelineResultTypes.Output
    assert s_pipeline.commands[2].merge_my == PipelineResultTypes.Error
    assert s_pipeline.commands[2].merge_to == PipelineResultTypes.Output


def test_pipeline_multiple_statements():
    client, server = get_runspace_pair()
    c_pipeline = psrpcore.ClientPowerShell(client)

    c_pipeline.add_statement()  # Should do nothing, not fail
    c_pipeline.add_command("Get-ChildItem")
    c_pipeline.add_command("Format-List")
    c_pipeline.add_statement()
    c_pipeline.add_script("Test-Path", use_local_scope=True)
    c_pipeline.add_statement()
    c_pipeline.add_command("Get-Service")
    c_pipeline.add_command("Format-Table")
    c_pipeline.invoke()
    server.receive_data(client.data_to_send())
    create_pipe = server.next_event()
    s_pipeline = create_pipe.pipeline

    assert len(s_pipeline.commands) == 5
    assert s_pipeline.commands[0].command_text == "Get-ChildItem"
    assert s_pipeline.commands[0].use_local_scope is None
    assert s_pipeline.commands[0].is_script is False
    assert s_pipeline.commands[0].end_of_statement is False
    assert s_pipeline.commands[1].command_text == "Format-List"
    assert s_pipeline.commands[1].use_local_scope is None
    assert s_pipeline.commands[1].is_script is False
    assert s_pipeline.commands[1].end_of_statement is True
    assert s_pipeline.commands[2].command_text == "Test-Path"
    assert s_pipeline.commands[2].use_local_scope is True
    assert s_pipeline.commands[2].is_script is True
    assert s_pipeline.commands[2].end_of_statement is True
    assert s_pipeline.commands[3].command_text == "Get-Service"
    assert s_pipeline.commands[3].use_local_scope is None
    assert s_pipeline.commands[3].is_script is False
    assert s_pipeline.commands[3].end_of_statement is False
    assert s_pipeline.commands[4].command_text == "Format-Table"
    assert s_pipeline.commands[4].use_local_scope is None
    assert s_pipeline.commands[4].is_script is False
    assert s_pipeline.commands[4].end_of_statement is True


def test_pipeline_parameters():
    client, server = get_runspace_pair()
    c_pipeline = psrpcore.ClientPowerShell(client)

    expected = re.escape(
        "A command is required to add a parameter/argument. A command must be added to the "
        "PowerShell instance first."
    )
    with pytest.raises(ValueError, match=expected):
        c_pipeline.add_argument("argument")

    with pytest.raises(ValueError, match=expected):
        c_pipeline.add_parameter("name", "value")

    with pytest.raises(ValueError, match=expected):
        c_pipeline.add_parameters({"name": "value"})

    c_pipeline.add_command("Get-ChildItem")
    c_pipeline.add_argument("/tmp")
    c_pipeline.add_argument(True)
    c_pipeline.add_statement()

    c_pipeline.add_command("Get-ChildItem")
    c_pipeline.add_parameter("Path", "/tmp")
    c_pipeline.add_parameter("Force")
    c_pipeline.add_statement()

    c_pipeline.add_command("Get-ChildItem")
    c_pipeline.add_parameters({"Path": "/tmp", "Force": True})

    c_pipeline.invoke()
    server.receive_data(client.data_to_send())
    create_pipe = server.next_event()
    s_pipeline = create_pipe.pipeline

    assert s_pipeline.commands[0].parameters == [(None, "/tmp"), (None, True)]
    assert s_pipeline.commands[1].parameters == [("Path", "/tmp"), ("Force", None)]
    assert s_pipeline.commands[2].parameters == [("Path", "/tmp"), ("Force", True)]


def test_pipeline_redirection():
    client, server = get_runspace_pair()
    c_pipeline = psrpcore.ClientPowerShell(client)

    command = psrpcore.Command("My-Cmdlet")

    expected = re.escape("Invalid redirection stream, must be none, Output, or Null")
    with pytest.raises(ValueError, match=expected):
        command.redirect_error(PipelineResultTypes.Error)

    with pytest.raises(ValueError, match=expected):
        command.redirect_debug(PipelineResultTypes.Error)

    with pytest.raises(ValueError, match=expected):
        command.redirect_warning(PipelineResultTypes.Error)

    with pytest.raises(ValueError, match=expected):
        command.redirect_verbose(PipelineResultTypes.Error)

    with pytest.raises(ValueError, match=expected):
        command.redirect_information(PipelineResultTypes.Error)

    with pytest.raises(ValueError, match=expected):
        command.redirect_all(PipelineResultTypes.Error)

    command.redirect_error(PipelineResultTypes.Output)
    command.merge_unclaimed = True
    c_pipeline.add_command(command)

    command = psrpcore.Command("My-Cmdlet2")
    command.redirect_all(PipelineResultTypes.Null)
    c_pipeline.add_command(command)

    command = psrpcore.Command("My-Cmdlet3")
    command.redirect_debug(PipelineResultTypes.Output)
    c_pipeline.add_command(command)

    command = psrpcore.Command("My-Cmdlet4")
    command.redirect_warning(PipelineResultTypes.Output)
    c_pipeline.add_command(command)

    command = psrpcore.Command("My-Cmdlet5")
    command.redirect_verbose(PipelineResultTypes.Output)
    c_pipeline.add_command(command)

    command = psrpcore.Command("My-Cmdlet6")
    command.redirect_information(PipelineResultTypes.Output)
    c_pipeline.add_command(command)

    command = psrpcore.Command("My-Cmdlet7")
    command.redirect_all(PipelineResultTypes.Output)
    command.redirect_all(PipelineResultTypes.none)  # Resets it back to normal
    c_pipeline.add_command(command)

    c_pipeline.invoke()
    server.receive_data(client.data_to_send())
    create_pipe = server.next_event()
    s_pipeline = create_pipe.pipeline

    assert s_pipeline.commands[0].command_text == "My-Cmdlet"
    assert s_pipeline.commands[0].merge_debug == PipelineResultTypes.none
    assert s_pipeline.commands[0].merge_error == PipelineResultTypes.Output
    assert s_pipeline.commands[0].merge_information == PipelineResultTypes.none
    assert s_pipeline.commands[0].merge_my == PipelineResultTypes.Error
    assert s_pipeline.commands[0].merge_to == PipelineResultTypes.Output
    assert s_pipeline.commands[0].merge_unclaimed is True
    assert s_pipeline.commands[0].merge_verbose == PipelineResultTypes.none
    assert s_pipeline.commands[0].merge_warning == PipelineResultTypes.none

    assert s_pipeline.commands[1].command_text == "My-Cmdlet2"
    assert s_pipeline.commands[1].merge_debug == PipelineResultTypes.Null
    assert s_pipeline.commands[1].merge_error == PipelineResultTypes.Null
    assert s_pipeline.commands[1].merge_information == PipelineResultTypes.Null
    assert s_pipeline.commands[1].merge_my == PipelineResultTypes.none
    assert s_pipeline.commands[1].merge_to == PipelineResultTypes.none
    assert s_pipeline.commands[1].merge_unclaimed is False
    assert s_pipeline.commands[1].merge_verbose == PipelineResultTypes.Null
    assert s_pipeline.commands[1].merge_warning == PipelineResultTypes.Null

    assert s_pipeline.commands[2].command_text == "My-Cmdlet3"
    assert s_pipeline.commands[2].merge_debug == PipelineResultTypes.Output
    assert s_pipeline.commands[2].merge_error == PipelineResultTypes.none
    assert s_pipeline.commands[2].merge_information == PipelineResultTypes.none
    assert s_pipeline.commands[2].merge_my == PipelineResultTypes.none
    assert s_pipeline.commands[2].merge_to == PipelineResultTypes.none
    assert s_pipeline.commands[2].merge_unclaimed is False
    assert s_pipeline.commands[2].merge_verbose == PipelineResultTypes.none
    assert s_pipeline.commands[2].merge_warning == PipelineResultTypes.none

    assert s_pipeline.commands[3].command_text == "My-Cmdlet4"
    assert s_pipeline.commands[3].merge_debug == PipelineResultTypes.none
    assert s_pipeline.commands[3].merge_error == PipelineResultTypes.none
    assert s_pipeline.commands[3].merge_information == PipelineResultTypes.none
    assert s_pipeline.commands[3].merge_my == PipelineResultTypes.none
    assert s_pipeline.commands[3].merge_to == PipelineResultTypes.none
    assert s_pipeline.commands[3].merge_unclaimed is False
    assert s_pipeline.commands[3].merge_verbose == PipelineResultTypes.none
    assert s_pipeline.commands[3].merge_warning == PipelineResultTypes.Output

    assert s_pipeline.commands[4].command_text == "My-Cmdlet5"
    assert s_pipeline.commands[4].merge_debug == PipelineResultTypes.none
    assert s_pipeline.commands[4].merge_error == PipelineResultTypes.none
    assert s_pipeline.commands[4].merge_information == PipelineResultTypes.none
    assert s_pipeline.commands[4].merge_my == PipelineResultTypes.none
    assert s_pipeline.commands[4].merge_to == PipelineResultTypes.none
    assert s_pipeline.commands[4].merge_unclaimed is False
    assert s_pipeline.commands[4].merge_verbose == PipelineResultTypes.Output
    assert s_pipeline.commands[4].merge_warning == PipelineResultTypes.none

    assert s_pipeline.commands[5].command_text == "My-Cmdlet6"
    assert s_pipeline.commands[5].merge_debug == PipelineResultTypes.none
    assert s_pipeline.commands[5].merge_error == PipelineResultTypes.none
    assert s_pipeline.commands[5].merge_information == PipelineResultTypes.Output
    assert s_pipeline.commands[5].merge_my == PipelineResultTypes.none
    assert s_pipeline.commands[5].merge_to == PipelineResultTypes.none
    assert s_pipeline.commands[5].merge_unclaimed is False
    assert s_pipeline.commands[5].merge_verbose == PipelineResultTypes.none
    assert s_pipeline.commands[5].merge_warning == PipelineResultTypes.none

    assert s_pipeline.commands[6].command_text == "My-Cmdlet7"
    assert s_pipeline.commands[6].merge_debug == PipelineResultTypes.none
    assert s_pipeline.commands[6].merge_error == PipelineResultTypes.none
    assert s_pipeline.commands[6].merge_information == PipelineResultTypes.none
    assert s_pipeline.commands[6].merge_my == PipelineResultTypes.none
    assert s_pipeline.commands[6].merge_to == PipelineResultTypes.none
    assert s_pipeline.commands[6].merge_unclaimed is False
    assert s_pipeline.commands[6].merge_verbose == PipelineResultTypes.none
    assert s_pipeline.commands[6].merge_warning == PipelineResultTypes.none


def test_pipeline_input_output():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientPowerShell(client, no_input=False)
    assert c_pipeline.state == PSInvocationState.NotStarted

    c_pipeline.add_script("Get-Service")
    c_pipeline.invoke()
    assert c_pipeline.state == PSInvocationState.Running

    c_command = client.data_to_send()
    server.receive_data(c_command)
    create_pipeline = server.next_event()
    s_pipeline = create_pipeline.pipeline
    assert isinstance(create_pipeline, psrpcore.CreatePipelineEvent)
    assert isinstance(s_pipeline, psrpcore.ServerPowerShell)
    assert len(s_pipeline.commands) == 1
    assert s_pipeline.commands[0].command_text == "Get-Service"
    assert s_pipeline.no_input is False
    assert s_pipeline.runspace_pool == server
    assert s_pipeline.state == PSInvocationState.NotStarted
    assert len(server.pipeline_table) == 1
    assert server.pipeline_table[s_pipeline.pipeline_id] == s_pipeline

    s_pipeline.start()
    c_pipeline.send("input 1")
    c_pipeline.send("input 2")
    c_pipeline.send(3)
    server.receive_data(client.data_to_send())

    input1 = server.next_event()
    input2 = server.next_event()
    input3 = server.next_event()

    assert server.next_event() is None
    assert isinstance(input1, psrpcore.PipelineInputEvent)
    assert isinstance(input1.ps_object, PSString)
    assert input1.ps_object == "input 1"
    assert isinstance(input2, psrpcore.PipelineInputEvent)
    assert isinstance(input2.ps_object, PSString)
    assert input2.ps_object == "input 2"
    assert isinstance(input3, psrpcore.PipelineInputEvent)
    assert isinstance(input3.ps_object, PSInt)
    assert input3.ps_object == 3

    c_pipeline.send_end()
    server.receive_data(client.data_to_send())
    end_of_input = server.next_event()
    assert isinstance(end_of_input, psrpcore.EndOfPipelineInputEvent)

    s_pipeline.write_output("output")
    s_pipeline.write_debug("debug")
    s_pipeline.write_error(NETException("error"))
    s_pipeline.write_verbose("verbose")
    s_pipeline.write_warning("warning")
    s_pipeline.write_information("information", "source")
    s_pipeline.write_progress("activity", 1, "description")
    s_pipeline.close()
    client.receive_data(server.data_to_send())

    output_event = client.next_event()
    assert isinstance(output_event, psrpcore.PipelineOutputEvent)
    assert isinstance(output_event.ps_object, PSString)
    assert output_event.ps_object == "output"

    debug_event = client.next_event()
    assert isinstance(debug_event, psrpcore.DebugRecordEvent)
    assert isinstance(debug_event.ps_object, InformationalRecord)
    assert debug_event.ps_object.InvocationInfo is None
    assert debug_event.ps_object.Message == "debug"
    assert debug_event.ps_object.PipelineIterationInfo is None

    error_event = client.next_event()
    assert isinstance(error_event, psrpcore.ErrorRecordEvent)
    assert isinstance(error_event.ps_object, ErrorRecord)
    assert str(error_event.ps_object) == "error"
    assert isinstance(error_event.ps_object.Exception, NETException)
    assert error_event.ps_object.Exception.Message == "error"
    assert isinstance(error_event.ps_object.CategoryInfo, ErrorCategoryInfo)
    assert str(error_event.ps_object.CategoryInfo), "NotSpecified (:) [], "
    assert error_event.ps_object.CategoryInfo.Category == ErrorCategory.NotSpecified
    assert error_event.ps_object.CategoryInfo.Reason is None
    assert error_event.ps_object.CategoryInfo.TargetName is None
    assert error_event.ps_object.CategoryInfo.TargetType is None
    assert error_event.ps_object.ErrorDetails is None
    assert error_event.ps_object.InvocationInfo is None
    assert error_event.ps_object.PipelineIterationInfo is None
    assert error_event.ps_object.ScriptStackTrace is None
    assert error_event.ps_object.TargetObject is None

    verbose_event = client.next_event()
    assert isinstance(verbose_event, psrpcore.VerboseRecordEvent)
    assert isinstance(verbose_event.ps_object, InformationalRecord)
    assert verbose_event.ps_object.InvocationInfo is None
    assert verbose_event.ps_object.Message == "verbose"
    assert verbose_event.ps_object.PipelineIterationInfo is None

    warning_event = client.next_event()
    assert isinstance(warning_event, psrpcore.WarningRecordEvent)
    assert isinstance(warning_event.ps_object, InformationalRecord)
    assert warning_event.ps_object.InvocationInfo is None
    assert warning_event.ps_object.Message == "warning"
    assert warning_event.ps_object.PipelineIterationInfo is None

    info_event = client.next_event()
    assert isinstance(info_event, psrpcore.InformationRecordEvent)
    assert isinstance(info_event.ps_object, InformationRecord)
    assert info_event.ps_object.Computer is not None
    assert info_event.ps_object.ManagedThreadId == 0
    assert info_event.ps_object.MessageData == "information"
    if hasattr(threading, "get_native_id"):
        assert info_event.ps_object.NativeThreadId > 0
    else:
        assert info_event.ps_object.NativeThreadId == 0
    assert info_event.ps_object.ProcessId > 0
    assert info_event.ps_object.Source == "source"
    assert info_event.ps_object.Tags == []
    assert info_event.ps_object.TimeGenerated is not None
    assert info_event.ps_object.User is not None

    progress_event = client.next_event()
    assert isinstance(progress_event, psrpcore.ProgressRecordEvent)
    assert progress_event.ps_object.Activity == "activity"
    assert progress_event.ps_object.ActivityId == 1
    assert progress_event.ps_object.CurrentOperation is None
    assert progress_event.ps_object.ParentActivityId == -1
    assert progress_event.ps_object.PercentComplete == -1
    assert progress_event.ps_object.SecondsRemaining == -1
    assert progress_event.ps_object.StatusDescription == "description"
    assert progress_event.ps_object.Type == ProgressRecordType.Processing

    state_event = client.next_event()
    assert isinstance(state_event, psrpcore.PipelineStateEvent)
    assert state_event.state == PSInvocationState.Completed
    assert client.next_event() is None


def test_pipeline_stop():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientPowerShell(client, no_input=False)
    assert c_pipeline.state == PSInvocationState.NotStarted

    c_pipeline.add_script("script")
    c_pipeline.invoke()
    assert c_pipeline.state == PSInvocationState.Running

    c_command = client.data_to_send()
    server.receive_data(c_command)
    create_pipeline = server.next_event()
    s_pipeline = create_pipeline.pipeline
    s_pipeline.start()

    s_pipeline.stop()
    assert s_pipeline.state == PSInvocationState.Stopped
    assert server.pipeline_table == {}

    client.receive_data(server.data_to_send())
    state = client.next_event()

    assert client.next_event() is None
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert isinstance(state.reason, ErrorRecord)
    assert state.state == PSInvocationState.Stopped
    assert str(state.reason) == "The pipeline has been stopped."
    assert str(state.reason.CategoryInfo) == "OperationStopped (:) [], PipelineStoppedException"
    assert state.reason.CategoryInfo.Category == ErrorCategory.OperationStopped
    assert state.reason.CategoryInfo.Reason == "PipelineStoppedException"
    assert state.reason.Exception.Message == "The pipeline has been stopped."
    assert state.reason.Exception.HResult == -2146233087
    assert state.reason.FullyQualifiedErrorId == "PipelineStopped"
    assert state.reason.InvocationInfo is None
    assert state.reason.PipelineIterationInfo is None
    assert state.reason.ScriptStackTrace is None
    assert state.reason.TargetObject is None
    assert c_pipeline.state == PSInvocationState.Stopped
    assert client.pipeline_table == {}


def test_pipeline_host_call():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientPowerShell(client)
    # This is meant to be parsed by some engine and isn't actually read in this test
    # Just used to indicate a scenario where this would occur.
    c_pipeline.add_script('$host.UI.PromptForCredential("caption", "message", "username", "targetname")')
    c_pipeline.invoke()

    server.receive_data(client.data_to_send())
    s_pipeline = server.next_event().pipeline
    s_pipeline.start()
    s_pipeline.host_call(HostMethodIdentifier.PromptForCredential1, ["caption", "message", "username", "targetname"])

    client.receive_data(server.data_to_send())
    host_call = client.next_event()
    assert isinstance(host_call, psrpcore.PipelineHostCallEvent)
    assert host_call.ps_object.ci == 1
    assert host_call.ps_object.mi == HostMethodIdentifier.PromptForCredential1
    assert host_call.ps_object.mp == ["caption", "message", "username", "targetname"]

    c_pipeline.host_response(1, "prompt response")
    server.receive_data(client.data_to_send())
    host_response = server.next_event()
    assert isinstance(host_response, psrpcore.PipelineHostResponseEvent)
    assert host_response.ps_object.ci == 1
    assert host_response.ps_object.mi == HostMethodIdentifier.PromptForCredential1
    assert host_response.ps_object.mr == "prompt response"


def test_command_metadata():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientGetCommandMetadata(client, "Invoke*")
    c_pipeline.invoke()

    server.receive_data(client.data_to_send())
    command_meta = server.next_event()
    assert isinstance(command_meta, psrpcore.GetCommandMetadataEvent)
    assert isinstance(command_meta.pipeline, psrpcore.ServerGetCommandMetadata)
    s_pipeline = command_meta.pipeline
    s_pipeline.start()

    with pytest.raises(ValueError, match="write_count must be called before writing to the command metadata pipeline"):
        s_pipeline.write_output("abc")

    s_pipeline.write_count(1)
    s_pipeline.write_cmdlet_info("Invoke-Expression", "namespace")
    s_pipeline.close()

    assert s_pipeline.state == PSInvocationState.Completed
    assert server.pipeline_table == {}

    client.receive_data(server.data_to_send())
    count = client.next_event()
    iex = client.next_event()
    state = client.next_event()

    assert client.next_event() is None
    assert c_pipeline.state == PSInvocationState.Completed
    assert client.pipeline_table == {}

    assert isinstance(count, psrpcore.PipelineOutputEvent)
    assert count.ps_object.Count == 1
    assert isinstance(iex, psrpcore.PipelineOutputEvent)
    assert iex.ps_object.Name == "Invoke-Expression"
    assert iex.ps_object.Namespace == "namespace"
    assert iex.ps_object.HelpUri == ""
    assert iex.ps_object.OutputType == []
    assert iex.ps_object.Parameters == {}
    assert iex.ps_object.ResolvedCommandName is None
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == PSInvocationState.Completed


def test_exchange_key_client():
    client, server = get_runspace_pair()

    client.exchange_key()
    server.receive_data(client.data_to_send())
    public_key = server.next_event()
    assert isinstance(public_key, psrpcore.PublicKeyEvent)

    client.receive_data(server.data_to_send())
    enc_key = client.next_event()
    assert isinstance(enc_key, psrpcore.EncryptedSessionKeyEvent)

    c_pipeline = psrpcore.ClientPowerShell(client)
    c_pipeline.add_script("command")
    c_pipeline.add_argument(PSSecureString("my secret"))
    c_pipeline.invoke()
    c_pipeline_data = client.data_to_send()
    assert b"my_secret" not in c_pipeline_data.data

    server.receive_data(c_pipeline_data)
    create_pipeline = server.next_event()
    assert isinstance(create_pipeline, psrpcore.CreatePipelineEvent)

    s_pipeline = create_pipeline.pipeline
    assert len(s_pipeline.commands) == 1
    assert s_pipeline.commands[0].command_text == "command"
    assert s_pipeline.commands[0].parameters == [(None, "my secret")]
    assert isinstance(s_pipeline.commands[0].parameters[0][1], PSSecureString)

    s_pipeline.start()
    s_pipeline.write_output(PSSecureString("secret output"))
    s_pipeline.close()
    s_output = server.data_to_send()
    assert s_pipeline.state == PSInvocationState.Completed
    assert server.pipeline_table == {}
    assert b"secret output" not in s_output

    client.receive_data(s_output)
    out = client.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert isinstance(out.ps_object, PSSecureString)
    assert out.ps_object == "secret output"

    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == PSInvocationState.Completed

    assert c_pipeline.state == PSInvocationState.Completed
    assert client.pipeline_table == {}


def test_exchange_key_request():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientPowerShell(client)
    c_pipeline.add_script("command")
    c_pipeline.invoke()
    server.receive_data(client.data_to_send())
    s_pipeline = server.next_event().pipeline
    s_pipeline.start()

    with pytest.raises(psrpcore.MissingCipherError):
        s_pipeline.write_output(PSSecureString("secret"))

    server.request_key()
    client.receive_data(server.data_to_send())
    pub_key_req = client.next_event()
    assert isinstance(pub_key_req, psrpcore.PublicKeyRequestEvent)

    with pytest.raises(psrpcore.MissingCipherError):
        s_pipeline.write_output(PSSecureString("secret"))

    server.receive_data(client.data_to_send())
    pub_key = server.next_event()
    assert isinstance(pub_key, psrpcore.PublicKeyEvent)

    s_pipeline.write_output(PSSecureString("secret"))
    s_pipeline.close()
    assert s_pipeline.state == PSInvocationState.Completed
    assert server.pipeline_table == {}

    client.receive_data(server.data_to_send())
    enc_key = client.next_event()
    assert isinstance(enc_key, psrpcore.EncryptedSessionKeyEvent)

    b_data = server.data_to_send()
    client.receive_data(b_data)
    assert b"secret" not in b_data

    out = client.next_event()
    assert isinstance(out, psrpcore.PipelineOutputEvent)
    assert isinstance(out.ps_object, PSSecureString)
    assert out.ps_object == "secret"

    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == PSInvocationState.Completed
    assert c_pipeline.state == PSInvocationState.Completed
    assert client.pipeline_table == {}

    # Subsequent calls shouldn't do anything
    server.request_key()
    assert server.data_to_send() is None

    client.exchange_key()
    assert client.data_to_send() is None
