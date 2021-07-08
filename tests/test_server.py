# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import re
import uuid

import pytest

import psrpcore
from psrpcore._pipeline import PowerShell
from psrpcore.types import (
    ErrorCategoryInfo,
    ErrorRecord,
    HostMethodIdentifier,
    NETException,
    PSInvocationState,
    RunspacePoolState,
)

from .conftest import get_runspace_pair


def test_close_with_begin():
    client, server = get_runspace_pair()

    server.begin_close()
    assert client.state == RunspacePoolState.Opened
    assert server.state == RunspacePoolState.Closing

    client.receive_data(server.data_to_send())
    state = client.next_event()
    assert isinstance(state, psrpcore.RunspacePoolStateEvent)
    assert state.state == RunspacePoolState.Closing
    assert state.reason is None
    assert client.state == RunspacePoolState.Closing
    assert server.state == RunspacePoolState.Closing

    server.close()
    assert client.state == RunspacePoolState.Closing
    assert server.state == RunspacePoolState.Closed

    client.receive_data(server.data_to_send())
    state = client.next_event()
    assert isinstance(state, psrpcore.RunspacePoolStateEvent)
    assert state.state == RunspacePoolState.Closed
    assert state.reason is None
    assert client.state == RunspacePoolState.Closed
    assert server.state == RunspacePoolState.Closed


def test_server_is_broken():
    client, server = get_runspace_pair()

    err = ErrorRecord(
        Exception=NETException(Message="exception message"),
        CategoryInfo=ErrorCategoryInfo(),
    )
    server.set_broken(err)
    assert client.state == RunspacePoolState.Opened
    assert server.state == RunspacePoolState.Broken

    client.receive_data(server.data_to_send())
    state = client.next_event()
    assert isinstance(state, psrpcore.RunspacePoolStateEvent)
    assert state.state == RunspacePoolState.Broken
    assert isinstance(state.reason, ErrorRecord)
    assert str(state.reason) == "exception message"
    assert client.state == RunspacePoolState.Broken
    assert server.state == RunspacePoolState.Broken


def test_connect_already_connected():
    server = get_runspace_pair()[1]
    server.connect()
    assert server.data_to_send() is None


def test_connect_invalid_state():
    server = psrpcore.ServerRunspacePool()

    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Disconnected' to accept Runspace Pool connections, "
        "current state is RunspacePoolState.BeforeOpen"
    )
    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        server.connect()


def test_send_event_invalid_state():
    server = psrpcore.ServerRunspacePool()

    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Opened' to generate a Runspace Pool event, "
        "current state is RunspacePoolState.BeforeOpen"
    )
    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        server.send_event(1, "source")


def test_set_broken():
    client, server = get_runspace_pair()

    server.set_broken(ErrorRecord(NETException("error"), ErrorCategoryInfo()))
    assert client.state == RunspacePoolState.Opened
    assert server.state == RunspacePoolState.Broken

    client.receive_data(server.data_to_send())
    assert server.data_to_send() is None

    state = client.next_event()
    assert isinstance(state, psrpcore.RunspacePoolStateEvent)
    assert state.state == RunspacePoolState.Broken
    assert isinstance(state.reason, ErrorRecord)
    assert str(state.reason) == "error"
    assert client.state == RunspacePoolState.Broken


def test_set_broken_invalid_state():
    server = psrpcore.ServerRunspacePool()

    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Broken, RunspacePoolState.Opened' to set as broken, "
        "current state is RunspacePoolState.BeforeOpen"
    )
    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        server.set_broken(ErrorRecord(NETException("error"), ErrorCategoryInfo()))


def test_host_call_invalid_state():
    server = psrpcore.ServerRunspacePool()

    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Opened' to create host call, "
        "current state is RunspacePoolState.BeforeOpen"
    )
    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        server.host_call(HostMethodIdentifier.Write1, ["test"])


def test_request_key_invalid_state():
    server = psrpcore.ServerRunspacePool()

    expected = re.escape(
        "Runspace Pool state must be one of 'RunspacePoolState.Opened' to request exchange key, "
        "current state is RunspacePoolState.BeforeOpen"
    )
    with pytest.raises(psrpcore.InvalidRunspacePoolState, match=expected):
        server.request_key()


def test_connect_invalid_runspace():
    client, server = get_runspace_pair()
    client2 = psrpcore.ClientRunspacePool(runspace_pool_id=uuid.UUID(int=0))
    client.disconnect()
    server.disconnect()

    client2.connect()
    server.connect()
    server.receive_data(client2.data_to_send())

    with pytest.raises(
        psrpcore.PSRPCoreError, match="Incoming connection is targeted towards a different Runspace Pool"
    ):
        server.next_event()


