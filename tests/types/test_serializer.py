# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import datetime
import decimal
import enum
import queue
import re
import uuid
import xml.etree.ElementTree as ElementTree

import pytest

import psrpcore.types._serializer as serializer
from psrpcore.types import (
    PSBool,
    PSByte,
    PSByteArray,
    PSChar,
    PSCustomObject,
    PSDateTime,
    PSDecimal,
    PSDouble,
    PSDuration,
    PSGuid,
    PSInt,
    PSInt16,
    PSInt64,
    PSQueue,
    PSSByte,
    PSScriptBlock,
    PSSingle,
    PSString,
    PSUInt,
    PSUInt16,
    PSUInt64,
    PSUri,
    PSVersion,
    PSXml,
)

from ..conftest import (
    COMPLEX_ENCODED_STRING,
    COMPLEX_STRING,
    FakeCryptoProvider,
    assert_xml_diff,
)

# A lot of the serializer tests are done in the tests for each object, these are just for extra edge cases we want to
# validate


@pytest.mark.parametrize(
    "input_value, expected",
    [
        (PSBool(True), "<B>true</B>"),
        (PSBool(False), "<B>false</B>"),
        (True, "<B>true</B>"),
        (False, "<B>false</B>"),
        (PSByte(1), "<By>1</By>"),
        (PSByteArray(b"\x00\x01\x02\x03"), "<BA>AAECAw==</BA>"),
        (b"\x00\x01\x02\x03", "<BA>AAECAw==</BA>"),
        (PSChar("a"), "<C>97</C>"),
        (PSDateTime(1970, 1, 1), "<DT>1970-01-01T00:00:00Z</DT>"),
        (datetime.datetime(1970, 1, 1), "<DT>1970-01-01T00:00:00Z</DT>"),
        (PSDecimal(1), "<D>1</D>"),
        (decimal.Decimal(1), "<D>1</D>"),
        (PSDouble(1.0), "<Db>1.0</Db>"),
        (PSDuration(1), "<TS>P1D</TS>"),
        (datetime.timedelta(1), "<TS>P1D</TS>"),
        (PSGuid(int=0), "<G>00000000-0000-0000-0000-000000000000</G>"),
        (uuid.UUID(int=0), "<G>00000000-0000-0000-0000-000000000000</G>"),
        (PSInt(1), "<I32>1</I32>"),
        (1, "<I32>1</I32>"),
        (PSInt16(1), "<I16>1</I16>"),
        (PSInt64(1), "<I64>1</I64>"),
        (PSSingle(1.0), "<Sg>1.0</Sg>"),
        (float(1.0), "<Sg>1.0</Sg>"),
        (PSSByte(1), "<SB>1</SB>"),
        (PSScriptBlock(COMPLEX_STRING), f"<SBK>{COMPLEX_ENCODED_STRING}</SBK>"),
        (PSString(COMPLEX_STRING), f"<S>{COMPLEX_ENCODED_STRING}</S>"),
        (COMPLEX_STRING, f"<S>{COMPLEX_ENCODED_STRING}</S>"),
        (PSUInt(1), "<U32>1</U32>"),
        (PSUInt16(1), "<U16>1</U16>"),
        (PSUInt64(1), "<U64>1</U64>"),
        (PSUri(COMPLEX_STRING), f"<URI>{COMPLEX_ENCODED_STRING}</URI>"),
        (PSVersion("1.2.3.4"), "<Version>1.2.3.4</Version>"),
        (PSXml(COMPLEX_STRING), f"<XD>{COMPLEX_ENCODED_STRING}</XD>"),
    ],
)
def test_serialize_primitive_object(input_value, expected):
    element = serializer.serialize(input_value, FakeCryptoProvider())
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert actual == expected


