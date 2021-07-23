# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import datetime
import xml.etree.ElementTree as ElementTree

import psrpcore.types._psrp as psrp
from psrpcore.types import (
    ApartmentState,
    DebugRecord,
    ErrorCategory,
    ErrorCategoryInfo,
    HostInfo,
    NETException,
    PSBool,
    PSDateTime,
    PSGuid,
    PSInt,
    PSInt64,
    PSObject,
    PSString,
    PSThreadOptions,
    PSVersion,
)

from ..conftest import assert_xml_diff, deserialize, serialize


def test_session_capability():
    ps_value = psrp.SessionCapability("1.2", "1.2.3", PSVersion("4.5.6.7"))
    assert ps_value.PSVersion == PSVersion("1.2")
    assert ps_value.protocolversion == PSVersion("1.2.3")
    assert ps_value.SerializationVersion == PSVersion("4.5.6.7")
    assert ps_value.TimeZone is None

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        "<MS>"
        '<Version N="PSVersion">1.2</Version>'
        '<Version N="protocolversion">1.2.3</Version>'
        '<Version N="SerializationVersion">4.5.6.7</Version>'
        "</MS>"
        "</Obj>"
    )

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.SessionCapability)
    assert ps_value.PSVersion == PSVersion("1.2")
    assert ps_value.protocolversion == PSVersion("1.2.3")
    assert ps_value.SerializationVersion == PSVersion("4.5.6.7")

    # Because we couldn't rehydrate the object there is no TimeZone property.
    assert len(ps_value.PSObject.extended_properties) == 3


def test_session_capability_with_timezone():
    ps_value = psrp.SessionCapability("1.2", "1.2.3", TimeZone=b"\x00\x01\x02\x03", SerializationVersion="4.5")
    assert ps_value.PSVersion == PSVersion("1.2")
    assert ps_value.protocolversion == PSVersion("1.2.3")
    assert ps_value.SerializationVersion == PSVersion("4.5")
    assert ps_value.TimeZone == b"\x00\x01\x02\x03"

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        "<MS>"
        '<Version N="PSVersion">1.2</Version>'
        '<Version N="protocolversion">1.2.3</Version>'
        '<Version N="SerializationVersion">4.5</Version>'
        '<BA N="TimeZone">AAECAw==</BA>'
        "</MS>"
        "</Obj>"
    )

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.SessionCapability)
    assert ps_value.PSVersion == PSVersion("1.2")
    assert ps_value.protocolversion == PSVersion("1.2.3")
    assert ps_value.SerializationVersion == PSVersion("4.5")
    assert ps_value.TimeZone == b"\x00\x01\x02\x03"
    assert len(ps_value.PSObject.extended_properties) == 4


def test_init_runspace_pool():
    ps_value = psrp.InitRunspacePool(
        1, 2, PSThreadOptions.UseNewThread, ApartmentState.STA, HostInfo(), {"key": "value"}
    )
    assert isinstance(ps_value, psrp.InitRunspacePool)
    assert ps_value.MinRunspaces == 1
    assert ps_value.MaxRunspaces == 2
    assert ps_value.PSThreadOptions == PSThreadOptions.UseNewThread
    assert ps_value.ApartmentState == ApartmentState.STA
    assert isinstance(ps_value.HostInfo, HostInfo)
    assert ps_value.HostInfo.IsHostNull
    assert ps_value.HostInfo.IsHostUINull
    assert ps_value.HostInfo.IsHostRawUINull
    assert ps_value.HostInfo.UseRunspaceHost
    assert ps_value.HostInfo.HostDefaultData is None
    assert ps_value.ApplicationArguments == {"key": "value"}

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        "<MS>"
        '<I32 N="MinRunspaces">1</I32>'
        '<I32 N="MaxRunspaces">2</I32>'
        '<Obj RefId="1" N="PSThreadOptions">'
        "<I32>1</I32>"
        '<TN RefId="0">'
        "<T>System.Management.Automation.Runspaces.PSThreadOptions</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>UseNewThread</ToString>"
        "</Obj"
        '><Obj RefId="2" N="ApartmentState">'
        "<I32>0</I32>"
        '<TN RefId="1">'
        "<T>System.Threading.ApartmentState</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>STA</ToString>"
        "</Obj>"
        '<Obj RefId="3" N="HostInfo">'
        "<MS>"
        '<B N="_isHostNull">true</B>'
        '<B N="_isHostUINull">true</B>'
        '<B N="_isHostRawUINull">true</B>'
        '<B N="_useRunspaceHost">true</B>'
        "</MS>"
        "</Obj>"
        '<Obj RefId="4" N="ApplicationArguments">'
        '<TN RefId="2">'
        "<T>System.Management.Automation.PSPrimitiveDictionary</T>"
        "<T>System.Collections.Hashtable</T>"
        "<T>System.Object</T>"
        "</TN>"
        '<DCT><En><S N="Key">key</S><S N="Value">value</S></En></DCT>'
        "</Obj>"
        "</MS>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.InitRunspacePool)
    assert ps_value.MinRunspaces == 1
    assert ps_value.MaxRunspaces == 2
    assert ps_value.PSThreadOptions == PSThreadOptions.UseNewThread
    assert ps_value.ApartmentState == ApartmentState.STA
    assert ps_value.HostInfo._isHostUINull
    assert ps_value.HostInfo._isHostRawUINull
    assert ps_value.HostInfo._useRunspaceHost
    assert not hasattr(ps_value.HostInfo, "_hostDefaultData")
    assert ps_value.ApplicationArguments == {"key": "value"}