def test_start_pipeline():
    client, server = get_runspace_pair()
    ps = psrpcore.ClientPowerShell(client)
    ps.add_script("test")
    ps.start()

    pipeline = psrpcore.ServerPipeline(server, ps.pipeline_id)
    server.receive_data(client.data_to_send())
    create_pipe = server.next_event()
    assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
    assert create_pipe.pipeline_id == ps.pipeline_id
    assert isinstance(create_pipe.pipeline, PowerShell)
    assert pipeline.state == PSInvocationState.NotStarted

    pipeline.start()
    assert pipeline.state == PSInvocationState.Running

    client.receive_data(server.data_to_send())
    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.pipeline_id == ps.pipeline_id
    assert state.state == PSInvocationState.Running
    assert ps.state == PSInvocationState.Running

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.NotStarted, PSInvocationState.Stopped, "
        "PSInvocationState.Completed' to start a pipeline, current state is PSInvocationState.Running"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        pipeline.start()

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.NotStarted, PSInvocationState.Stopped, "
        "PSInvocationState.Stopping, PSInvocationState.Completed, PSInvocationState.Failed' to closing a pipeline, "
        "current state is PSInvocationState.Running"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        pipeline.close()

    pipeline.complete()
    assert pipeline.state == PSInvocationState.Completed

    client.receive_data(server.data_to_send())
    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.pipeline_id == ps.pipeline_id
    assert state.state == PSInvocationState.Completed
    assert ps.state == PSInvocationState.Completed

    # Start the pipeline again
    ps.start()
    server.receive_data(client.data_to_send())
    create_pipe = server.next_event()
    assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
    assert create_pipe.pipeline_id == ps.pipeline_id
    assert isinstance(create_pipe.pipeline, PowerShell)
    assert pipeline.state == PSInvocationState.Completed

    pipeline.start()
    assert pipeline.state == PSInvocationState.Running

    pipeline.complete()
    pipeline.close()
    assert pipeline.pipeline_id not in server.pipeline_table

    # Verify it doesn't fail if closing an already closed pipeline
    pipeline.close()


def test_stop_pipeline():
    client, server = get_runspace_pair()
    ps = psrpcore.ClientPowerShell(client)
    ps.add_script("test")
    ps.start()

    pipeline = psrpcore.ServerPipeline(server, ps.pipeline_id)
    server.receive_data(client.data_to_send())
    create_pipe = server.next_event()
    assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
    assert create_pipe.pipeline_id == ps.pipeline_id
    assert isinstance(create_pipe.pipeline, PowerShell)
    assert pipeline.state == PSInvocationState.NotStarted

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.Running' to stop a pipeline, current state is "
        "PSInvocationState.NotStarted"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        pipeline.stop()

    pipeline.start()
    assert pipeline.state == PSInvocationState.Running
    client.receive_data(server.data_to_send())
    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.pipeline_id == ps.pipeline_id
    assert state.state == PSInvocationState.Running
    assert ps.state == PSInvocationState.Running

    pipeline.stop()
    client.receive_data(server.data_to_send())
    pipe_state = client.next_event()
    assert isinstance(pipe_state, psrpcore.PipelineStateEvent)
    assert pipe_state.state == PSInvocationState.Stopped
    assert isinstance(pipe_state.reason, ErrorRecord)
    assert str(pipe_state.reason) == "The pipeline has been stopped."
    assert pipeline.state == PSInvocationState.Stopped
    assert ps.state == PSInvocationState.Stopped

    pipeline.stop()
    assert pipeline.state == PSInvocationState.Stopped
    assert server.data_to_send() is None

    # Run again from a stopped state
    ps.start()
    server.receive_data(client.data_to_send())
    create_pipe = server.next_event()
    assert isinstance(create_pipe, psrpcore.CreatePipelineEvent)
    assert create_pipe.pipeline_id == ps.pipeline_id
    assert isinstance(create_pipe.pipeline, PowerShell)
    assert pipeline.state == PSInvocationState.Stopped

    pipeline.start()
    client.receive_data(server.data_to_send())
    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == PSInvocationState.Running
    assert ps.state == PSInvocationState.Running

    pipeline.stop()
    client.receive_data(server.data_to_send())
    state = client.next_event()
    assert isinstance(state, psrpcore.PipelineStateEvent)
    assert state.state == PSInvocationState.Stopped
    assert ps.state == PSInvocationState.Stopped

    pipeline.close()
    assert pipeline.state == PSInvocationState.Stopped
    assert server.data_to_send() is None


