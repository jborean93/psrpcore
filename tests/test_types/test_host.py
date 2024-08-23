# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import xml.etree.ElementTree as ElementTree

import psrpcore.types._host as host
from psrpcore.types import ConsoleColor, PSChar, PSObject

from ..conftest import assert_xml_diff, deserialize, serialize


def test_buffer_cell():
    value = host.BufferCell(97, ConsoleColor.White, ConsoleColor.Black, host.BufferCellType.Leading)
    assert value.Character == PSChar("a")
    assert value.ForegroundColor == ConsoleColor.White
    assert value.BackgroundColor == ConsoleColor.Black
    assert value.BufferCellType == host.BufferCellType.Leading

    element = serialize(value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.Host.BufferCell</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<Props>"
        '<C N="Character">97</C>'
        '<Obj RefId="1" N="ForegroundColor">'
        "<I32>15</I32>"
        '<TN RefId="1">'
        "<T>System.ConsoleColor</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>White</ToString>"
        "</Obj>"
        '<Obj RefId="2" N="BackgroundColor"><I32>0</I32><TNRef RefId="1" /><ToString>Black</ToString></Obj>'
        '<Obj RefId="3" N="BufferCellType">'
        "<I32>1</I32>"
        '<TN RefId="2">'
        "<T>System.Management.Automation.Host.ControlKeyStates</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>Leading</ToString>"
        "</Obj>"
        "</Props>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    value = deserialize(element)
    assert isinstance(value, PSObject)
    assert isinstance(value, host.BufferCell)
    assert value.Character == PSChar("a")
    assert value.ForegroundColor == ConsoleColor.White
    assert value.BackgroundColor == ConsoleColor.Black
    assert value.BufferCellType == host.BufferCellType.Leading

    assert host.BufferCell.FromPSObjectForRemoting(value) is value


def test_choice_description():
    value = host.ChoiceDescription("label", "help")
    assert value.Label == "label"
    assert value.HelpMessage == "help"

    element = serialize(value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert_xml_diff(
        actual,
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.Host.ChoiceDescription</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<Props>"
        '<S N="Label">label</S>'
        '<S N="HelpMessage">help</S>'
        "</Props>"
        "</Obj>",
    )

    value = deserialize(element)
    assert isinstance(value, PSObject)
    assert isinstance(value, host.ChoiceDescription)
    assert value.Label == "label"
    assert value.HelpMessage == "help"

    assert host.ChoiceDescription.FromPSObjectForRemoting(value) is value


def test_coordinates():
    value = host.Coordinates(10, 412)
    assert value.X == 10
    assert value.Y == 412

    element = serialize(value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert_xml_diff(
        actual,
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.Host.Coordinates</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<Props>"
        '<I32 N="X">10</I32>'
        '<I32 N="Y">412</I32>'
        "</Props>"
        "</Obj>",
    )

    value = deserialize(element)
    assert isinstance(value, PSObject)
    assert isinstance(value, host.Coordinates)
    assert value.X == 10
    assert value.Y == 412

    assert host.Coordinates.FromPSObjectForRemoting(value) is value


def test_field_description():
    value = host.FieldDescription("name")
    assert value.Name == "name"
    assert value.ParameterTypeName is None
    assert value.ParameterTypeFullName is None
    assert value.ParameterAssemblyFullName is None
    assert value.Label == ""
    assert value.HelpMessage == ""
    assert value.IsMandatory is True
    assert value.DefaultValue is None
    assert value.Attributes is None

    element = serialize(value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert_xml_diff(
        actual,
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.Host.FieldDescription</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<Props>"
        '<S N="Name">name</S>'
        '<Nil N="ParameterTypeName" />'
        '<Nil N="ParameterTypeFullName" />'
        '<Nil N="ParameterAssemblyFullName" />'
        '<S N="Label" />'
        '<S N="HelpMessage" />'
        '<B N="IsMandatory">true</B>'
        '<Nil N="DefaultValue" />'
        '<Nil N="Attributes" />'
        "</Props>"
        "</Obj>",
    )

    value = deserialize(element)
    assert isinstance(value, PSObject)
    assert isinstance(value, host.FieldDescription)
    assert value.ParameterTypeName is None
    assert value.ParameterTypeFullName is None
    assert value.ParameterAssemblyFullName is None
    assert value.Label == ""
    assert value.HelpMessage == ""
    assert value.IsMandatory is True
    assert value.DefaultValue is None
    assert value.Attributes is None

    assert host.FieldDescription.FromPSObjectForRemoting(value) is value


def test_key_info():
    value = host.KeyInfo(10, 97, host.ControlKeyStates.EnhancedKey, False)
    assert value.VirtualKeyCode == 10
    assert value.Character == PSChar("a")
    assert value.ControlKeyState == host.ControlKeyStates.EnhancedKey
    assert value.KeyDown is False

    element = serialize(value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert_xml_diff(
        actual,
        (
            '<Obj RefId="0">'
            '<TN RefId="0">'
            "<T>System.Management.Automation.Host.KeyInfo</T>"
            "<T>System.Object</T>"
            "</TN>"
            "<Props>"
            '<I32 N="VirtualKeyCode">10</I32>'
            '<C N="Character">97</C>'
            '<Obj RefId="1" N="ControlKeyState">'
            "<I32>256</I32>"
            '<TN RefId="1">'
            "<T>System.Management.Automation.Host.ControlKeyStates</T>"
            "<T>System.Enum</T>"
            "<T>System.ValueType</T>"
            "<T>System.Object</T>"
            "</TN>"
            "<ToString>EnhancedKey</ToString>"
            "</Obj>"
            '<B N="KeyDown">false</B>'
            "</Props>"
            "</Obj>"
        ),
    )

    value = deserialize(element)
    assert isinstance(value, PSObject)
    assert isinstance(value, host.KeyInfo)
    assert value.VirtualKeyCode == 10
    assert value.Character == PSChar("a")
    assert value.ControlKeyState == host.ControlKeyStates.EnhancedKey
    assert value.KeyDown is False

    assert host.KeyInfo.FromPSObjectForRemoting(value) is value


def test_rectangle():
    value = host.Rectangle(1, 2, 3, 4)
    assert value.Left == 1
    assert value.Top == 2
    assert value.Right == 3
    assert value.Bottom == 4

    element = serialize(value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert_xml_diff(
        actual,
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.Host.Rectangle</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<Props>"
        '<I32 N="Left">1</I32>'
        '<I32 N="Top">2</I32>'
        '<I32 N="Right">3</I32>'
        '<I32 N="Bottom">4</I32>'
        "</Props>"
        "</Obj>",
    )

    value = deserialize(element)
    assert isinstance(value, PSObject)
    assert isinstance(value, host.Rectangle)
    assert value.Left == 1
    assert value.Top == 2
    assert value.Right == 3
    assert value.Bottom == 4

    assert host.Rectangle.FromPSObjectForRemoting(value) is value


def test_size():
    value = host.Size(10, 412)
    assert value.Width == 10
    assert value.Height == 412

    element = serialize(value)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert_xml_diff(
        actual,
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.Host.Size</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<Props>"
        '<I32 N="Width">10</I32>'
        '<I32 N="Height">412</I32>'
        "</Props>"
        "</Obj>",
    )

    value = deserialize(element)
    assert isinstance(value, PSObject)
    assert isinstance(value, host.Size)
    assert value.Width == 10
    assert value.Height == 412

    assert host.Size.FromPSObjectForRemoting(value) is value