@pytest.mark.parametrize(
    "input_value, expected",
    [
        ("<B>true</B>", PSBool(True)),
        ("<B>false</B>", PSBool(False)),
        ("<By>1</By>", PSByte(1)),
        ("<BA>AAECAw==</BA>", PSByteArray(b"\x00\x01\x02\x03")),
        ("<C>97</C>", PSChar("a")),
        (
            "<DT>2008-04-11T10:42:32.2731993-07:00</DT>",
            PSDateTime(
                2008,
                4,
                11,
                10,
                42,
                32,
                273199,
                tzinfo=datetime.timezone(-datetime.timedelta(seconds=25200)),
                nanosecond=300,
            ),
        ),
        ("<D>1</D>", PSDecimal(1)),
        ("<Db>1.0</Db>", PSDouble(1.0)),
        ("<TS>PT9.0269026S</TS> ", PSDuration(seconds=9, microseconds=26902, nanoseconds=600)),
        ("<G>00000000-0000-0000-0000-000000000000</G>", PSGuid(int=0)),
        ("<I32>1</I32>", PSInt(1)),
        ("<I16>1</I16>", PSInt16(1)),
        ("<I64>1</I64>", PSInt64(1)),
        ("<Sg>1.0</Sg>", PSSingle(1.0)),
        ("<SB>1</SB>", PSSByte(1)),
        (f"<SBK>{COMPLEX_ENCODED_STRING}</SBK>", PSScriptBlock(COMPLEX_STRING)),
        (f"<S>{COMPLEX_ENCODED_STRING}</S>", PSString(COMPLEX_STRING)),
        ("<U32>1</U32>", PSUInt(1)),
        ("<U16>1</U16>", PSUInt16(1)),
        ("<U64>1</U64>", PSUInt64(1)),
        (f"<URI>{COMPLEX_ENCODED_STRING}</URI>", PSUri(COMPLEX_STRING)),
        ("<Version>1.2.3.4</Version>", PSVersion("1.2.3.4")),
        (f"<XD>{COMPLEX_ENCODED_STRING}</XD>", PSXml(COMPLEX_STRING)),
    ],
)
def test_deserialize_primitive_object(input_value, expected):
    element = ElementTree.fromstring(input_value)
    actual = serializer.deserialize(element, FakeCryptoProvider())
    assert isinstance(actual, type(expected))
    assert actual == expected


def test_deserialize_invalid_duration():
    expected = re.escape("Duration input 'invalid' is not valid, cannot deserialize")
    with pytest.raises(ValueError, match=expected):
        serializer.deserialize(ElementTree.fromstring("<TS>invalid</TS>"), FakeCryptoProvider())


def test_serialize_python_class():
    class MyClass:
        def __init__(self):
            self.attribute = "abc"
            self.__private = "wont appear"

        @property
        def property(self):
            return "def"

        def __str__(self):
            return "MyClass"

        def function(self):
            return "wont appear"

    element = serializer.serialize(MyClass(), FakeCryptoProvider())
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.PSCustomObject</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<MS>"
        '<S N="attribute">abc</S>'
        '<S N="property">def</S>'
        "</MS>"
        "</Obj>"
    )


def test_deserialize_unknown_tag():
    expected = re.escape("Unknown element found: bad")
    with pytest.raises(ValueError, match=expected):
        serializer.deserialize(ElementTree.fromstring("<bad>test</bad>"), FakeCryptoProvider())


def test_deserialize_special_queue():
    clixml = (
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Collections.Generic.Queue`1[[System.Object]]</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<QUE>"
        "<I32>1</I32>"
        "<I32>2</I32>"
        "</QUE>"
        "</Obj>"
    )

    actual = serializer.deserialize(ElementTree.fromstring(clixml), FakeCryptoProvider())
    assert actual.PSTypeNames == [
        "Deserialized.System.Collections.Generic.Queue`1[[System.Object]]",
        "Deserialized.System.Object",
    ]
    assert isinstance(actual, PSQueue)
    assert actual.get() == 1
    assert actual.get() == 2
    with pytest.raises(queue.Empty):
        actual.get(block=False)