def test_pipeline_host_call_invalid_state():
    client, server = get_runspace_pair()
    ps = psrpcore.ClientPowerShell(client)
    ps.add_script("test")
    ps.start()

    pipeline = psrpcore.ServerPipeline(server, ps.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.Running' to make a pipeline host call, current state is "
        "PSInvocationState.NotStarted"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        pipeline.host_call(HostMethodIdentifier.Write1, ["line"])


def test_pipeline_write_output_invalid_state():
    client, server = get_runspace_pair()
    ps = psrpcore.ClientPowerShell(client)
    ps.add_script("test")
    ps.start()

    pipeline = psrpcore.ServerPipeline(server, ps.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.Running' to write pipeline output, current state is "
        "PSInvocationState.NotStarted"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        pipeline.write_output("value")


def test_pipeline_write_error_invalid_state():
    client, server = get_runspace_pair()
    ps = psrpcore.ClientPowerShell(client)
    ps.add_script("test")
    ps.start()

    pipeline = psrpcore.ServerPipeline(server, ps.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.Running' to write pipeline error, current state is "
        "PSInvocationState.NotStarted"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        pipeline.write_error(NETException("error"))


def test_pipeline_write_debug_invalid_state():
    client, server = get_runspace_pair()
    ps = psrpcore.ClientPowerShell(client)
    ps.add_script("test")
    ps.start()

    pipeline = psrpcore.ServerPipeline(server, ps.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.Running' to write pipeline debug, current state is "
        "PSInvocationState.NotStarted"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        pipeline.write_debug("value")


def test_pipeline_write_verbose_invalid_state():
    client, server = get_runspace_pair()
    ps = psrpcore.ClientPowerShell(client)
    ps.add_script("test")
    ps.start()

    pipeline = psrpcore.ServerPipeline(server, ps.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.Running' to write pipeline verbose, current state is "
        "PSInvocationState.NotStarted"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        pipeline.write_verbose("value")


def test_pipeline_write_warning_invalid_state():
    client, server = get_runspace_pair()
    ps = psrpcore.ClientPowerShell(client)
    ps.add_script("test")
    ps.start()

    pipeline = psrpcore.ServerPipeline(server, ps.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.Running' to write pipeline warning, current state is "
        "PSInvocationState.NotStarted"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        pipeline.write_warning("value")


def test_pipeline_write_progress_invalid_state():
    client, server = get_runspace_pair()
    ps = psrpcore.ClientPowerShell(client)
    ps.add_script("test")
    ps.start()

    pipeline = psrpcore.ServerPipeline(server, ps.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.Running' to write pipeline progress, current state is "
        "PSInvocationState.NotStarted"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        pipeline.write_progress("activity", 1, "status")


def test_pipeline_information_invalid_protocol():
    client, server = get_runspace_pair()
    ps = psrpcore.ClientPowerShell(client)
    ps.add_script("test")
    ps.start()

    pipeline = psrpcore.ServerPipeline(server, ps.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()

    server.their_capability = None
    expected = re.escape("writing information record requires a protocol version of 2.3, current version is 2.0")
    with pytest.raises(psrpcore.InvalidProtocolVersion, match=expected):
        pipeline.write_information("message", "source")


def test_pipeline_information_invalid_state():
    client, server = get_runspace_pair()
    ps = psrpcore.ClientPowerShell(client)
    ps.add_script("test")
    ps.start()

    pipeline = psrpcore.ServerPipeline(server, ps.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()

    expected = re.escape(
        "Pipeline state must be one of 'PSInvocationState.Running' to write pipeline information, current state is "
        "PSInvocationState.NotStarted"
    )
    with pytest.raises(psrpcore.InvalidPipelineState, match=expected):
        pipeline.write_information("message", "source")


def test_pipeline_host_call():
    client, server = get_runspace_pair()

    c_pipeline = psrpcore.ClientPowerShell(client)
    # This is meant to be parsed by some engine and isn't actually read in this test
    # Just used to indicate a scenario where this would occur.
    c_pipeline.add_script('$host.UI.PromptForCredential("caption", "message", "username", "targetname")')
    c_pipeline.start()

    s_pipeline = psrpcore.ServerPipeline(server, c_pipeline.pipeline_id)
    server.receive_data(client.data_to_send())
    server.next_event()
    s_pipeline.start()

    client.receive_data(server.data_to_send())
    client.next_event()

    s_host = psrpcore.ServerHostRequestor(s_pipeline)
    s_host.prompt_for_credential("caption", "message", "username", "targetname")

    client.receive_data(server.data_to_send())
    host_call = client.next_event()
    assert isinstance(host_call, psrpcore.PipelineHostCallEvent)
    assert host_call.ci == 1
    assert host_call.method_identifier == HostMethodIdentifier.PromptForCredential1
    assert host_call.method_parameters == ["caption", "message", "username", "targetname"]

    c_host = psrpcore.ClientHostResponder(c_pipeline)
    c_host.prompt_for_credential(1, "prompt response")
    server.receive_data(client.data_to_send())
    host_response = server.next_event()
    assert isinstance(host_response, psrpcore.PipelineHostResponseEvent)
    assert host_response.ci == 1
    assert host_response.method_identifier == HostMethodIdentifier.PromptForCredential1
    assert host_response.result == "prompt response"