def test_public_key():
    ps_value = psrp.PublicKey("test")
    assert isinstance(ps_value, psrp.PublicKey)
    assert ps_value.PublicKey == "test"
    assert isinstance(ps_value.PublicKey, PSString)

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert actual == '<Obj RefId="0"><MS><S N="PublicKey">test</S></MS></Obj>'

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.PublicKey)
    assert isinstance(ps_value.PublicKey, PSString)
    assert ps_value.PublicKey == "test"


def test_encrypted_session_key():
    ps_value = psrp.EncryptedSessionKey("test")
    assert isinstance(ps_value, psrp.EncryptedSessionKey)
    assert ps_value.EncryptedSessionKey == "test"
    assert isinstance(ps_value.EncryptedSessionKey, PSString)

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert actual == '<Obj RefId="0"><MS><S N="EncryptedSessionKey">test</S></MS></Obj>'

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.EncryptedSessionKey)
    assert isinstance(ps_value.EncryptedSessionKey, PSString)
    assert ps_value.EncryptedSessionKey == "test"


def test_public_key_request():
    ps_value = psrp.PublicKeyRequest()
    assert isinstance(ps_value, psrp.PublicKeyRequest)
    assert ps_value == ""

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert actual == "<S />"

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSString)
    assert not isinstance(ps_value, psrp.EncryptedSessionKey)
    assert ps_value == ""


def test_set_max_runspaces():
    ps_value = psrp.SetMaxRunspaces(10, -20)
    assert isinstance(ps_value, psrp.SetMaxRunspaces)
    assert ps_value.MaxRunspaces == 10
    assert ps_value.ci == -20

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert actual == '<Obj RefId="0">' "<MS>" '<I32 N="MaxRunspaces">10</I32>' '<I64 N="ci">-20</I64>' "</MS>" "</Obj>"

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.SetMaxRunspaces)
    assert isinstance(ps_value.MaxRunspaces, PSInt)
    assert ps_value.MaxRunspaces == 10
    assert isinstance(ps_value.ci, PSInt64)
    assert ps_value.ci == -20


def test_set_min_runspaces():
    ps_value = psrp.SetMinRunspaces(10, -20)
    assert isinstance(ps_value, psrp.SetMinRunspaces)
    assert ps_value.MinRunspaces == 10
    assert ps_value.ci == -20

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert actual == '<Obj RefId="0">' "<MS>" '<I32 N="MinRunspaces">10</I32>' '<I64 N="ci">-20</I64>' "</MS>" "</Obj>"

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.SetMinRunspaces)
    assert isinstance(ps_value.MinRunspaces, PSInt)
    assert ps_value.MinRunspaces == 10
    assert isinstance(ps_value.ci, PSInt64)
    assert ps_value.ci == -20


