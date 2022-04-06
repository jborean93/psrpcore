# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import xml.etree.ElementTree as ElementTree

import psrpcore.types._complex as complex
from psrpcore.types import PSChar, PSObject

from ..conftest import (
    COMPLEX_ENCODED_STRING,
    COMPLEX_STRING,
    assert_xml_diff,
    deserialize,
    serialize,
)


def test_ps_custom_object_empty():
    obj = complex.PSCustomObject()
    assert obj.PSTypeNames == ["System.Management.Automation.PSCustomObject", "System.Object"]

    obj.PSObject.to_string = "to string value"
    element = serialize(obj)

    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0"><T>System.Management.Automation.PSCustomObject</T><T>System.Object</T></TN>'
        "<ToString>to string value</ToString>"
        "</Obj>"
    )

    actual = deserialize(element)
    assert isinstance(actual, complex.PSCustomObject)
    assert actual.PSTypeNames == ["System.Management.Automation.PSCustomObject", "System.Object"]
    assert str(actual) == "to string value"
    assert repr(actual) == "PSCustomObject()"


def test_ps_custom_object_type_name():
    obj = complex.PSCustomObject(**{"PSTypeName": "MyType", "My Property": "Value"})
    assert obj.PSTypeNames == ["MyType", "System.Management.Automation.PSCustomObject", "System.Object"]

    obj.PSObject.to_string = "to string value"
    element = serialize(obj)

    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>MyType</T>"
        "<T>System.Management.Automation.PSCustomObject</T>"
        "<T>System.Object</T></TN>"
        '<MS><S N="My Property">Value</S></MS>'
        "<ToString>to string value</ToString>"
        "</Obj>"
    )

    actual = deserialize(element)
    assert isinstance(actual, PSObject)
    assert actual.PSTypeNames == [
        "Deserialized.MyType",
        "Deserialized.System.Management.Automation.PSCustomObject",
        "Deserialized.System.Object",
    ]
    assert str(actual) == "to string value"
    assert repr(actual) == "PSObject(My Property='Value')"


def test_ps_custom_object_properties():
    obj = complex.PSCustomObject(Foo="Bar", Hello="World")
    assert obj.PSTypeNames == ["System.Management.Automation.PSCustomObject", "System.Object"]

    element = serialize(obj)

    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0"><T>System.Management.Automation.PSCustomObject</T><T>System.Object</T></TN>'
        '<MS><S N="Foo">Bar</S><S N="Hello">World</S></MS>'
        "</Obj>"
    )

    actual = deserialize(element)
    assert isinstance(actual, complex.PSCustomObject)
    assert actual.PSTypeNames == ["System.Management.Automation.PSCustomObject", "System.Object"]
    assert str(actual) == "PSCustomObject(Foo='Bar', Hello='World')"
    assert repr(actual) == "PSCustomObject(Foo='Bar', Hello='World')"


def test_psrp_pipeline_result_types():
    value = complex.PipelineResultTypes.Output | complex.PipelineResultTypes.Error
    assert value.value == 3
    assert str(value) == "PipelineResultTypes.Warning"

    element = serialize(value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        "<I32>3</I32>"
        '<TN RefId="0">'
        "<T>System.Management.Automation.Runspaces.PipelineResultTypes</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>Output, Error, Warning</ToString>"
        "</Obj>"
    )

    value = deserialize(element)
    assert isinstance(value, complex.PipelineResultTypes)
    assert value == complex.PipelineResultTypes.Output | complex.PipelineResultTypes.Error


def test_console_color():
    value = complex.ConsoleColor.DarkRed
    assert value.value == 4
    assert str(value) == "ConsoleColor.DarkRed"

    element = serialize(value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        "<I32>4</I32>"
        '<TN RefId="0">'
        "<T>System.ConsoleColor</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>DarkRed</ToString>"
        "</Obj>"
    )

    value = deserialize(element)
    assert isinstance(value, complex.ConsoleColor)
    assert value == complex.ConsoleColor.DarkRed


def test_ps_thread_options():
    state = complex.PSThreadOptions.UseNewThread
    assert str(state) == "PSThreadOptions.UseNewThread"

    element = serialize(state)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        "<I32>1</I32>"
        '<TN RefId="0">'
        "<T>System.Management.Automation.Runspaces.PSThreadOptions</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>UseNewThread</ToString>"
        "</Obj>"
    )

    state = deserialize(element)
    assert isinstance(state, complex.PSThreadOptions)
    assert state == complex.PSThreadOptions.UseNewThread


def test_apartment_state():
    state = complex.ApartmentState.STA
    assert str(state) == "ApartmentState.STA"

    element = serialize(state)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        "<I32>0</I32>"
        '<TN RefId="0"><T>System.Threading.ApartmentState</T><T>System.Enum</T>'
        "<T>System.ValueType</T><T>System.Object</T></TN>"
        "<ToString>STA</ToString>"
        "</Obj>"
    )

    state = deserialize(element)
    assert isinstance(state, complex.ApartmentState)
    assert state == complex.ApartmentState.STA


