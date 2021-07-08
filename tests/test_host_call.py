# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)
import typing
import uuid

import psrpcore
from psrpcore.types import HostMethodIdentifier

from .conftest import COMPLEX_STRING, get_runspace_pair


def get_runspace_pipeline_host_pair(
    script: str,
) -> typing.Tuple[
    psrpcore.ClientRunspacePool, psrpcore.ServerRunspacePool, psrpcore.ClientHostResponder, psrpcore.ServerHostRequestor
]:
    client, server = get_runspace_pair()
    c_ps = psrpcore.ClientPowerShell(client)
    c_ps.add_script(script)
    c_ps.start()

    s_ps = psrpcore.ServerPipeline(server, c_ps.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()
    s_ps.start()
    client.receive_data(server.data_to_send())
    client.next_event()

    return client, server, psrpcore.ClientHostResponder(c_ps), psrpcore.ServerHostRequestor(s_ps)


def test_host_response_error_no_type():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.ReadLine()")

    ci = s_host.read_line()
    client.receive_data(server.data_to_send())
    client.next_event()

    # Sometimes the pshost returns a typeless error record. This replicates that behaviour.
    error = psrpcore.types.ErrorRecordMsg(
        Exception=psrpcore.types.NETException("error message"),
        CategoryInfo=psrpcore.types.ErrorCategoryInfo(),
    )
    error.PSObject.type_names = []
    client.host_response(ci, error_record=error)

    server.receive_data(client.data_to_send())
    resp = server.next_event()
    assert isinstance(resp.error, psrpcore.types.ErrorRecord)
    assert str(resp.error) == "error message"
    assert resp.result is None


def test_get_name():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.Name")

    ci = s_host.get_name()
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == ci
    assert call.method_identifier == HostMethodIdentifier.GetName
    assert call.method_parameters == []

    c_host.get_name(call.ci, COMPLEX_STRING)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetName
    assert resp.result == COMPLEX_STRING
    assert resp.error is None


def test_get_version():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.Version")

    ci = s_host.get_version()
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == ci
    assert call.method_identifier == HostMethodIdentifier.GetVersion
    assert call.method_parameters == []

    c_host.get_version(call.ci, "1.2.3.4")
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetVersion
    assert resp.result == psrpcore.types.PSVersion("1.2.3.4")
    assert resp.error is None


def test_get_instance_id():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.InstanceId")

    ci = s_host.get_instance_id()
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == ci
    assert call.method_identifier == HostMethodIdentifier.GetInstanceId
    assert call.method_parameters == []

    c_host.get_instance_id(call.ci, uuid.UUID(int=0))
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetInstanceId
    assert resp.result == psrpcore.types.PSGuid(int=0)
    assert resp.error is None


def test_get_current_culture():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.CurrentCulture")

    ci = s_host.get_current_culture()
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == ci
    assert call.method_identifier == HostMethodIdentifier.GetCurrentCulture
    assert call.method_parameters == []

    c_host.get_current_culture(call.ci, "en-AU")
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetCurrentCulture
    assert resp.result == "en-AU"
    assert resp.error is None


def test_get_current_ui_culture():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.CurrentUICulture")

    ci = s_host.get_current_ui_culture()
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == ci
    assert call.method_identifier == HostMethodIdentifier.GetCurrentUICulture
    assert call.method_parameters == []

    c_host.get_current_ui_culture(call.ci, "en-AU")
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetCurrentUICulture
    assert resp.result == "en-AU"
    assert resp.error is None


def test_set_should_exit():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.SetShouldExit(1)")

    ci = s_host.set_should_exit(1)
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.SetShouldExit
    assert call.method_parameters == [1]


def test_enter_nested_prompt():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.EnterNestedPrompt()")

    ci = s_host.enter_nested_prompt()
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.EnterNestedPrompt
    assert call.method_parameters == []


def test_exit_nested_prompt():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.ExitNestedPrompt()")

    ci = s_host.exit_nested_prompt()
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.ExitNestedPrompt
    assert call.method_parameters == []


def test_notify_begin_application():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.NotifyBeginApplication()")

    ci = s_host.notify_begin_application()
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.NotifyBeginApplication
    assert call.method_parameters == []


def test_notify_end_application():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.NotifyEndApplication()")

    ci = s_host.notify_end_application()
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.NotifyEndApplication
    assert call.method_parameters == []


def test_pop_runspace():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.PopRunspace()")

    ci = s_host.pop_runspace()
    assert ci is None

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.PopRunspace
    assert call.method_parameters == []


def test_get_is_runspace_pushed():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.IsRunspacePushed")

    ci = s_host.get_is_runspace_pushed()
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.GetIsRunspacePushed
    assert call.method_parameters == []

    c_host.get_is_runspace_pushed(call.ci, False)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetIsRunspacePushed
    assert resp.result is False
    assert resp.error is None


def test_read_line():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.ReadLine()")

    ci = s_host.read_line()
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.method_identifier == HostMethodIdentifier.ReadLine
    assert call.method_parameters == []

    c_host.read_line(call.ci, COMPLEX_STRING)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.ReadLine
    assert resp.result == COMPLEX_STRING
    assert resp.error is None


def test_read_line_as_secure_string():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.ReadLineAsSecureString()")

    ci = s_host.read_line_as_secure_string()
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.method_identifier == HostMethodIdentifier.ReadLineAsSecureString
    assert call.method_parameters == []

    client.exchange_key()
    server.receive_data(client.data_to_send())
    server.next_event()
    client.receive_data(server.data_to_send())
    client.next_event()

    c_host.read_line_as_secure_string(call.ci, psrpcore.types.PSSecureString(COMPLEX_STRING))
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.ReadLineAsSecureString
    assert isinstance(resp.result, psrpcore.types.PSSecureString)
    assert resp.result.decrypt() == COMPLEX_STRING
    assert resp.error is None


def test_write1():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.Write('write')")

    ci = s_host.write("write")
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.Write1
    assert call.method_parameters == ["write"]


def test_write2():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.Write('DarkBlue', 'White', 'write')")

    ci = s_host.write("write", psrpcore.types.ConsoleColor.DarkBlue, psrpcore.types.ConsoleColor.White)
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.Write2
    assert call.method_parameters == [psrpcore.types.ConsoleColor.DarkBlue, psrpcore.types.ConsoleColor.White, "write"]
    assert isinstance(call.method_parameters[0], psrpcore.types.ConsoleColor)
    assert isinstance(call.method_parameters[1], psrpcore.types.ConsoleColor)

    # Try it with omitting the background color (defaults to 0/Black).
    ci = s_host.write("write", psrpcore.types.ConsoleColor.DarkBlue)
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.Write2
    assert call.method_parameters == [psrpcore.types.ConsoleColor.DarkBlue, psrpcore.types.ConsoleColor.Black, "write"]
    assert isinstance(call.method_parameters[0], psrpcore.types.ConsoleColor)
    assert isinstance(call.method_parameters[1], psrpcore.types.ConsoleColor)


def test_write_line1():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.WriteLine()")

    ci = s_host.write_line()
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.method_identifier == HostMethodIdentifier.WriteLine1
    assert call.method_parameters == []


def test_write_line2():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.WriteLine('line')")

    ci = s_host.write_line("line")
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.method_identifier == HostMethodIdentifier.WriteLine2
    assert call.method_parameters == ["line"]


def test_write_line3():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.WriteLine('DarkBlue', 'White', 'line')")
    ci = s_host.write_line("line", psrpcore.types.ConsoleColor.DarkBlue, psrpcore.types.ConsoleColor.White)
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.method_identifier == HostMethodIdentifier.WriteLine3
    assert call.method_parameters == [psrpcore.types.ConsoleColor.DarkBlue, psrpcore.types.ConsoleColor.White, "line"]
    assert isinstance(call.method_parameters[0], psrpcore.types.ConsoleColor)
    assert isinstance(call.method_parameters[1], psrpcore.types.ConsoleColor)

    # Try it with omitting the background color (defaults to 0/Black).
    ci = s_host.write_line(background_color=psrpcore.types.ConsoleColor.Red)
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.WriteLine3
    assert call.method_parameters == [psrpcore.types.ConsoleColor.Black, psrpcore.types.ConsoleColor.Red, ""]
    assert isinstance(call.method_parameters[0], psrpcore.types.ConsoleColor)
    assert isinstance(call.method_parameters[1], psrpcore.types.ConsoleColor)


def test_write_error_line():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.WriteErrorLine('line')")

    ci = s_host.write_error_line("line")
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.method_identifier == HostMethodIdentifier.WriteErrorLine
    assert call.method_parameters == ["line"]


def test_write_debug_line():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.WriteDebugLine('line')")

    ci = s_host.write_debug_line("line")
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.method_identifier == HostMethodIdentifier.WriteDebugLine
    assert call.method_parameters == ["line"]


def test_write_progress():
    client, server, _, s_host = get_runspace_pipeline_host_pair(
        """
        $rec = [System.Management.Automation.ProgressRecord]::new(1, 'activity', 'status')
        $host.UI.WriteProgress(10, $rec)
    """
    )

    ci = s_host.write_progress(10, 1, "activity", "status")
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.method_identifier == HostMethodIdentifier.WriteProgress
    assert len(call.method_parameters) == 2
    assert call.method_parameters[0] == 10
    assert isinstance(call.method_parameters[1], psrpcore.types.ProgressRecord)

    record = call.method_parameters[1]
    assert record.ActivityId == 1
    assert record.Activity == "activity"
    assert record.StatusDescription == "status"
    assert record.CurrentOperation is None
    assert record.ParentActivityId == -1
    assert record.PercentComplete == -1
    assert record.RecordType == psrpcore.types.ProgressRecordType.Processing
    assert record.SecondsRemaining == -1


def test_write_verbose_line():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.WriteVerboseLine('line')")

    ci = s_host.write_verbose_line("line")
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.method_identifier == HostMethodIdentifier.WriteVerboseLine
    assert call.method_parameters == ["line"]


def test_write_warning_line():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.WriteWarningLine('line')")

    ci = s_host.write_warning_line("line")
    assert ci is None
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.method_identifier == HostMethodIdentifier.WriteWarningLine
    assert call.method_parameters == ["line"]


def test_prompt():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair(
        """
        $descriptions = @(
            [System.Management.Automation.Host.FieldDescription]::new("name 1"),
            [System.Management.Automation.Host.FieldDescription]::new("name 2")
        )
        $host.UI.Prompt("caption", "message", $descriptions)
    """
    )

    ci = s_host.prompt(
        "caption",
        "message",
        [
            psrpcore.types.FieldDescription("name 1"),
            psrpcore.types.FieldDescription("name 2"),
        ],
    )
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.Prompt
    assert len(call.method_parameters) == 3
    assert call.method_parameters[0] == "caption"
    assert call.method_parameters[1] == "message"
    assert len(call.method_parameters[2]) == 2
    assert isinstance(call.method_parameters[2][0], psrpcore.types.FieldDescription)
    assert call.method_parameters[2][0].Name == "name 1"
    assert isinstance(call.method_parameters[2][1], psrpcore.types.FieldDescription)
    assert call.method_parameters[2][1].Name == "name 2"

    c_host.prompt(call.ci, {"name 1": 1, "name 2": "2"})
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.Prompt
    assert resp.result == {"name 1": 1, "name 2": "2"}
    assert resp.error is None


def test_prompt_for_credential_defaults():
    # Technically this calls PromptForCredential2 but we replicate it with 1.
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("Get-Credential")

    ci = s_host.prompt_for_credential()
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.PromptForCredential1
    assert len(call.method_parameters) == 4
    assert call.method_parameters[0] == "PSRPCore credential request"
    assert call.method_parameters[1] == "Enter your credentials."
    assert call.method_parameters[2] is None
    assert call.method_parameters[3] == ""

    client.exchange_key()
    server.receive_data(client.data_to_send())
    server.next_event()
    client.receive_data(server.data_to_send())
    client.next_event()

    c_host.prompt_for_credential(
        call.ci, psrpcore.types.PSCredential("username", psrpcore.types.PSSecureString("password"))
    )
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.PromptForCredential1
    assert isinstance(resp.result, psrpcore.types.PSCredential)
    assert resp.result.UserName == "username"
    assert isinstance(resp.result.Password, psrpcore.types.PSSecureString)
    assert resp.result.Password.decrypt() == "password"
    assert resp.error is None


def test_prompt_for_credential1():
    # Pwsh also uses Credential2 here but for strictness we also do 1.
    client, server, c_host, s_host = get_runspace_pipeline_host_pair(
        "$host.UI.PromptForCredential('caption', 'message', 'username', 'target name')"
    )

    ci = s_host.prompt_for_credential("caption", "message", "username", "target name")
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.PromptForCredential1
    assert len(call.method_parameters) == 4
    assert call.method_parameters[0] == "caption"
    assert call.method_parameters[1] == "message"
    assert call.method_parameters[2] == "username"
    assert call.method_parameters[3] == "target name"

    client.exchange_key()
    server.receive_data(client.data_to_send())
    server.next_event()
    client.receive_data(server.data_to_send())
    client.next_event()

    c_host.prompt_for_credential(
        call.ci, psrpcore.types.PSCredential("username", psrpcore.types.PSSecureString("password"))
    )
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.PromptForCredential1
    assert isinstance(resp.result, psrpcore.types.PSCredential)
    assert resp.result.UserName == "username"
    assert isinstance(resp.result.Password, psrpcore.types.PSSecureString)
    assert resp.result.Password.decrypt() == "password"
    assert resp.error is None


def test_prompt_for_credential2():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair(
        "$host.UI.PromptForCredential('caption', 'message', 'username', 'target name', 'Domain', 'AlwaysPrompt')"
    )

    ci = s_host.prompt_for_credential(
        "caption",
        "message",
        "username",
        "target name",
        psrpcore.types.PSCredentialTypes.Domain,
        psrpcore.types.PSCredentialUIOptions.AlwaysPrompt,
    )
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.PromptForCredential2
    assert len(call.method_parameters) == 6
    assert call.method_parameters[0] == "caption"
    assert call.method_parameters[1] == "message"
    assert call.method_parameters[2] == "username"
    assert call.method_parameters[3] == "target name"
    assert call.method_parameters[4] == psrpcore.types.PSCredentialTypes.Domain
    assert isinstance(call.method_parameters[4], psrpcore.types.PSCredentialTypes)
    assert call.method_parameters[5] == psrpcore.types.PSCredentialUIOptions.AlwaysPrompt
    assert isinstance(call.method_parameters[5], psrpcore.types.PSCredentialUIOptions)

    client.exchange_key()
    server.receive_data(client.data_to_send())
    server.next_event()
    client.receive_data(server.data_to_send())
    client.next_event()

    c_host.prompt_for_credential(
        call.ci, psrpcore.types.PSCredential("username", psrpcore.types.PSSecureString("password"))
    )
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.PromptForCredential2
    assert isinstance(resp.result, psrpcore.types.PSCredential)
    assert resp.result.UserName == "username"
    assert isinstance(resp.result.Password, psrpcore.types.PSSecureString)
    assert resp.result.Password.decrypt() == "password"
    assert resp.error is None


def test_prompt_for_choice():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair(
        """
        $choices = @(
            [System.Management.Automation.Host.ChoiceDescription]::new("name 1"),
            [System.Management.Automation.Host.ChoiceDescription]::new("name 2", "help msg")
        )
        $host.UI.PromptForChoice("caption", "message", $choices, -1)
    """
    )

    ci = s_host.prompt_for_choice(
        "caption",
        "message",
        [
            psrpcore.types.ChoiceDescription("name 1"),
            psrpcore.types.ChoiceDescription("name 2", "help msg"),
        ],
    )
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.PromptForChoice
    assert len(call.method_parameters) == 4
    assert call.method_parameters[0] == "caption"
    assert call.method_parameters[1] == "message"
    assert len(call.method_parameters[2]) == 2
    assert isinstance(call.method_parameters[2][0], psrpcore.types.ChoiceDescription)
    assert call.method_parameters[2][0].Label == "name 1"
    assert call.method_parameters[2][0].HelpMessage is None
    assert isinstance(call.method_parameters[2][1], psrpcore.types.ChoiceDescription)
    assert call.method_parameters[2][1].Label == "name 2"
    assert call.method_parameters[2][1].HelpMessage == "help msg"
    assert call.method_parameters[3] == -1

    c_host.prompt_for_choice(call.ci, 0)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.PromptForChoice
    assert resp.result == 0
    assert resp.error is None


def test_prompt_for_choice_multiple_selection_defaults():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair(
        """
        $default = [System.Collections.ObjectModel.Collection[int]]::new()
        $default.Add(0)
        $default.Add(1)
        $choices = @(
            [System.Management.Automation.Host.ChoiceDescription]::new("name 1"),
            [System.Management.Automation.Host.ChoiceDescription]::new("name 2", "help msg"),
            [System.Management.Automation.Host.ChoiceDescription]::new("name 3", "other help msg")
        )
        $host.UI.PromptForChoice("caption", "message", $choices, $default)
    """
    )

    ci = s_host.prompt_for_multiple_choice(
        "caption",
        "message",
        [
            psrpcore.types.ChoiceDescription("name 1"),
            psrpcore.types.ChoiceDescription("name 2", "help msg"),
            psrpcore.types.ChoiceDescription("name 3", "other help msg"),
        ],
    )
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.PromptForChoiceMultipleSelection
    assert len(call.method_parameters) == 4
    assert call.method_parameters[0] == "caption"
    assert call.method_parameters[1] == "message"

    assert len(call.method_parameters[2]) == 3
    assert isinstance(call.method_parameters[2][0], psrpcore.types.ChoiceDescription)
    assert call.method_parameters[2][0].Label == "name 1"
    assert call.method_parameters[2][0].HelpMessage is None
    assert isinstance(call.method_parameters[2][1], psrpcore.types.ChoiceDescription)
    assert call.method_parameters[2][1].Label == "name 2"
    assert call.method_parameters[2][1].HelpMessage == "help msg"
    assert isinstance(call.method_parameters[2][2], psrpcore.types.ChoiceDescription)
    assert call.method_parameters[2][2].Label == "name 3"
    assert call.method_parameters[2][2].HelpMessage == "other help msg"

    assert call.method_parameters[3] == []

    c_host.prompt_for_multiple_choice(call.ci, 1)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.PromptForChoiceMultipleSelection
    assert resp.result == [1]
    assert resp.error is None


def test_prompt_for_choice_multiple_selection():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair(
        """
        $default = [System.Collections.ObjectModel.Collection[int]]::new()
        $default.Add(0)
        $default.Add(1)
        $choices = @(
            [System.Management.Automation.Host.ChoiceDescription]::new("name 1"),
            [System.Management.Automation.Host.ChoiceDescription]::new("name 2", "help msg"),
            [System.Management.Automation.Host.ChoiceDescription]::new("name 3", "other help msg")
        )
        $host.UI.PromptForChoice("caption", "message", $choices, $default)
    """
    )

    ci = s_host.prompt_for_multiple_choice(
        "caption",
        "message",
        [
            psrpcore.types.ChoiceDescription("name 1"),
            psrpcore.types.ChoiceDescription("name 2", "help msg"),
            psrpcore.types.ChoiceDescription("name 3", "other help msg"),
        ],
        [1, 2],
    )
    assert ci == 1
    client.receive_data(server.data_to_send())

    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.PromptForChoiceMultipleSelection
    assert len(call.method_parameters) == 4
    assert call.method_parameters[0] == "caption"
    assert call.method_parameters[1] == "message"

    assert len(call.method_parameters[2]) == 3
    assert isinstance(call.method_parameters[2][0], psrpcore.types.ChoiceDescription)
    assert call.method_parameters[2][0].Label == "name 1"
    assert call.method_parameters[2][0].HelpMessage is None
    assert isinstance(call.method_parameters[2][1], psrpcore.types.ChoiceDescription)
    assert call.method_parameters[2][1].Label == "name 2"
    assert call.method_parameters[2][1].HelpMessage == "help msg"
    assert isinstance(call.method_parameters[2][2], psrpcore.types.ChoiceDescription)
    assert call.method_parameters[2][2].Label == "name 3"
    assert call.method_parameters[2][2].HelpMessage == "other help msg"

    assert call.method_parameters[3] == [1, 2]

    c_host.prompt_for_multiple_choice(call.ci, [0, 2])
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.PromptForChoiceMultipleSelection
    assert resp.result == [0, 2]
    assert resp.error is None


def test_get_foreground_color():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.ForegroundColor")

    ci = s_host.get_foreground_color()
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.GetForegroundColor
    assert call.method_parameters == []

    c_host.get_foreground_color(call.ci, psrpcore.types.ConsoleColor.DarkCyan)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetForegroundColor
    assert resp.result == psrpcore.types.ConsoleColor.DarkCyan
    assert resp.error is None


def test_set_foreground_color():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.ForegroundColor = 'Blue'")

    ci = s_host.set_foreground_color(psrpcore.types.ConsoleColor.Blue)
    assert ci is None

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.SetForegroundColor
    assert call.method_parameters == [psrpcore.types.ConsoleColor.Blue]
    assert isinstance(call.method_parameters[0], psrpcore.types.ConsoleColor)


def test_get_background_color():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.BackgroundColor")

    ci = s_host.get_background_color()
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.GetBackgroundColor
    assert call.method_parameters == []

    c_host.get_background_color(call.ci, psrpcore.types.ConsoleColor.Gray)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetBackgroundColor
    assert resp.result == psrpcore.types.ConsoleColor.Gray
    assert resp.error is None


def test_set_background_color():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.BackgroundColor = 'Red'")

    ci = s_host.set_background_color(psrpcore.types.ConsoleColor.DarkMagenta)
    assert ci is None

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.SetBackgroundColor
    assert call.method_parameters == [psrpcore.types.ConsoleColor.DarkMagenta]
    assert isinstance(call.method_parameters[0], psrpcore.types.ConsoleColor)


def test_get_cursor_position():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.CursorPosition")

    ci = s_host.get_cursor_position()
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.GetCursorPosition
    assert call.method_parameters == []

    c_host.get_cursor_position(call.ci, 1, 2)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetCursorPosition
    assert isinstance(resp.result, psrpcore.types.Coordinates)
    assert resp.result.X == 1
    assert resp.result.Y == 2
    assert resp.error is None


def test_set_cursor_position():
    client, server, _, s_host = get_runspace_pipeline_host_pair(
        "$host.UI.RawUI.CursorPosition = [System.Management.Automation.Host.Coordinates]@{X=0; Y=10}"
    )

    ci = s_host.set_cursor_position(0, 10)
    assert ci is None

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.SetCursorPosition
    assert len(call.method_parameters) == 1
    assert isinstance(call.method_parameters[0], psrpcore.types.Coordinates)
    assert call.method_parameters[0].X == 0
    assert call.method_parameters[0].Y == 10


def test_get_window_position():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.WindowPosition")

    ci = s_host.get_window_position()
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.GetWindowPosition
    assert call.method_parameters == []

    c_host.get_window_position(call.ci, 3, 4)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetWindowPosition
    assert isinstance(resp.result, psrpcore.types.Coordinates)
    assert resp.result.X == 3
    assert resp.result.Y == 4
    assert resp.error is None


def test_set_window_position():
    client, server, _, s_host = get_runspace_pipeline_host_pair(
        "$host.UI.RawUI.WindowPosition = [System.Management.Automation.Host.Coordinates]@{X=0; Y=10}"
    )

    ci = s_host.set_window_position(0, 10)
    assert ci is None

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.SetWindowPosition
    assert len(call.method_parameters) == 1
    assert isinstance(call.method_parameters[0], psrpcore.types.Coordinates)
    assert call.method_parameters[0].X == 0
    assert call.method_parameters[0].Y == 10


def test_get_cursor_size():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.CursorSize")

    ci = s_host.get_cursor_size()
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.GetCursorSize
    assert call.method_parameters == []

    c_host.get_cursor_size(call.ci, 10)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetCursorSize
    assert resp.result == 10
    assert resp.error is None


def test_set_cursor_size():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.CursorSize = 10")

    ci = s_host.set_cursor_size(10)
    assert ci is None

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.SetCursorSize
    assert call.method_parameters == [10]


def test_get_buffer_size():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.BufferSize")

    ci = s_host.get_buffer_size()
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.GetBufferSize
    assert call.method_parameters == []

    c_host.get_buffer_size(call.ci, 10, 20)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetBufferSize
    assert isinstance(resp.result, psrpcore.types.Size)
    assert resp.result.Width == 10
    assert resp.result.Height == 20
    assert resp.error is None


def test_set_buffer_size():
    client, server, _, s_host = get_runspace_pipeline_host_pair(
        "$host.UI.RawUI.BufferSize = [System.Management.Automation.Host.Size]@{Width=10; Height=20}"
    )

    ci = s_host.set_buffer_size(10, 20)
    assert ci is None

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.SetBufferSize
    assert len(call.method_parameters) == 1
    assert isinstance(call.method_parameters[0], psrpcore.types.Size)
    assert call.method_parameters[0].Width == 10
    assert call.method_parameters[0].Height == 20


def test_get_window_size():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.WindowSize")

    ci = s_host.get_window_size()
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.GetWindowSize
    assert call.method_parameters == []

    c_host.get_window_size(call.ci, 10, 20)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetWindowSize
    assert isinstance(resp.result, psrpcore.types.Size)
    assert resp.result.Width == 10
    assert resp.result.Height == 20
    assert resp.error is None


def test_set_window_size():
    client, server, _, s_host = get_runspace_pipeline_host_pair(
        "$host.UI.RawUI.WindowSize = [System.Management.Automation.Host.Size]@{Width=10; Height=20}"
    )

    ci = s_host.set_window_size(10, 20)
    assert ci is None

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.SetWindowSize
    assert len(call.method_parameters) == 1
    assert isinstance(call.method_parameters[0], psrpcore.types.Size)
    assert call.method_parameters[0].Width == 10
    assert call.method_parameters[0].Height == 20


def test_get_window_title():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.WindowTitle")

    ci = s_host.get_window_title()
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.GetWindowTitle
    assert call.method_parameters == []

    c_host.get_window_title(call.ci, "existing title")
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetWindowTitle
    assert resp.result == "existing title"
    assert resp.error is None


def test_set_window_title():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.WindowTitle = 'new title'")

    ci = s_host.set_window_title("new title")
    assert ci is None

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.SetWindowTitle
    assert len(call.method_parameters) == 1
    assert call.method_parameters == ["new title"]


def test_get_max_window_size():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.MaxWindowSize")

    ci = s_host.get_max_window_size()
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.GetMaxWindowSize
    assert call.method_parameters == []

    c_host.get_max_window_size(call.ci, 10, 20)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetMaxWindowSize
    assert isinstance(resp.result, psrpcore.types.Size)
    assert resp.result.Width == 10
    assert resp.result.Height == 20
    assert resp.error is None


def test_get_max_physical_window_size():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.MaxPhysicalWindowSize")

    ci = s_host.get_max_physical_window_size()
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.GetMaxPhysicalWindowSize
    assert call.method_parameters == []

    c_host.get_max_physical_window_size(call.ci, 10, 20)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetMaxPhysicalWindowSize
    assert isinstance(resp.result, psrpcore.types.Size)
    assert resp.result.Width == 10
    assert resp.result.Height == 20
    assert resp.error is None


def test_get_key_available():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.KeyAvailable")

    ci = s_host.get_key_available()
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.GetKeyAvailable
    assert call.method_parameters == []

    c_host.get_key_available(call.ci, False)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetKeyAvailable
    assert resp.result is False
    assert resp.error is None


def test_read_key():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.ReadKey()")

    ci = s_host.read_key()
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.ReadKey
    assert call.method_parameters == [psrpcore.types.ReadKeyOptions.IncludeKeyDown]

    c_host.read_key(call.ci, "é", True)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.ReadKey
    assert isinstance(resp.result, psrpcore.types.KeyInfo)
    assert resp.result.Character == psrpcore.types.PSChar("é")
    assert resp.result.KeyDown is True
    assert isinstance(resp.result.ControlKeyState, psrpcore.types.ControlKeyStates)
    assert resp.result.ControlKeyState == psrpcore.types.ControlKeyStates.none
    assert resp.result.VirtualKeyCode == 0
    assert resp.error is None


def test_flush_input_buffer():
    client, server, _, s_host = get_runspace_pipeline_host_pair("$host.UI.RawUI.FlushInputBuffer()")

    ci = s_host.flush_input_buffer()
    assert ci is None

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.FlushInputBuffer
    assert call.method_parameters == []


def test_set_buffer_contents1():
    client, server, _, s_host = get_runspace_pipeline_host_pair(
        """
        $rec = [System.Management.Automation.Host.Rectangle]::new(0, 0, 10, 10)
        $cell = [System.Management.Automation.Host.BufferCell]::new('a', 'White', 'Gray', 'Complete')
        $host.UI.RawUI.SetBufferContents($rec, $cell)
    """
    )

    ci = s_host.set_buffer_cells(0, 0, 10, 10, "a")
    assert ci is None

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.SetBufferContents1
    assert len(call.method_parameters) == 2

    assert isinstance(call.method_parameters[0], psrpcore.types.Rectangle)
    assert call.method_parameters[0].Left == 0
    assert call.method_parameters[0].Top == 0
    assert call.method_parameters[0].Right == 10
    assert call.method_parameters[0].Bottom == 10

    assert isinstance(call.method_parameters[1], psrpcore.types.BufferCell)
    assert isinstance(call.method_parameters[1].Character, psrpcore.types.PSChar)
    assert call.method_parameters[1].Character == 97
    assert call.method_parameters[1].ForegroundColor == psrpcore.types.ConsoleColor.White
    assert call.method_parameters[1].BackgroundColor == psrpcore.types.ConsoleColor.Black
    assert call.method_parameters[1].BufferCellType == psrpcore.types.BufferCellType.Complete


def test_set_buffer_contents2():
    client, server, _, s_host = get_runspace_pipeline_host_pair(
        """
        $coordinates = [System.Management.Automation.Host.Coordinates]::new(0, 0)
        $cell = [System.Management.Automation.Host.BufferCell]::new('a', 'White', 'Gray', 'Complete')
        $cells = $Host.UI.RawUI.NewBufferCellArray(3, 4, $cell)
        $host.UI.RawUI.SetBufferContents($coordinates, $cells)
    """
    )

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
    ci = s_host.set_buffer_contents(0, 10, contents)
    assert ci is None

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.SetBufferContents2
    assert len(call.method_parameters) == 2

    coordinates = call.method_parameters[0]
    assert isinstance(coordinates, psrpcore.types.Coordinates)
    assert coordinates.X == 0
    assert coordinates.Y == 10

    cells = call.method_parameters[1]
    assert isinstance(cells, list)
    assert len(cells) == 4
    for row in cells:
        assert isinstance(row, list)
        assert len(row) == 3
        for cell in row:
            assert isinstance(cell, psrpcore.types.BufferCell)
            assert cell.Character == psrpcore.types.PSChar("a")
            assert cell.ForegroundColor == psrpcore.types.ConsoleColor.White
            assert cell.BackgroundColor == psrpcore.types.ConsoleColor.Black
            assert cell.BufferCellType == psrpcore.types.BufferCellType.Complete


def test_get_buffer_contents():
    client, server, c_host, s_host = get_runspace_pipeline_host_pair(
        """
        $rec = [System.Management.Automation.Host.Rectangle]::new(0, 0, 10, 10)
        $host.UI.RawUI.GetBufferContents($rec)
        """
    )

    ci = s_host.get_buffer_contents(0, 0, 3, 4)
    assert ci == 1

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == 1
    assert call.method_identifier == HostMethodIdentifier.GetBufferContents
    assert len(call.method_parameters) == 1
    assert isinstance(call.method_parameters[0], psrpcore.types.Rectangle)
    assert call.method_parameters[0].Left == 0
    assert call.method_parameters[0].Top == 0
    assert call.method_parameters[0].Right == 3
    assert call.method_parameters[0].Bottom == 4

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
    c_host.get_buffer_contents(call.ci, contents)
    server.receive_data(client.data_to_send())

    resp = server.next_event()
    assert isinstance(resp, psrpcore.PipelineHostResponseEvent)
    assert resp.method_identifier == HostMethodIdentifier.GetBufferContents
    assert isinstance(resp.result, list)
    assert len(resp.result) == 4
    for row in resp.result:
        assert isinstance(row, list)
        assert len(row) == 3
        for cell in row:
            assert isinstance(cell, psrpcore.types.BufferCell)
            assert cell.Character == psrpcore.types.PSChar("a")
            assert cell.ForegroundColor == psrpcore.types.ConsoleColor.White
            assert cell.BackgroundColor == psrpcore.types.ConsoleColor.Black
            assert cell.BufferCellType == psrpcore.types.BufferCellType.Complete
    assert resp.error is None


def test_scroll_buffer_contents():
    client, server, _, s_host = get_runspace_pipeline_host_pair(
        """
        $coordinates = [System.Management.Automation.Host.Coordinates]::new(0, 0)
        $cell = [System.Management.Automation.Host.BufferCell]::new('a', 'White', 'Gray', 'Complete')
        $cells = $Host.UI.RawUI.NewBufferCellArray(3, 4, $cell)
        $host.UI.RawUI.SetBufferContents($coordinates, $cells)
    """
    )

    ci = s_host.scroll_buffer_contents(0, 0, 10, 10, 30, 40, 0, 50, 10, 60, "a")
    assert ci is None

    client.receive_data(server.data_to_send())
    call = client.next_event()
    assert isinstance(call, psrpcore.PipelineHostCallEvent)
    assert call.ci == -100
    assert call.method_identifier == HostMethodIdentifier.ScrollBufferContents
    assert len(call.method_parameters) == 4

    source = call.method_parameters[0]
    assert isinstance(source, psrpcore.types.Rectangle)
    assert source.Left == 0
    assert source.Top == 0
    assert source.Right == 10
    assert source.Bottom == 10

    destination = call.method_parameters[1]
    assert isinstance(destination, psrpcore.types.Coordinates)
    assert destination.X == 30
    assert destination.Y == 40

    clip = call.method_parameters[2]
    assert isinstance(clip, psrpcore.types.Rectangle)
    assert clip.Left == 0
    assert clip.Top == 50
    assert clip.Right == 10
    assert clip.Bottom == 60

    fill = call.method_parameters[3]
    assert isinstance(fill, psrpcore.types.BufferCell)
    assert fill.Character == psrpcore.types.PSChar("a")
    assert fill.ForegroundColor == psrpcore.types.ConsoleColor.White
    assert fill.BackgroundColor == psrpcore.types.ConsoleColor.Black
    assert fill.BufferCellType == psrpcore.types.BufferCellType.Complete