def tet_runspace_availability_bool():
    ps_value = psrp.RunspaceAvailability(True, 50)
    assert isinstance(ps_value, psrp.RunspaceAvailability)
    assert ps_value.SetMinMaxRunspacesResponse is True
    assert ps_value.ci == 50

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        "<MS>"
        '<B N="SetMinMaxRunspacesResponse">true</B>'
        '<I64 N="ci">50</I64>'
        "</MS>"
        "</Obj>"
    )

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.RunspaceAvailability)
    assert isinstance(ps_value.SetMinMaxRunspacesResponse, PSBool)
    assert ps_value.SetMinMaxRunspacesResponse is True
    assert isinstance(ps_value.ci, PSInt64)
    assert ps_value.ci == 50


def tet_runspace_availability_long():
    ps_value = psrp.RunspaceAvailability(PSInt64(10), 50)
    assert isinstance(ps_value, psrp.RunspaceAvailability)
    assert ps_value.SetMinMaxRunspacesResponse == 10
    assert ps_value.ci == 50

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        "<MS>"
        '<I64 N="SetMinMaxRunspacesResponse">10</I64>'
        '<I64 N="ci">50</I64>'
        "</MS>"
        "</Obj>"
    )

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.RunspaceAvailability)
    assert isinstance(ps_value.SetMinMaxRunspacesResponse, PSInt64)
    assert ps_value.SetMinMaxRunspacesResponse == 10
    assert isinstance(ps_value.ci, PSInt64)
    assert ps_value.ci == 50


def test_runspace_pool_state():
    ps_value = psrp.RunspacePoolStateMsg(1)
    assert ps_value.RunspaceState == 1
    assert isinstance(ps_value.RunspaceState, PSInt)
    assert ps_value.ExceptionAsErrorRecord is None

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert actual == '<Obj RefId="0"><MS><I32 N="RunspaceState">1</I32></MS></Obj>'

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.RunspacePoolStateMsg)
    assert ps_value.RunspaceState == 1
    assert isinstance(ps_value.RunspaceState, PSInt)
    assert not hasattr(ps_value, "ExceptionAsErrorRecord")
    assert len(ps_value.PSObject.extended_properties) == 1


def test_user_event():
    ps_value = psrp.UserEvent(
        EventIdentifier=1,
        SourceIdentifier="source id",
        TimeGenerated=PSDateTime(1970, 1, 1),
        Sender="sender",
        SourceArgs="source args",
        MessageData="message data",
        ComputerName="computer name",
        RunspaceId=PSGuid("85ba13fb-6804-47f0-861a-8fe0ceb04acd"),
    )
    assert ps_value.EventIdentifier == 1
    assert ps_value.SourceIdentifier == "source id"
    assert ps_value.TimeGenerated == PSDateTime(1970, 1, 1)
    assert ps_value.Sender == "sender"
    assert ps_value.SourceArgs == "source args"
    assert ps_value.MessageData == "message data"
    assert ps_value.ComputerName == "computer name"
    assert ps_value.RunspaceId == PSGuid("85ba13fb-6804-47f0-861a-8fe0ceb04acd")

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        "<MS>"
        '<I32 N="PSEventArgs.EventIdentifier">1</I32>'
        '<S N="PSEventArgs.SourceIdentifier">source id</S>'
        '<DT N="PSEventArgs.TimeGenerated">1970-01-01T00:00:00Z</DT>'
        '<S N="PSEventArgs.Sender">sender</S>'
        '<S N="PSEventArgs.SourceArgs">source args</S>'
        '<S N="PSEventArgs.MessageData">message data</S>'
        '<S N="PSEventArgs.ComputerName">computer name</S>'
        '<G N="PSEventArgs.RunspaceId">85ba13fb-6804-47f0-861a-8fe0ceb04acd</G>'
        "</MS>"
        "</Obj>"
    )

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.UserEvent)
    assert ps_value["PSEventArgs.EventIdentifier"] == 1
    assert ps_value["PSEventArgs.SourceIdentifier"] == "source id"
    assert ps_value["PSEventArgs.TimeGenerated"] == PSDateTime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    assert ps_value["PSEventArgs.Sender"] == "sender"
    assert ps_value["PSEventArgs.SourceArgs"] == "source args"
    assert ps_value["PSEventArgs.MessageData"] == "message data"
    assert ps_value["PSEventArgs.ComputerName"] == "computer name"
    assert ps_value["PSEventArgs.RunspaceId"] == PSGuid("85ba13fb-6804-47f0-861a-8fe0ceb04acd")


