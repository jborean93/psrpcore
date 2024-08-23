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
    ClixmlStream,
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
    PSList,
    PSQueue,
    PSSByte,
    PSScriptBlock,
    PSSecureString,
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
        (PSDateTime(1970, 1, 1), "<DT>1970-01-01T00:00:00</DT>"),
        (datetime.datetime(1970, 1, 1), "<DT>1970-01-01T00:00:00</DT>"),
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
        ("", ""),
        ("just newline _x000A_", "just newline \n"),
        ("surrogate pair _xD83C__xDFB5_", "surrogate pair 🎵"),
        ("null char _x0000_", "null char \0"),
        ("normal char _x0061_", "normal char a"),
        ("escaped literal _x005F_x005F_", "escaped literal _x005F_"),
        ("underscope before escape _x005F__x000A_", "underscope before escape _\n"),
        ("surrogate high _xD83C_", "surrogate high \uD83C"),
        ("surrogate low _xDFB5_", "surrogate low \uDFB5"),
        ("lower case hex _x005f_", "lower case hex _"),
        ("invalid hex _x005G_", "invalid hex _x005G_"),
        # Tests regex actually matches UTF-16-BE hex chars (\x00 then char).
        ("_x\u6100\u6200\u6300\u6400_", "_x\u6100\u6200\u6300\u6400_"),
    ],
)
def test_deserialize_string(input_value: str, expected: str) -> None:
    clixml = ElementTree.fromstring(f"<S>{input_value}</S>")
    actual = serializer.deserialize(clixml, FakeCryptoProvider())
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


def test_serialize_secure_string_failure() -> None:
    with pytest.raises(NotImplementedError):
        serializer.serialize(PSSecureString("secret"), serializer.PSCryptoProvider())


def test_deserialize_secure_string_failure() -> None:
    value = "<SS>encvalue</SS>"
    element = ElementTree.fromstring(value)
    ss = serializer.deserialize(element, serializer.PSCryptoProvider())
    assert isinstance(ss, PSSecureString)

    with pytest.raises(NotImplementedError):
        assert ss.decrypt()


def test_serialize_clixml_single() -> None:
    expected = '<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><S>foo</S></Objs>'
    actual = serializer.serialize_clixml("foo", FakeCryptoProvider())

    assert actual == expected


def test_serialize_clixml_single_with_stream() -> None:
    expected = (
        '<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><S S="verbose">foo</S></Objs>'
    )
    actual = serializer.serialize_clixml(("foo", ClixmlStream.VERBOSE), FakeCryptoProvider())

    assert actual == expected


def test_serialize_clixml_list() -> None:
    expected = (
        '<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><S>foo</S><S>bar</S></Objs>'
    )
    actual = serializer.serialize_clixml(["foo", "bar"], FakeCryptoProvider())

    assert actual == expected


def test_serialize_clixml_list_with_streams() -> None:
    expected = '<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><S S="output">foo</S><S S="warning">bar</S></Objs>'
    actual = serializer.serialize_clixml(
        [
            ("foo", ClixmlStream.OUTPUT),
            ("bar", ClixmlStream.WARNING),
        ],
        FakeCryptoProvider(),
    )

    assert actual == expected


def test_serialize_clixml_list_of_lists() -> None:
    expected = (
        '<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04">'
        '<Obj RefId="0"><TN RefId="0"><T>System.Collections.ArrayList</T><T>System.Object</T></TN><LST><S>foo</S><S>bar</S></LST></Obj>'
        "<S>final</S></Objs>"
    )
    actual = serializer.serialize_clixml([["foo", "bar"], "final"], FakeCryptoProvider())

    assert actual == expected


@pytest.mark.parametrize("newline", ("\n", "\r\n"))
def test_deserialize_clixml_with_header(newline: str) -> None:
    value = f'#< CLIXML{newline}<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><S>foo</S></Objs>'

    actual = serializer.deserialize_clixml(value, FakeCryptoProvider())
    assert isinstance(actual, list)
    assert len(actual) == 1
    assert isinstance(actual[0], PSString)
    assert actual[0] == "foo"


def test_deserialize_clixml_without_header() -> None:
    value = f'<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><S>foo</S></Objs>'

    actual = serializer.deserialize_clixml(value, FakeCryptoProvider())
    assert isinstance(actual, list)
    assert len(actual) == 1
    assert isinstance(actual[0], PSString)
    assert actual[0] == "foo"


def test_deserialize_clixml_preserve_streams_no_attrib() -> None:
    value = f'<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><S>foo</S></Objs>'

    actual = serializer.deserialize_clixml(value, FakeCryptoProvider(), preserve_streams=True)
    assert isinstance(actual, list)
    assert len(actual) == 1
    assert len(actual[0]) == 2
    assert isinstance(actual[0][0], PSString)
    assert actual[0][0] == "foo"
    assert actual[0][1] == ClixmlStream.OUTPUT


def test_deserialize_clixml_preserve_streams_with_attrib() -> None:
    value = (
        f'<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><S S="verbose">foo</S></Objs>'
    )

    actual = serializer.deserialize_clixml(value, FakeCryptoProvider(), preserve_streams=True)
    assert isinstance(actual, list)
    assert len(actual) == 1
    assert len(actual[0]) == 2
    assert isinstance(actual[0][0], PSString)
    assert actual[0][0] == "foo"
    assert actual[0][1] == ClixmlStream.VERBOSE


def test_deserialize_clixml_preserve_streams_with_unknown_attrib() -> None:
    value = (
        f'<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><S S="unknown">foo</S></Objs>'
    )

    actual = serializer.deserialize_clixml(value, FakeCryptoProvider(), preserve_streams=True)
    assert isinstance(actual, list)
    assert len(actual) == 1
    assert len(actual[0]) == 2
    assert isinstance(actual[0][0], PSString)
    assert actual[0][0] == "foo"
    assert actual[0][1] == ClixmlStream.OUTPUT


def test_deserialize_clixml_multiple_values() -> None:
    value = (
        f'<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><S>foo</S><I64>1</I64></Objs>'
    )

    actual = serializer.deserialize_clixml(value, FakeCryptoProvider())
    assert isinstance(actual, list)
    assert len(actual) == 2
    assert isinstance(actual[0], PSString)
    assert actual[0] == "foo"
    assert isinstance(actual[1], PSInt64)
    assert actual[1] == 1


def test_deserialize_clixml_list_value() -> None:
    value = (
        '<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04">'
        '<Obj RefId="0"><TN RefId="0"><T>System.Collections.ArrayList</T><T>System.Object</T></TN><LST><S>foo</S><S>bar</S></LST></Obj>'
        "<S>final</S></Objs>"
    )
    actual = serializer.deserialize_clixml(value, FakeCryptoProvider())
    assert isinstance(actual, list)
    assert len(actual) == 2
    assert isinstance(actual[0], PSList)
    assert len(actual[0]) == 2
    assert isinstance(actual[0][0], PSString)
    assert actual[0][0] == "foo"
    assert isinstance(actual[0][1], PSString)
    assert actual[0][1] == "bar"
    assert isinstance(actual[1], PSString)
    assert actual[1] == "final"