def test_remote_stream_options():
    options = (
        complex.RemoteStreamOptions.AddInvocationInfoToDebugRecord
        | complex.RemoteStreamOptions.AddInvocationInfoToErrorRecord
    )
    assert str(options) == "RemoteStreamOptions.AddInvocationInfoToDebugRecord|AddInvocationInfoToErrorRecord"

    element = serialize(options)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        "<I32>5</I32>"
        '<TN RefId="0">'
        "<T>System.Management.Automation.RemoteStreamOptions</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>AddInvocationInfoToErrorRecord, AddInvocationInfoToDebugRecord</ToString>"
        "</Obj>"
    )

    options = deserialize(element)
    assert isinstance(options, complex.RemoteStreamOptions)
    assert (
        options
        == complex.RemoteStreamOptions.AddInvocationInfoToDebugRecord
        | complex.RemoteStreamOptions.AddInvocationInfoToErrorRecord
    )


def test_error_category():
    error = complex.ErrorCategory.CloseError
    assert str(error) == "ErrorCategory.CloseError"

    element = serialize(error)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        "<I32>2</I32>"
        '<TN RefId="0">'
        "<T>System.Management.Automation.ErrorCategory</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>CloseError</ToString>"
        "</Obj>"
    )

    error = deserialize(element)
    assert isinstance(error, complex.ErrorCategory)
    assert error == complex.ErrorCategory.CloseError