def test_connect_runspace_pool():
    ps_value = psrp.ConnectRunspacePool(1, 2)

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = '<Obj RefId="0"><MS><I32 N="MinRunspaces">1</I32><I32 N="MaxRunspaces">2</I32></MS></Obj>'
    assert actual == expected

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.UserEvent)
    assert ps_value.MinRunspaces == 1
    assert ps_value.MaxRunspaces == 2


def test_connect_runspace_pool_empty():
    ps_value = psrp.ConnectRunspacePool()

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = "<S />"
    assert actual == expected

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.UserEvent)
    assert isinstance(ps_value, PSString)
    assert ps_value == ""


def test_error_record():
    ps_value = psrp.ErrorRecordMsg(
        Exception=NETException(Message="exception message"),
        CategoryInfo=ErrorCategoryInfo(),
    )

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        '<TN RefId="0"><T>System.Management.Automation.ErrorRecord</T><T>System.Object</T></TN>'
        "<MS>"
        '<Obj RefId="1" N="Exception">'
        '<TN RefId="1"><T>System.Exception</T><T>System.Object</T></TN>'
        '<Props><S N="Message">exception message</S>'
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
        '<Nil N="InvocationInfo" />'
        '<I32 N="ErrorCategory_Category">0</I32>'
        '<Nil N="ErrorCategory_Activity" />'
        '<Nil N="ErrorCategory_Reason" />'
        '<Nil N="ErrorCategory_TargetName" />'
        '<Nil N="ErrorCategory_TargetType" />'
        '<S N="ErrorCategory_Message">NotSpecified (:) [], </S>'
        '<B N="SerializeExtendedInfo">false</B>'
        "</MS>"
        "<ToString>exception message</ToString>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.ErrorRecordMsg)
    assert isinstance(ps_value, psrp.ErrorRecord)
    assert isinstance(ps_value.Exception, NETException)
    assert ps_value.Exception.Message == "exception message"
    assert ps_value.CategoryInfo.Category == ErrorCategory.NotSpecified
    assert ps_value.CategoryInfo.Activity is None
    assert ps_value.CategoryInfo.Reason is None
    assert ps_value.CategoryInfo.TargetName is None
    assert ps_value.CategoryInfo.TargetType is None
    assert ps_value.TargetObject is None
    assert ps_value.FullyQualifiedErrorId is None
    assert ps_value.InvocationInfo is None
    assert ps_value.ErrorDetails is None
    assert ps_value.PipelineIterationInfo is None
    assert ps_value.ScriptStackTrace is None


def test_debug_record():
    ps_value = psrp.DebugRecordMsg("msg")
    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.DebugRecord</T>"
        "<T>System.Management.Automation.InformationalRecord</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<MS>"
        '<S N="InformationalRecord_Message">msg</S>'
        '<B N="InformationalRecord_SerializeInvocationInfo">false</B>'
        "</MS>"
        "</Obj>"
    )
    assert actual == expected

    ps_value = deserialize(element)

    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.DebugRecordMsg)
    assert isinstance(ps_value, DebugRecord)
    assert ps_value.Message == "msg"
    assert ps_value.InvocationInfo is None
    assert ps_value.PipelineIterationInfo is None


def test_information_record():
    ps_value = psrp.InformationRecordMsg(MessageData=1, Source="source")

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8", method="xml").decode()
    expected = (
        '<Obj RefId="0">'
        "<MS>"
        '<I32 N="MessageData">1</I32>'
        '<S N="Source">source</S>'
        '<Nil N="TimeGenerated" />'
        '<Nil N="Tags" />'
        '<Nil N="User" />'
        '<Nil N="Computer" />'
        '<Nil N="ProcessId" />'
        '<Nil N="NativeThreadId" />'
        '<Nil N="ManagedThreadId" />'
        "</MS>"
        "</Obj>"
    )
    assert actual == expected

    ps_value = deserialize(element)
    assert isinstance(ps_value, PSObject)
    assert not isinstance(ps_value, psrp.InformationRecordMsg)
    assert isinstance(ps_value, PSObject)
    assert ps_value.MessageData == 1
    assert ps_value.Source == "source"
    assert ps_value.TimeGenerated is None
    assert ps_value.Tags is None
    assert ps_value.User is None
    assert ps_value.Computer is None
    assert ps_value.ProcessId is None
    assert ps_value.NativeThreadId is None
    assert ps_value.ManagedThreadId is None
