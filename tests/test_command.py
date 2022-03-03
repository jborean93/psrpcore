# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import re
from xml.etree import ElementTree

import pytest

import psrpcore
from psrpcore.types import PipelineResultTypes, PSObject, SessionCapability

from .conftest import assert_xml_diff, deserialize, serialize


@pytest.mark.parametrize(
    "kwds, expected",
    [
        ({"name": "name"}, "command_text='name' is_script=False use_local_scope=None end_of_statement=False"),
        (
            {"name": "name", "is_script": True},
            "command_text='name' is_script=True use_local_scope=None end_of_statement=False",
        ),
        (
            {"name": "name", "use_local_scope": False},
            "command_text='name' is_script=False use_local_scope=False end_of_statement=False",
        ),
    ],
    ids=["name only", "is_script", "use_local_scope"],
)
def test_command_repr(kwds, expected):
    cmd = psrpcore.Command(**kwds)
    assert repr(cmd) == f"<Command {expected}>"
    assert str(cmd) == kwds["name"]


def test_add_argument():
    cmd = psrpcore.Command("cmd")
    cmd.add_argument("str").add_argument(1)

    element = serialize(cmd)
    actual = ElementTree.tostring(element, method="xml", encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        "<MS>"
        '<S N="Cmd">cmd</S>'
        '<Obj RefId="1" N="Args">'
        '<TN RefId="0">'
        "<T>System.Collections.ArrayList</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<LST>"
        '<Obj RefId="2"><MS><Nil N="N" /><S N="V">str</S></MS></Obj>'
        '<Obj RefId="3">'
        "<MS>"
        '<Nil N="N" />'
        '<I32 N="V">1</I32>'
        "</MS>"
        "</Obj>"
        "</LST>"
        "</Obj>"
        '<B N="IsScript">false</B>'
        '<Nil N="UseLocalScope" />'
        '<Obj RefId="4" N="MergeMyResult">'
        "<I32>0</I32>"
        '<TN RefId="1">'
        "<T>System.Management.Automation.Runspaces.PipelineResultTypes</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>None</ToString>"
        "</Obj>"
        '<Ref RefId="4" N="MergeToResult" />'
        '<Ref RefId="4" N="MergePreviousResults" />'
        "</MS>"
        "<ToString>cmd</ToString>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    raw_cmd = deserialize(element)
    assert isinstance(raw_cmd, PSObject)
    assert not isinstance(raw_cmd, psrpcore.Command)

    cmd = psrpcore.Command.FromPSObjectForRemoting(raw_cmd)
    assert isinstance(cmd, psrpcore.Command)

    assert cmd.command_text == "cmd"
    assert not cmd.is_script
    assert cmd.use_local_scope is None
    assert cmd.parameters == [(None, "str"), (None, 1)]
    assert cmd.end_of_statement is False
    assert not cmd.merge_unclaimed
    assert cmd.merge_my == PipelineResultTypes.none
    assert cmd.merge_to == PipelineResultTypes.none
    assert cmd.merge_error == PipelineResultTypes.none
    assert cmd.merge_warning == PipelineResultTypes.none
    assert cmd.merge_verbose == PipelineResultTypes.none
    assert cmd.merge_debug == PipelineResultTypes.none
    assert cmd.merge_information == PipelineResultTypes.none


def test_add_parameter():
    cmd = psrpcore.Command("cmd")
    cmd.add_parameter("param1", "test").add_parameter("param2", True)
    cmd.redirect_error()
    cmd.redirect_information()

    element = serialize(
        cmd,
        their_capability=SessionCapability(
            PSVersion="2.0",
            protocolversion="2.3",
            SerializationVersion="1.1.0.1",
        ),
    )
    actual = ElementTree.tostring(element, method="xml", encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        "<MS>"
        '<S N="Cmd">cmd</S>'
        '<Obj RefId="1" N="Args">'
        '<TN RefId="0">'
        "<T>System.Collections.ArrayList</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<LST>"
        '<Obj RefId="2"><MS><S N="N">param1</S><S N="V">test</S></MS></Obj>'
        '<Obj RefId="3"><MS><S N="N">param2</S><B N="V">true</B></MS></Obj>'
        "</LST>"
        "</Obj>"
        '<B N="IsScript">false</B>'
        '<Nil N="UseLocalScope" />'
        '<Obj RefId="4" N="MergeMyResult">'
        "<I32>2</I32>"
        '<TN RefId="1">'
        "<T>System.Management.Automation.Runspaces.PipelineResultTypes</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>Error</ToString>"
        "</Obj>"
        '<Obj RefId="5" N="MergeToResult">'
        "<I32>1</I32>"
        '<TNRef RefId="1" />'
        "<ToString>Output</ToString>"
        "</Obj>"
        '<Obj RefId="6" N="MergePreviousResults">'
        "<I32>0</I32>"
        '<TNRef RefId="1" />'
        "<ToString>None</ToString>"
        "</Obj>"
        '<Ref RefId="5" N="MergeError" />'
        '<Ref RefId="6" N="MergeWarning" />'
        '<Ref RefId="6" N="MergeVerbose" />'
        '<Ref RefId="6" N="MergeDebug" />'
        '<Ref RefId="5" N="MergeInformation" />'
        "</MS>"
        "<ToString>cmd</ToString>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    raw_cmd = deserialize(element)
    assert isinstance(raw_cmd, PSObject)
    assert not isinstance(raw_cmd, psrpcore.Command)

    cmd = psrpcore.Command.FromPSObjectForRemoting(raw_cmd)
    assert isinstance(cmd, psrpcore.Command)

    assert cmd.command_text == "cmd"
    assert not cmd.is_script
    assert cmd.use_local_scope is None
    assert cmd.parameters == [("param1", "test"), ("param2", True)]
    assert cmd.end_of_statement is False
    assert not cmd.merge_unclaimed
    assert cmd.merge_my == PipelineResultTypes.Error
    assert cmd.merge_to == PipelineResultTypes.Output
    assert cmd.merge_error == PipelineResultTypes.Output
    assert cmd.merge_warning == PipelineResultTypes.none
    assert cmd.merge_verbose == PipelineResultTypes.none
    assert cmd.merge_debug == PipelineResultTypes.none
    assert cmd.merge_information == PipelineResultTypes.Output


def test_add_parameters():
    cmd = psrpcore.Command("cmd")
    cmd.add_parameters(param1="test", param2=True)
    cmd.redirect_error(PipelineResultTypes.Null)
    cmd.redirect_information(PipelineResultTypes.Null)

    element = serialize(
        cmd,
        their_capability=SessionCapability(
            PSVersion="2.0",
            protocolversion="2.2",
            SerializationVersion="1.1.0.1",
        ),
    )
    actual = ElementTree.tostring(element, method="xml", encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        "<MS>"
        '<S N="Cmd">cmd</S>'
        '<Obj RefId="1" N="Args">'
        '<TN RefId="0">'
        "<T>System.Collections.ArrayList</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<LST>"
        '<Obj RefId="2"><MS><S N="N">param1</S><S N="V">test</S></MS></Obj>'
        '<Obj RefId="3"><MS><S N="N">param2</S><B N="V">true</B></MS></Obj>'
        "</LST>"
        "</Obj>"
        '<B N="IsScript">false</B>'
        '<Nil N="UseLocalScope" />'
        '<Obj RefId="4" N="MergeMyResult">'
        "<I32>0</I32>"
        '<TN RefId="1">'
        "<T>System.Management.Automation.Runspaces.PipelineResultTypes</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>None</ToString>"
        "</Obj>"
        '<Ref RefId="4" N="MergeToResult" />'
        '<Ref RefId="4" N="MergePreviousResults" />'
        '<Obj RefId="5" N="MergeError">'
        "<I32>8</I32>"
        '<TNRef RefId="1" />'
        "<ToString>Null</ToString>"
        "</Obj>"
        '<Ref RefId="4" N="MergeWarning" />'
        '<Ref RefId="4" N="MergeVerbose" />'
        '<Ref RefId="4" N="MergeDebug" />'
        "</MS>"
        "<ToString>cmd</ToString>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    raw_cmd = deserialize(element)
    assert isinstance(raw_cmd, PSObject)
    assert not isinstance(raw_cmd, psrpcore.Command)

    cmd = psrpcore.Command.FromPSObjectForRemoting(raw_cmd)
    assert isinstance(cmd, psrpcore.Command)

    assert cmd.command_text == "cmd"
    assert not cmd.is_script
    assert cmd.use_local_scope is None
    assert cmd.parameters == [("param1", "test"), ("param2", True)]
    assert cmd.end_of_statement is False
    assert not cmd.merge_unclaimed
    assert cmd.merge_my == PipelineResultTypes.none
    assert cmd.merge_to == PipelineResultTypes.none
    assert cmd.merge_error == PipelineResultTypes.Null
    assert cmd.merge_warning == PipelineResultTypes.none
    assert cmd.merge_verbose == PipelineResultTypes.none
    assert cmd.merge_debug == PipelineResultTypes.none
    assert cmd.merge_information == PipelineResultTypes.none


def test_merge_unclaimed():
    cmd = psrpcore.Command("test")
    cmd.merge_unclaimed = True

    element = serialize(cmd)
    actual = ElementTree.tostring(element, method="xml", encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        "<MS>"
        '<S N="Cmd">test</S>'
        '<Obj RefId="1" N="Args">'
        '<TN RefId="0">'
        "<T>System.Collections.ArrayList</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<LST />"
        "</Obj>"
        '<B N="IsScript">false</B>'
        '<Nil N="UseLocalScope" />'
        '<Obj RefId="2" N="MergeMyResult">'
        "<I32>0</I32>"
        '<TN RefId="1">'
        "<T>System.Management.Automation.Runspaces.PipelineResultTypes</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>None</ToString>"
        "</Obj>"
        '<Ref RefId="2" N="MergeToResult" />'
        '<Obj RefId="3" N="MergePreviousResults">'
        "<I32>3</I32>"
        '<TNRef RefId="1" />'
        "<ToString>Output, Error, Warning</ToString>"
        "</Obj>"
        "</MS>"
        "<ToString>test</ToString>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    raw_cmd = deserialize(element)
    assert isinstance(raw_cmd, PSObject)
    assert not isinstance(raw_cmd, psrpcore.Command)

    cmd = psrpcore.Command.FromPSObjectForRemoting(raw_cmd)
    assert isinstance(cmd, psrpcore.Command)
    assert cmd.merge_unclaimed


def test_redirect_error():
    cmd = psrpcore.Command("test")

    cmd.redirect_all(PipelineResultTypes.Null)
    assert cmd.merge_my == PipelineResultTypes.none
    assert cmd.merge_to == PipelineResultTypes.none
    assert cmd.merge_error == PipelineResultTypes.Null
    assert cmd.merge_warning == PipelineResultTypes.Null
    assert cmd.merge_verbose == PipelineResultTypes.Null
    assert cmd.merge_verbose == PipelineResultTypes.Null
    assert cmd.merge_information == PipelineResultTypes.Null

    cmd.redirect_all(PipelineResultTypes.Output)
    assert cmd.merge_my == PipelineResultTypes.Error
    assert cmd.merge_to == PipelineResultTypes.Output
    assert cmd.merge_error == PipelineResultTypes.Output
    assert cmd.merge_warning == PipelineResultTypes.Output
    assert cmd.merge_verbose == PipelineResultTypes.Output
    assert cmd.merge_verbose == PipelineResultTypes.Output
    assert cmd.merge_information == PipelineResultTypes.Output

    cmd.redirect_all(PipelineResultTypes.none)
    assert cmd.merge_my == PipelineResultTypes.none
    assert cmd.merge_to == PipelineResultTypes.none
    assert cmd.merge_error == PipelineResultTypes.none
    assert cmd.merge_warning == PipelineResultTypes.none
    assert cmd.merge_verbose == PipelineResultTypes.none
    assert cmd.merge_verbose == PipelineResultTypes.none
    assert cmd.merge_information == PipelineResultTypes.none


def test_redirect_to_invalid_output():
    expected = re.escape("Invalid redirection stream, must be none, Output, or Null")

    with pytest.raises(ValueError, match=expected):
        psrpcore.Command("test").redirect_error(PipelineResultTypes.Verbose)