def test_serialize_native_enum():
    class MyEnum(enum.IntEnum):
        none = 0
        test1 = 1

    element = serializer.serialize(MyEnum.none, FakeCryptoProvider())
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert actual == (
        '<Obj RefId="0">'
        "<I32>0</I32>"
        '<TN RefId="0">'
        f"<T>{MyEnum.__module__}.{MyEnum.__name__}</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>none</ToString>"
        "</Obj>"
    )

    element = serializer.serialize(MyEnum.test1, FakeCryptoProvider())
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert actual == (
        '<Obj RefId="0">'
        "<I32>1</I32>"
        '<TN RefId="0">'
        f"<T>{MyEnum.__module__}.{MyEnum.__name__}</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>test1</ToString>"
        "</Obj>"
    )


def test_serialize_native_flags():
    class MyEnum(enum.IntFlag):
        none = 0
        test1 = 1
        test2 = 2

    element = serializer.serialize(MyEnum.none, FakeCryptoProvider())
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert actual == (
        '<Obj RefId="0">'
        "<I32>0</I32>"
        '<TN RefId="0">'
        f"<T>{MyEnum.__module__}.{MyEnum.__name__}</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>none</ToString>"
        "</Obj>"
    )

    element = serializer.serialize(MyEnum.test1 | MyEnum.test2, FakeCryptoProvider())
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert actual == (
        '<Obj RefId="0">'
        "<I32>3</I32>"
        '<TN RefId="0">'
        f"<T>{MyEnum.__module__}.{MyEnum.__name__}</T>"
        "<T>System.Enum</T>"
        "<T>System.ValueType</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<ToString>test1, test2</ToString>"
        "</Obj>"
    )


def test_fail_deserialize_dict_no_key():
    clixml = (
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Collections.Hashtable</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<DCT>"
        '<En><S N="NotKey">1</S><S N="Value">test</S></En>'
        "</DCT>"
        "</Obj>"
    )

    with pytest.raises(ValueError, match="Failed to find dict Key attribute"):
        serializer.deserialize(ElementTree.fromstring(clixml), FakeCryptoProvider())


def test_fail_deserialize_dict_no_value():
    clixml = (
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Collections.Hashtable</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<DCT>"
        '<En><S N="Key">1</S><S N="NotValue">test</S></En>'
        "</DCT>"
        "</Obj>"
    )

    with pytest.raises(ValueError, match="Failed to find dict Value attribute"):
        serializer.deserialize(ElementTree.fromstring(clixml), FakeCryptoProvider())


def test_serialize_circular_reference():
    obj = PSCustomObject(MyProp=1, List=[1], Dict={"test": 1}, CircularRef=None)
    obj.List.append(obj)
    obj.Dict["obj"] = obj
    obj.CircularRef = obj

    element = serializer.serialize(obj, FakeCryptoProvider())
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    expected = (
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Management.Automation.PSCustomObject</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<MS>"
        '<I32 N="MyProp">1</I32>'
        '<Obj RefId="1" N="List">'
        '<TN RefId="1">'
        "<T>System.Collections.ArrayList</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<LST>"
        "<I32>1</I32>"
        '<Ref RefId="0" />'
        "</LST>"
        "</Obj>"
        '<Obj RefId="2" N="Dict">'
        '<TN RefId="2">'
        "<T>System.Collections.Hashtable</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<DCT>"
        '<En><S N="Key">test</S><I32 N="Value">1</I32></En>'
        '<En><S N="Key">obj</S><Ref RefId="0" N="Value" /></En>'
        "</DCT>"
        "</Obj>"
        '<Ref RefId="0" N="CircularRef" />'
        "</MS>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    obj = serializer.deserialize(element, FakeCryptoProvider())
    assert isinstance(obj, PSCustomObject)
    assert obj.MyProp == 1
    assert len(obj.List) == 2
    assert obj.List[0] == 1
    assert obj.List[1] == obj
    assert obj.Dict["test"] == 1
    assert obj.Dict["obj"] == obj
    assert obj.CircularRef == obj