def test_error_record_plain():
    value = complex.ErrorRecord(
        Exception=complex.NETException("Exception"),
        CategoryInfo=complex.ErrorCategoryInfo(),
    )

    assert value.Exception.Message == "Exception"
    assert str(value) == "Exception"
    assert value.CategoryInfo.Category == complex.ErrorCategory.NotSpecified
    assert value.CategoryInfo.Activity is None
    assert value.CategoryInfo.Reason is None
    assert value.CategoryInfo.TargetName is None
    assert value.CategoryInfo.TargetType is None
    assert value.TargetObject is None
    assert value.FullyQualifiedErrorId is None
    assert value.InvocationInfo is None
    assert value.ErrorDetails is None
    assert value.PipelineIterationInfo is None
    assert value.ScriptStackTrace is None

    element = serialize(value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.ErrorRecord</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<MS>"
        '<Obj RefId="1" N="Exception">'
        '<TN RefId="1">'
        "<T>System.Exception</T>"
        "<T>System.Object</T>"
        "</TN><Props>"
        '<S N="Message">Exception</S>'
        '<Nil N="Data" />'
        '<Nil N="HelpLink" />'
        '<Nil N="HResult" />'
        '<Nil N="InnerException" />'
        '<Nil N="Source" />'
        '<Nil N="StackTrace" />'
        '<Nil N="TargetSite" />'
        "</Props></Obj>"
        '<Nil N="TargetObject" />'
        '<Nil N="FullyQualifiedErrorId" />'
        '<Nil N="InvocationInfo" />'
        '<I32 N="ErrorCategory_Category">0</I32>'
        '<Nil N="ErrorCategory_Activity" />'
        '<Nil N="ErrorCategory_Reason" />'
        '<Nil N="ErrorCategory_TargetName" />'
        '<Nil N="ErrorCategory_TargetType" />'
        '<S N="ErrorCategory_Message">NotSpecified (:) [], </S>'
        '<B N="SerializeExtendedInfo">false</B>'
        "</MS>"
        "<ToString>Exception</ToString>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    value = deserialize(element)

    assert isinstance(value, complex.ErrorRecord)
    assert value.serialize_extended_info is False
    assert value.Exception.Message == "Exception"
    assert str(value) == "Exception"
    assert isinstance(value.CategoryInfo, complex.ErrorCategoryInfo)
    assert value.CategoryInfo.Category == complex.ErrorCategory.NotSpecified
    assert value.CategoryInfo.Activity is None
    assert value.CategoryInfo.Reason is None
    assert value.CategoryInfo.TargetName is None
    assert value.CategoryInfo.TargetType is None
    assert value.TargetObject is None
    assert value.FullyQualifiedErrorId is None
    assert value.InvocationInfo is None
    assert value.ErrorDetails is None
    assert value.PipelineIterationInfo is None
    assert value.ScriptStackTrace is None


def test_error_record_with_error_details():
    value = complex.ErrorRecord(
        Exception=complex.NETException("Exception"),
        CategoryInfo=complex.ErrorCategoryInfo(
            Category=complex.ErrorCategory.CloseError,
            Activity="Closing a file",
            Reason="File is locked",
        ),
        TargetObject="C:\\temp\\file.txt",
        FullyQualifiedErrorId="CloseError",
        ErrorDetails=complex.ErrorDetails(
            Message="Error Detail Message",
        ),
        ScriptStackTrace="At <1>MyScript.ps1",
    )

    assert value.Exception.Message == "Exception"
    assert str(value) == "Error Detail Message"
    assert value.CategoryInfo.Category == complex.ErrorCategory.CloseError
    assert value.CategoryInfo.Activity == "Closing a file"
    assert value.CategoryInfo.Reason == "File is locked"
    assert value.CategoryInfo.TargetName is None
    assert value.CategoryInfo.TargetType is None
    assert value.TargetObject == "C:\\temp\\file.txt"
    assert value.FullyQualifiedErrorId == "CloseError"
    assert value.InvocationInfo is None
    assert value.ErrorDetails.Message == "Error Detail Message"
    assert value.ErrorDetails.RecommendedAction is None
    assert value.PipelineIterationInfo is None
    assert value.ScriptStackTrace == "At <1>MyScript.ps1"

    element = serialize(value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.ErrorRecord</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<MS>"
        '<Obj RefId="1" N="Exception">'
        '<TN RefId="1">'
        "<T>System.Exception</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<Props>"
        '<S N="Message">Exception</S>'
        '<Nil N="Data" />'
        '<Nil N="HelpLink" />'
        '<Nil N="HResult" />'
        '<Nil N="InnerException" />'
        '<Nil N="Source" />'
        '<Nil N="StackTrace" />'
        '<Nil N="TargetSite" />'
        "</Props>"
        "</Obj>"
        '<S N="TargetObject">C:\\temp\\file.txt</S>'
        '<S N="FullyQualifiedErrorId">CloseError</S>'
        '<Nil N="InvocationInfo" />'
        '<I32 N="ErrorCategory_Category">2</I32>'
        '<S N="ErrorCategory_Activity">Closing a file</S>'
        '<S N="ErrorCategory_Reason">File is locked</S>'
        '<Nil N="ErrorCategory_TargetName" />'
        '<Nil N="ErrorCategory_TargetType" />'
        '<S N="ErrorCategory_Message">CloseError (:) [Closing a file], File is locked</S>'
        '<S N="ErrorDetails_Message">Error Detail Message</S>'
        '<Nil N="ErrorDetails_RecommendedAction" />'
        '<S N="ErrorDetails_ScriptStackTrace">At &lt;1&gt;MyScript.ps1</S>'
        '<B N="SerializeExtendedInfo">false</B>'
        "</MS>"
        "<ToString>Error Detail Message</ToString>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    value = deserialize(element)

    assert isinstance(value, complex.ErrorRecord)
    assert value.serialize_extended_info is False
    assert value.Exception.Message == "Exception"
    assert str(value) == "Error Detail Message"
    assert value.CategoryInfo.Category == complex.ErrorCategory.CloseError
    assert value.CategoryInfo.Activity == "Closing a file"
    assert value.CategoryInfo.Reason == "File is locked"
    assert value.CategoryInfo.TargetName is None
    assert value.CategoryInfo.TargetType is None
    assert value.TargetObject == "C:\\temp\\file.txt"
    assert value.FullyQualifiedErrorId == "CloseError"
    assert value.InvocationInfo is None
    assert value.ErrorDetails.Message == "Error Detail Message"
    assert value.ErrorDetails.RecommendedAction is None
    assert value.PipelineIterationInfo is None
    assert value.ScriptStackTrace == "At <1>MyScript.ps1"


def test_error_record_with_invocation_info():
    value = complex.ErrorRecord(
        Exception=complex.NETException("Exception"),
        CategoryInfo=complex.ErrorCategoryInfo(),
        InvocationInfo=complex.InvocationInfo(
            BoundParameters=complex.PSDict(Path="C:\\temp\\file.txt"),
            CommandOrigin=complex.CommandOrigin.Runspace,
            ExpectingInput=False,
            HistoryId=10,
            InvocationName="Remove-Item",
            Line=10,
            OffsetInLine=20,
            PipelineLength=30,
            PipelinePosition=40,
            PositionMessage="position message",
            UnboundArguments=[True],
        ),
        PipelineIterationInfo=[1],
    )

    assert value.Exception.Message == "Exception"
    assert str(value) == "Exception"
    assert value.CategoryInfo.Category == complex.ErrorCategory.NotSpecified
    assert value.CategoryInfo.Activity is None
    assert value.CategoryInfo.Reason is None
    assert value.CategoryInfo.TargetName is None
    assert value.CategoryInfo.TargetType is None
    assert value.TargetObject is None
    assert value.FullyQualifiedErrorId is None
    assert value.InvocationInfo.BoundParameters == {"Path": "C:\\temp\\file.txt"}
    assert value.InvocationInfo.CommandOrigin == complex.CommandOrigin.Runspace
    assert value.InvocationInfo.DisplayScriptPosition is None
    assert value.InvocationInfo.ExpectingInput is False
    assert value.InvocationInfo.HistoryId == 10
    assert value.InvocationInfo.InvocationName == "Remove-Item"
    assert value.InvocationInfo.Line == "10"
    assert value.InvocationInfo.MyCommand is None
    assert value.InvocationInfo.OffsetInLine == 20
    assert value.InvocationInfo.PSCommandPath is None
    assert value.InvocationInfo.PSScriptRoot is None
    assert value.InvocationInfo.PipelineLength == 30
    assert value.InvocationInfo.PipelinePosition == 40
    assert value.InvocationInfo.PositionMessage == "position message"
    assert value.InvocationInfo.ScriptLineNumber is None
    assert value.InvocationInfo.ScriptName is None
    assert value.InvocationInfo.UnboundArguments == [True]
    assert value.ErrorDetails is None
    assert value.PipelineIterationInfo == [1]
    assert value.ScriptStackTrace is None

    element = serialize(value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.ErrorRecord</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<MS>"
        '<Obj RefId="1" N="Exception">'
        '<TN RefId="1"><T>System.Exception</T>'
        "<T>System.Object</T>"
        "</TN><Props>"
        '<S N="Message">Exception</S>'
        '<Nil N="Data" />'
        '<Nil N="HelpLink" />'
        '<Nil N="HResult" />'
        '<Nil N="InnerException" />'
        '<Nil N="Source" />'
        '<Nil N="StackTrace" />'
        '<Nil N="TargetSite" />'
        "</Props>"
        "</Obj>"
        '<Nil N="TargetObject" />'
        '<Nil N="FullyQualifiedErrorId" />'
        '<Obj RefId="2" N="InvocationInfo">'
        '<TN RefId="2">'
        "<T>System.Management.Automation.InvocationInfo</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<Props>"
        '<Obj RefId="3" N="BoundParameters">'
        '<TN RefId="3">'
        "<T>System.Collections.Hashtable</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<DCT>"
        '<En><S N="Key">Path</S><S N="Value">C:\\temp\\file.txt</S></En>'
        "</DCT>"
        "</Obj>"
        '<Obj RefId="4" N="CommandOrigin">'
        "<I32>0</I32>"
        '<TN RefId="4">'
        "<T>System.Management.Automation.CommandOrigin</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>Runspace</ToString>"
        "</Obj>"
        '<Nil N="DisplayScriptPosition" />'
        '<B N="ExpectingInput">false</B>'
        '<I64 N="HistoryId">10</I64>'
        '<S N="InvocationName">Remove-Item</S>'
        '<S N="Line">10</S>'
        '<Nil N="MyCommand" />'
        '<I32 N="OffsetInLine">20</I32>'
        '<I32 N="PipelineLength">30</I32>'
        '<I32 N="PipelinePosition">40</I32>'
        '<S N="PositionMessage">position message</S>'
        '<Nil N="PSCommandPath" />'
        '<Nil N="PSScriptRoot" />'
        '<Nil N="ScriptLineNumber" />'
        '<Nil N="ScriptName" />'
        '<Obj RefId="5" N="UnboundArguments">'
        '<TN RefId="5">'
        "<T>System.Collections.ArrayList</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<LST>"
        "<B>true</B>"
        "</LST>"
        "</Obj>"
        "</Props>"
        "</Obj>"
        '<I32 N="ErrorCategory_Category">0</I32'
        '><Nil N="ErrorCategory_Activity" />'
        '<Nil N="ErrorCategory_Reason" />'
        '<Nil N="ErrorCategory_TargetName" />'
        '<Nil N="ErrorCategory_TargetType" />'
        '<S N="ErrorCategory_Message">NotSpecified (:) [], </S>'
        '<B N="SerializeExtendedInfo">false</B>'
        "</MS>"
        "<ToString>Exception</ToString>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    value.serialize_extended_info = True
    element = serialize(value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.ErrorRecord</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<MS>"
        '<Obj RefId="1" N="Exception">'
        '<TN RefId="1">'
        "<T>System.Exception</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<Props>"
        '<S N="Message">Exception</S>'
        '<Nil N="Data" />'
        '<Nil N="HelpLink" />'
        '<Nil N="HResult" />'
        '<Nil N="InnerException" />'
        '<Nil N="Source" />'
        '<Nil N="StackTrace" />'
        '<Nil N="TargetSite" />'
        "</Props>"
        "</Obj>"
        '<Nil N="TargetObject" />'
        '<Nil N="FullyQualifiedErrorId" />'
        '<Obj RefId="2" N="InvocationInfo">'
        '<TN RefId="2">'
        "<T>System.Management.Automation.InvocationInfo</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<Props>"
        '<Obj RefId="3" N="BoundParameters">'
        '<TN RefId="3">'
        "<T>System.Collections.Hashtable</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<DCT>"
        '<En><S N="Key">Path</S><S N="Value">C:\\temp\\file.txt</S></En>'
        "</DCT>"
        "</Obj>"
        '<Obj RefId="4" N="CommandOrigin">'
        "<I32>0</I32>"
        '<TN RefId="4">'
        "<T>System.Management.Automation.CommandOrigin</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>Runspace</ToString>"
        "</Obj>"
        '<Nil N="DisplayScriptPosition" />'
        '<B N="ExpectingInput">false</B>'
        '<I64 N="HistoryId">10</I64>'
        '<S N="InvocationName">Remove-Item</S>'
        '<S N="Line">10</S>'
        '<Nil N="MyCommand" />'
        '<I32 N="OffsetInLine">20</I32>'
        '<I32 N="PipelineLength">30</I32>'
        '<I32 N="PipelinePosition">40</I32>'
        '<S N="PositionMessage">position message</S>'
        '<Nil N="PSCommandPath" />'
        '<Nil N="PSScriptRoot" />'
        '<Nil N="ScriptLineNumber" />'
        '<Nil N="ScriptName" />'
        '<Obj RefId="5" N="UnboundArguments">'
        '<TN RefId="5">'
        "<T>System.Collections.ArrayList</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<LST>"
        "<B>true</B>"
        "</LST>"
        "</Obj>"
        "</Props>"
        "</Obj>"
        '<I32 N="ErrorCategory_Category">0</I32>'
        '<Nil N="ErrorCategory_Activity" />'
        '<Nil N="ErrorCategory_Reason" />'
        '<Nil N="ErrorCategory_TargetName" />'
        '<Nil N="ErrorCategory_TargetType" />'
        '<S N="ErrorCategory_Message">NotSpecified (:) [], </S>'
        '<B N="SerializeExtendedInfo">true</B>'
        '<Obj RefId="6" N="InvocationInfo_BoundParameters">'
        '<TNRef RefId="3" />'
        "<DCT>"
        '<En><S N="Key">Path</S><S N="Value">C:\\temp\\file.txt</S></En>'
        "</DCT>"
        "</Obj>"
        '<Ref RefId="4" N="InvocationInfo_CommandOrigin" />'
        '<B N="InvocationInfo_ExpectingInput">false</B>'
        '<S N="InvocationInfo_InvocationName">Remove-Item</S>'
        '<S N="InvocationInfo_Line">10</S>'
        '<I32 N="InvocationInfo_OffsetInLine">20</I32>'
        '<I64 N="InvocationInfo_HistoryId">10</I64>'
        '<Obj RefId="7" N="InvocationInfo_PipelineIterationInfo">'
        '<TNRef RefId="5" />'
        "<LST />"
        "</Obj>"
        '<I32 N="InvocationInfo_PipelineLength">30</I32>'
        '<I32 N="InvocationInfo_PipelinePosition">40</I32>'
        '<Nil N="InvocationInfo_PSScriptRoot" />'
        '<Nil N="InvocationInfo_PSCommandPath" />'
        '<S N="InvocationInfo_PositionMessage">position message</S>'
        '<Nil N="InvocationInfo_ScriptLineNumber" />'
        '<Nil N="InvocationInfo_ScriptName" />'
        '<Obj RefId="8" N="InvocationInfo_UnboundArguments">'
        '<TNRef RefId="5" />'
        "<LST><B>true</B></LST>"
        '</Obj><B N="SerializeExtent">false</B>'
        '<Obj RefId="9" N="PipelineIterationInfo">'
        '<TNRef RefId="5" />'
        "<LST><I32>1</I32></LST>"
        "</Obj>"
        "</MS>"
        "<ToString>Exception</ToString>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    value = deserialize(element)

    assert isinstance(value, complex.ErrorRecord)
    assert str(value) == "Exception"
    assert value.serialize_extended_info is True
    assert value.Exception.Message == "Exception"

    # The exception contains the original invocation info and so doesn't have the re-computed values.
    assert isinstance(value.Exception.SerializedRemoteInvocationInfo, complex.InvocationInfo)
    assert value.Exception.SerializedRemoteInvocationInfo.PositionMessage == "position message"
    assert value.CategoryInfo.Category == complex.ErrorCategory.NotSpecified
    assert value.CategoryInfo.Activity is None
    assert value.CategoryInfo.Reason is None
    assert value.CategoryInfo.TargetName is None
    assert value.CategoryInfo.TargetType is None
    assert value.TargetObject is None
    assert value.FullyQualifiedErrorId is None
    assert value.InvocationInfo.BoundParameters == {"Path": "C:\\temp\\file.txt"}
    assert value.InvocationInfo.CommandOrigin == complex.CommandOrigin.Runspace

    display_script = value.InvocationInfo.DisplayScriptPosition
    assert isinstance(display_script, complex.ScriptExtent)
    assert display_script.StartOffset == 0
    assert display_script.StartLineNumber is None
    assert display_script.StartColumnNumber == 20
    assert display_script.EndOffset == 0
    assert display_script.EndLineNumber is None
    assert display_script.EndColumnNumber == 3
    assert display_script.File == ""
    assert display_script.Text == ""

    assert value.InvocationInfo.ExpectingInput is False
    assert value.InvocationInfo.HistoryId == 10
    assert value.InvocationInfo.InvocationName == "Remove-Item"
    assert value.InvocationInfo.Line == "10"
    assert value.InvocationInfo.MyCommand is None
    assert value.InvocationInfo.OffsetInLine == 20
    assert value.InvocationInfo.PSCommandPath == ""
    assert value.InvocationInfo.PSScriptRoot == ""
    assert value.InvocationInfo.PipelineLength == 30
    assert value.InvocationInfo.PipelinePosition == 40
    assert value.InvocationInfo.PositionMessage is None  # Haven't fully implemented these fields.
    assert value.InvocationInfo.ScriptLineNumber is None
    assert value.InvocationInfo.ScriptName is None
    assert value.InvocationInfo.UnboundArguments == [True]
    assert value.ErrorDetails is None
    assert value.PipelineIterationInfo == [1]
    assert value.ScriptStackTrace is None


def test_verbose_record_no_invocation_info():
    script_extent = complex.ScriptExtent(
        StartPosition=complex.ScriptPosition(
            File="my file",
            LineNumber=0,
            ColumnNumber=1,
            Line="my line",
        ),
        EndPosition=complex.ScriptPosition(
            File="my file",
            LineNumber=2,
            ColumnNumber=3,
            Line="my line",
        ),
    )
    invocation_info = complex.InvocationInfo(
        BoundParameters={"Param": "Value"},
        CommandOrigin=complex.CommandOrigin.Runspace,
        DisplayScriptPosition=script_extent,
        ExpectingInput=False,
        HistoryId=10,
        InvocationName="Invocation",
        Line=10,
        MyCommand=complex.PSCustomObject(
            CommandType=complex.CommandTypes.Function,
            Definition="command definition",
            Name="command name",
            Visibility=complex.SessionStateEntryVisibility.Private,
        ),
        OffsetInLine=2,
        PipelineLength=3,
        PipelinePosition=4,
        PSCommandPath="comand path",
        PSScriptRoot="script root",
        ScriptLineNumber=5,
        ScriptName="script name",
        UnboundArguments=["unbound", 1],
    )
    verbose = complex.VerboseRecord(
        Message="message",
        InvocationInfo=invocation_info,
        PipelineIterationInfo=[1, 2],
    )

    element = serialize(verbose)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.VerboseRecord</T>"
        "<T>System.Management.Automation.InformationalRecord</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<MS>"
        '<S N="InformationalRecord_Message">message</S>'
        '<B N="InformationalRecord_SerializeInvocationInfo">false</B>'
        "</MS>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    verbose = deserialize(element)
    assert isinstance(verbose, complex.VerboseRecord)
    assert verbose.Message == "message"
    assert verbose.InvocationInfo is None
    assert verbose.PipelineIterationInfo is None
    assert not verbose.serialize_extended_info


def test_verbose_record_invocation_info():
    script_extent = complex.ScriptExtent(
        StartPosition=complex.ScriptPosition(
            File="my file",
            LineNumber=0,
            ColumnNumber=1,
            Line="my line",
        ),
        EndPosition=complex.ScriptPosition(
            File="my file",
            LineNumber=2,
            ColumnNumber=3,
            Line="my line",
        ),
    )
    invocation_info = complex.InvocationInfo(
        BoundParameters={"Param": "Value"},
        CommandOrigin=complex.CommandOrigin.Runspace,
        DisplayScriptPosition=script_extent,
        ExpectingInput=False,
        HistoryId=10,
        InvocationName="Invocation",
        Line=10,
        MyCommand=complex.PSCustomObject(
            CommandType=complex.CommandTypes.Function,
            Definition="command definition",
            Name="command name",
            Visibility=complex.SessionStateEntryVisibility.Private,
        ),
        OffsetInLine=2,
        PipelineLength=3,
        PipelinePosition=4,
        PSCommandPath="comand path",
        PSScriptRoot="script root",
        ScriptLineNumber=5,
        ScriptName="script name",
        UnboundArguments=["unbound", 1],
    )
    verbose = complex.VerboseRecord(
        Message="message",
        InvocationInfo=invocation_info,
        PipelineIterationInfo=[1, 2],
    )
    verbose.serialize_extended_info = True

    element = serialize(verbose)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.VerboseRecord</T>"
        "<T>System.Management.Automation.InformationalRecord</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<MS>"
        '<S N="InformationalRecord_Message">message</S>'
        '<B N="InformationalRecord_SerializeInvocationInfo">true</B>'
        '<Obj RefId="1" N="InvocationInfo_BoundParameters">'
        '<TN RefId="1"><T>System.Collections.Hashtable</T><T>System.Object</T></TN>'
        '<DCT><En><S N="Key">Param</S><S N="Value">Value</S></En></DCT>'
        "</Obj>"
        '<Obj RefId="2" N="InvocationInfo_CommandOrigin">'
        "<I32>0</I32>"
        '<TN RefId="2">'
        "<T>System.Management.Automation.CommandOrigin</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN><ToString>Runspace</ToString>"
        "</Obj>"
        '<B N="InvocationInfo_ExpectingInput">false</B>'
        '<S N="InvocationInfo_InvocationName">Invocation</S>'
        '<S N="InvocationInfo_Line">10</S>'
        '<I32 N="InvocationInfo_OffsetInLine">2</I32>'
        '<I64 N="InvocationInfo_HistoryId">10</I64>'
        '<Obj RefId="3" N="InvocationInfo_PipelineIterationInfo">'
        '<TN RefId="3"><T>System.Collections.ArrayList</T><T>System.Object</T></TN>'
        "<LST />"
        '</Obj><I32 N="InvocationInfo_PipelineLength">3</I32>'
        '<I32 N="InvocationInfo_PipelinePosition">4</I32>'
        '<S N="InvocationInfo_PSScriptRoot">script root</S>'
        '<S N="InvocationInfo_PSCommandPath">comand path</S>'
        '<Nil N="InvocationInfo_PositionMessage" />'
        '<I32 N="InvocationInfo_ScriptLineNumber">5</I32>'
        '<S N="InvocationInfo_ScriptName">script name</S>'
        '<Obj RefId="4" N="InvocationInfo_UnboundArguments">'
        '<TNRef RefId="3" />'
        "<LST><S>unbound</S><I32>1</I32></LST>"
        "</Obj>"
        '<S N="ScriptExtent_File">my file</S>'
        '<I32 N="ScriptExtent_StartLineNumber">0</I32>'
        '<I32 N="ScriptExtent_StartColumnNumber">1</I32>'
        '<I32 N="ScriptExtent_EndLineNumber">2</I32>'
        '<I32 N="ScriptExtent_EndColumnNumber">3</I32>'
        '<B N="SerializeExtent">true</B>'
        '<Obj RefId="5" N="CommandInfo_CommandType">'
        "<I32>2</I32>"
        '<TN RefId="4">'
        "<T>System.Management.Automation.CommandTypes</T><T>System.Enum</T><T>System.ValueType</T><T>System.Object</T>"
        "</TN><ToString>Function</ToString>"
        "</Obj>"
        '<S N="CommandInfo_Definition">command definition</S>'
        '<S N="CommandInfo_Name">command name</S>'
        '<Obj RefId="6" N="CommandInfo_Visibility">'
        "<I32>1</I32>"
        '<TN RefId="5">'
        "<T>System.Management.Automation.SessionStateEntryVisibility</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN><ToString>Private</ToString>"
        "</Obj>"
        '<Obj RefId="7" N="InformationalRecord_PipelineIterationInfo">'
        '<TNRef RefId="3" />'
        "<LST><I32>1</I32><I32>2</I32></LST>"
        "</Obj>"
        "</MS>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    verbose = deserialize(element)
    assert isinstance(verbose, complex.VerboseRecord)
    assert verbose.Message == "message"

    invocation_info = verbose.InvocationInfo
    assert isinstance(invocation_info, complex.InvocationInfo)
    assert invocation_info.BoundParameters == {"Param": "Value"}
    assert invocation_info.CommandOrigin == complex.CommandOrigin.Runspace

    display_script = invocation_info.DisplayScriptPosition
    assert isinstance(display_script, complex.ScriptExtent)
    assert display_script.StartOffset == 0
    assert display_script.StartLineNumber == 0
    assert display_script.StartColumnNumber == 1
    assert display_script.EndOffset == 0
    assert display_script.EndLineNumber == 2
    assert display_script.EndColumnNumber == 3
    assert display_script.File == "my file"
    assert display_script.Text == "..."

    assert not invocation_info.ExpectingInput
    assert invocation_info.Line == "10"

    my_command = invocation_info.MyCommand
    assert isinstance(my_command, complex.RemoteCommandInfo)
    assert my_command.CommandType == complex.CommandTypes.Function
    assert my_command.Name == "command name"
    assert my_command.Definition == "command definition"
    assert my_command.Visibility == complex.SessionStateEntryVisibility.Private

    assert invocation_info.OffsetInLine == 2
    assert invocation_info.PipelineLength == 3
    assert invocation_info.PipelinePosition == 4
    assert invocation_info.PositionMessage is None
    assert invocation_info.PSCommandPath == ""
    assert invocation_info.PSScriptRoot == ""
    assert invocation_info.ScriptLineNumber == 5
    assert invocation_info.ScriptName == "script name"
    assert invocation_info.UnboundArguments == ["unbound", 1]

    assert verbose.PipelineIterationInfo == [1, 2]
    assert verbose.serialize_extended_info


def test_progress_record_defaults():
    record = complex.ProgressRecord(
        ActivityId=10,
        Activity=(COMPLEX_STRING + " - activity"),
        StatusDescription=(COMPLEX_STRING + " - status"),
    )
    element = serialize(record)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = (
        "<PR>"
        f"<AV>{COMPLEX_ENCODED_STRING} - activity</AV>"
        "<AI>10</AI>"
        "<Nil />"
        "<PI>-1</PI>"
        "<PC>-1</PC>"
        "<T>Processing</T>"
        "<SR>-1</SR>"
        f"<SD>{COMPLEX_ENCODED_STRING} - status</SD>"
        "</PR>"
    )
    assert actual == expected

    record = deserialize(element)
    assert isinstance(record, complex.ProgressRecord)
    assert record.ActivityId == 10
    assert record.Activity == COMPLEX_STRING + " - activity"
    assert record.StatusDescription == COMPLEX_STRING + " - status"
    assert record.CurrentOperation is None
    assert record.ParentActivityId == -1
    assert record.PercentComplete == -1
    assert record.RecordType == complex.ProgressRecordType.Processing
    assert record.SecondsRemaining == -1


def test_progress_record_explicit():
    record = complex.ProgressRecord(
        ActivityId=10,
        Activity=(COMPLEX_STRING + " - activity"),
        StatusDescription=(COMPLEX_STRING + " - status"),
        CurrentOperation=(COMPLEX_STRING + " - operation"),
        ParentActivityId=20,
        PercentComplete=100,
        RecordType=complex.ProgressRecordType.Completed,
        SecondsRemaining=0,
    )
    element = serialize(record)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = (
        "<PR>"
        f"<AV>{COMPLEX_ENCODED_STRING} - activity</AV>"
        "<AI>10</AI>"
        f"<S>{COMPLEX_ENCODED_STRING} - operation</S>"
        "<PI>20</PI>"
        "<PC>100</PC>"
        "<T>Completed</T>"
        "<SR>0</SR>"
        f"<SD>{COMPLEX_ENCODED_STRING} - status</SD>"
        "</PR>"
    )
    assert actual == expected

    record = deserialize(element)
    assert isinstance(record, complex.ProgressRecord)
    assert record.ActivityId == 10
    assert record.Activity == COMPLEX_STRING + " - activity"
    assert record.StatusDescription == COMPLEX_STRING + " - status"
    assert record.CurrentOperation == COMPLEX_STRING + " - operation"
    assert record.ParentActivityId == 20
    assert record.PercentComplete == 100
    assert record.RecordType == complex.ProgressRecordType.Completed
    assert record.SecondsRemaining == 0


def test_progress_record_missing_entry():
    data = "<PR><AV>activity</AV><AI>95</AI><PI /><SD>status</SD></PR>"
    record = deserialize(ElementTree.fromstring(data))

    assert isinstance(record, complex.ProgressRecord)
    assert record.ActivityId == 95
    assert record.Activity == "activity"
    assert record.StatusDescription == "status"
    assert record.CurrentOperation is None
    assert record.ParentActivityId == -1
    assert record.PercentComplete == -1
    assert record.RecordType == complex.ProgressRecordType.Processing
    assert record.SecondsRemaining == -1


def test_script_extent_text_no_end():
    extent = complex.ScriptExtent(
        StartPosition=complex.ScriptPosition(ColumnNumber=0), EndPosition=complex.ScriptPosition(ColumnNumber=0)
    )

    assert extent.Text == ""


def test_script_extent_text_same_line():
    extent = complex.ScriptExtent(
        StartPosition=complex.ScriptPosition(
            ColumnNumber=0,
            LineNumber=0,
            Line="test line",
        ),
        EndPosition=complex.ScriptPosition(
            ColumnNumber=6,
            LineNumber=0,
            Line="test line",
        ),
    )

    assert extent.Text == "test l"


def test_script_extent_text_multiple_lines():
    extent = complex.ScriptExtent(
        StartPosition=complex.ScriptPosition(
            ColumnNumber=2,
            LineNumber=0,
            Line="test line 2",
        ),
        EndPosition=complex.ScriptPosition(
            ColumnNumber=3,
            LineNumber=1,
            Line="test line 3",
        ),
    )

    assert extent.Text == "st line 2...t line 3"


def test_ps_primitive_dictionary():
    prim_dict = complex.PSPrimitiveDictionary(
        {
            "key": "value",
            "int key": 1,
            "casted": PSChar("a"),
        }
    )

    assert prim_dict["key"] == "value"
    assert prim_dict["int key"] == 1
    assert prim_dict["casted"] == 97
    assert isinstance(prim_dict["casted"], PSChar)

    element = serialize(prim_dict)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.PSPrimitiveDictionary</T>"
        "<T>System.Collections.Hashtable</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<DCT>"
        '<En><S N="Key">key</S><S N="Value">value</S></En>'
        '<En><S N="Key">int key</S><I32 N="Value">1</I32></En>'
        '<En><S N="Key">casted</S><C N="Value">97</C></En>'
        "</DCT>"
        "</Obj>"
    )

    prim_dict = deserialize(element)
    assert isinstance(prim_dict, complex.PSPrimitiveDictionary)
    assert isinstance(prim_dict, dict)
    assert prim_dict["key"] == "value"
    assert prim_dict["int key"] == 1
    assert prim_dict["casted"] == 97
    assert isinstance(prim_dict["casted"], PSChar)
