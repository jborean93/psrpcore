# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import enum
import re
import xml.etree.ElementTree as ElementTree

import pytest

import psrpcore.types._enum as ps_enum
from psrpcore.types import (
    PSInt,
    PSInt64,
    PSNoteProperty,
    PSObject,
    PSString,
    PSType,
    PSUInt,
)

from ..conftest import COMPLEX_ENCODED_STRING, COMPLEX_STRING, deserialize, serialize


@pytest.mark.parametrize("rehydrate", [True, False])
def test_ps_enum(rehydrate):
    type_name = "MyEnumRehydrated" if rehydrate else "MyEnum"

    @PSType(type_names=[f"System.{type_name}"], rehydrate=rehydrate)
    class EnumTest(ps_enum.PSEnumBase):

        none = 0
        Value1 = 1
        Value2 = 2
        Value3 = 3

    assert str(EnumTest.none) == "EnumTest.none"
    assert repr(EnumTest.none) == "<EnumTest.none: 0>"
    assert str(EnumTest.Value1) == "EnumTest.Value1"
    assert repr(EnumTest.Value1) == "<EnumTest.Value1: 1>"
    assert str(EnumTest.Value2) == "EnumTest.Value2"
    assert str(EnumTest.Value3) == "EnumTest.Value3"

    val = EnumTest.Value1
    assert isinstance(val, PSObject)
    assert isinstance(val, enum.Enum)
    assert isinstance(val, ps_enum.PSEnumBase)
    assert not isinstance(val, PSInt)
    assert isinstance(val.value, PSInt)
    assert isinstance(val, int)

    element = serialize(val)

    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == f'<Obj RefId="0">'
        f"<I32>1</I32>"
        f'<TN RefId="0">'
        f"<T>System.{type_name}</T>"
        f"<T>System.Enum</T>"
        f"<T>System.ValueType</T>"
        f"<T>System.Object</T>"
        f"</TN>"
        f"<ToString>Value1</ToString>"
        f"</Obj>"
    )

    actual = deserialize(element)
    base_types = [f"System.{type_name}", "System.Enum", "System.ValueType", "System.Object"]

    if rehydrate:
        assert actual == val
        assert str(actual) == "EnumTest.Value1"
        assert isinstance(actual, int)
        assert isinstance(actual, PSObject)
        assert not isinstance(actual, PSInt)
        assert isinstance(actual, ps_enum.PSEnumBase)
        assert isinstance(actual, EnumTest)
        assert isinstance(actual, enum.Enum)
        assert actual.PSTypeNames == base_types

    else:
        # Without hydration we just get the primitive value back
        base_types = [f"Deserialized.{t}" for t in base_types]
        assert actual == val.value
        assert str(actual) == "Value1"
        assert isinstance(actual, int)
        assert isinstance(actual, PSObject)
        assert isinstance(actual, PSInt)
        assert not isinstance(actual, ps_enum.PSEnumBase)
        assert not isinstance(actual, EnumTest)
        assert not isinstance(actual, enum.Enum)
        assert actual.PSTypeNames == base_types


@pytest.mark.parametrize("rehydrate", [True, False])
def test_ps_enum_unsigned_type(rehydrate):
    type_name = "EnumUIntRehydrated" if rehydrate else "EnumUInt"

    @PSType(type_names=[f"System.{type_name}"], rehydrate=rehydrate)
    class EnumTest(ps_enum.PSEnumBase, base_type=PSUInt):

        none = 0
        Value1 = 1
        Value2 = 2
        Value3 = 3

    assert str(EnumTest.none) == "EnumTest.none"
    assert repr(EnumTest.none) == "<EnumTest.none: 0>"
    assert str(EnumTest.Value1) == "EnumTest.Value1"
    assert repr(EnumTest.Value1) == "<EnumTest.Value1: 1>"
    assert str(EnumTest.Value2) == "EnumTest.Value2"
    assert str(EnumTest.Value3) == "EnumTest.Value3"

    val = EnumTest.Value1
    assert isinstance(val, PSObject)
    assert isinstance(val, enum.Enum)
    assert isinstance(val, ps_enum.PSEnumBase)
    assert not isinstance(val, PSUInt)
    assert isinstance(val.value, PSUInt)
    assert isinstance(val, int)

    element = serialize(val)

    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == f'<Obj RefId="0">'
        f"<U32>1</U32>"
        f'<TN RefId="0">'
        f"<T>System.{type_name}</T>"
        f"<T>System.Enum</T>"
        f"<T>System.ValueType</T>"
        f"<T>System.Object</T>"
        f"</TN>"
        f"<ToString>Value1</ToString>"
        f"</Obj>"
    )

    actual = deserialize(element)
    base_types = [f"System.{type_name}", "System.Enum", "System.ValueType", "System.Object"]

    if rehydrate:
        assert actual == val
        assert str(actual) == "EnumTest.Value1"
        assert isinstance(actual, int)
        assert isinstance(actual, PSObject)
        assert not isinstance(actual, PSUInt)
        assert isinstance(actual, ps_enum.PSEnumBase)
        assert isinstance(actual, EnumTest)
        assert isinstance(actual, enum.Enum)
        assert actual.PSTypeNames == base_types

    else:
        # Without hydration we just get the primitive value back
        base_types = [f"Deserialized.{t}" for t in base_types]
        assert actual == val.value
        assert str(actual) == "Value1"
        assert isinstance(actual, int)
        assert isinstance(actual, PSObject)
        assert isinstance(actual, PSUInt)
        assert not isinstance(actual, ps_enum.PSEnumBase)
        assert not isinstance(actual, EnumTest)
        assert not isinstance(actual, enum.Enum)
        assert actual.PSTypeNames == base_types


@pytest.mark.parametrize("rehydrate", [True, False])
def test_ps_enum_extended_properties(rehydrate):
    type_name = "EnumExtendedRehydrated" if rehydrate else "EnumExtended"

    @PSType(type_names=[f"System.{type_name}"], rehydrate=rehydrate)
    class EnumTest(ps_enum.PSEnumBase, base_type=PSInt64):

        none = 0
        Value1 = 1
        Value2 = 2
        Value3 = 3

    assert str(EnumTest.none) == "EnumTest.none"
    assert repr(EnumTest.none) == "<EnumTest.none: 0>"
    assert str(EnumTest.Value1) == "EnumTest.Value1"
    assert repr(EnumTest.Value1) == "<EnumTest.Value1: 1>"
    assert str(EnumTest.Value2) == "EnumTest.Value2"
    assert str(EnumTest.Value3) == "EnumTest.Value3"

    val = EnumTest.none
    val.PSObject.extended_properties.append(PSNoteProperty(COMPLEX_STRING))
    val[COMPLEX_STRING] = COMPLEX_STRING
    assert isinstance(val, PSObject)
    assert isinstance(val, enum.Enum)
    assert isinstance(val, ps_enum.PSEnumBase)
    assert not isinstance(val, PSInt64)
    assert isinstance(val.value, PSInt64)
    assert isinstance(val.value, int)

    element = serialize(val)

    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == f'<Obj RefId="0">'
        f"<I64>0</I64>"
        f'<TN RefId="0">'
        f"<T>System.{type_name}</T>"
        f"<T>System.Enum</T>"
        f"<T>System.ValueType</T>"
        f"<T>System.Object</T>"
        f"</TN>"
        f"<MS>"
        f'<S N="{COMPLEX_ENCODED_STRING}">{COMPLEX_ENCODED_STRING}</S>'
        f"</MS>"
        f"<ToString>None</ToString>"
        f"</Obj>"
    )

    actual = deserialize(element)
    base_types = [f"System.{type_name}", "System.Enum", "System.ValueType", "System.Object"]

    assert val[COMPLEX_STRING] == COMPLEX_STRING

    if rehydrate:
        assert actual == val
        assert str(actual) == "EnumTest.none"
        assert isinstance(actual, int)
        assert isinstance(actual, PSObject)
        assert not isinstance(actual, PSInt64)
        assert isinstance(actual, ps_enum.PSEnumBase)
        assert isinstance(actual, EnumTest)
        assert isinstance(actual, enum.Enum)
        assert actual.PSTypeNames == base_types

    else:
        # Without hydration we just get the primitive value back
        base_types = [f"Deserialized.{t}" for t in base_types]
        assert actual == val.value
        assert str(actual) == "None"
        assert isinstance(actual, int)
        assert isinstance(actual, PSObject)
        assert isinstance(actual, PSInt64)
        assert not isinstance(actual, ps_enum.PSEnumBase)
        assert not isinstance(actual, EnumTest)
        assert not isinstance(actual, enum.Enum)
        assert actual.PSTypeNames == base_types


@pytest.mark.parametrize("rehydrate", [True, False])
def test_ps_flags(rehydrate):
    type_name = "FlagHydrated" if rehydrate else "Flag"

    @PSType(type_names=[f"System.{type_name}"], rehydrate=rehydrate)
    class FlagTest(ps_enum.PSFlagBase):

        none = 0
        Flag1 = 1
        Flag2 = 2
        Flag3 = 4

    assert str(FlagTest.none) == "FlagTest.none"
    assert repr(FlagTest.none) == "<FlagTest.none: 0>"
    assert str(FlagTest.Flag1) == "FlagTest.Flag1"
    assert repr(FlagTest.Flag1) == "<FlagTest.Flag1: 1>"
    assert str(FlagTest.Flag2) == "FlagTest.Flag2"
    assert str(FlagTest.Flag3) == "FlagTest.Flag3"
    assert str(FlagTest.Flag1 | FlagTest.Flag3) == "FlagTest.Flag3|Flag1"
    assert repr(FlagTest.Flag1 | FlagTest.Flag3) == "<FlagTest.Flag3|Flag1: 5>"

    val = FlagTest.Flag1 | FlagTest.Flag3
    assert isinstance(val, PSObject)
    assert isinstance(val, enum.Flag)
    assert not isinstance(val, ps_enum.PSEnumBase)
    assert isinstance(val, ps_enum.PSFlagBase)
    assert not isinstance(val, PSInt)
    assert isinstance(val.value, PSInt)
    assert isinstance(val, int)

    element = serialize(val)

    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == f'<Obj RefId="0">'
        f"<I32>5</I32>"
        f'<TN RefId="0">'
        f"<T>System.{type_name}</T>"
        f"<T>System.Enum</T>"
        f"<T>System.ValueType</T>"
        f"<T>System.Object</T>"
        f"</TN>"
        f"<ToString>Flag1, Flag3</ToString>"
        f"</Obj>"
    )

    actual = deserialize(element)
    base_types = [f"System.{type_name}", "System.Enum", "System.ValueType", "System.Object"]

    if rehydrate:
        assert actual == val
        assert str(actual) == "FlagTest.Flag3|Flag1"
        assert isinstance(actual, int)
        assert isinstance(actual, PSObject)
        assert not isinstance(actual, PSInt)
        assert isinstance(actual, ps_enum.PSFlagBase)
        assert isinstance(actual, FlagTest)
        assert isinstance(actual, enum.Flag)
        assert actual.PSTypeNames == base_types

    else:
        # Without hydration we just get the primitive value back
        base_types = [f"Deserialized.{t}" for t in base_types]
        assert actual == val.value
        assert str(actual) == "Flag1, Flag3"
        assert isinstance(actual, int)
        assert isinstance(actual, PSObject)
        assert isinstance(actual, PSInt)
        assert not isinstance(actual, ps_enum.PSFlagBase)
        assert not isinstance(actual, FlagTest)
        assert not isinstance(actual, enum.Flag)
        assert actual.PSTypeNames == base_types

    element = serialize(FlagTest.none)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == f'<Obj RefId="0">'
        f"<I32>0</I32>"
        f'<TN RefId="0">'
        f"<T>System.{type_name}</T>"
        f"<T>System.Enum</T>"
        f"<T>System.ValueType</T>"
        f"<T>System.Object</T>"
        f"</TN>"
        f"<ToString>None</ToString>"
        f"</Obj>"
    )

    element = serialize(FlagTest.none | FlagTest.Flag2)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == f'<Obj RefId="0">'
        f"<I32>2</I32>"
        f'<TN RefId="0">'
        f"<T>System.{type_name}</T>"
        f"<T>System.Enum</T>"
        f"<T>System.ValueType</T>"
        f"<T>System.Object</T>"
        f"</TN>"
        f"<ToString>Flag2</ToString>"
        f"</Obj>"
    )


def test_ps_flags_operators():
    @PSType(type_names=["System.FlagTest"])
    class FlagTest(ps_enum.PSFlagBase):

        none = 0
        Flag1 = 1
        Flag2 = 2
        Flag3 = 4
        Flag4 = 8

    val = FlagTest.none
    assert val == FlagTest.none
    assert val != FlagTest.Flag1
    assert str(val) == "FlagTest.none"
    assert val.name == "none"
    assert val.value == 0

    val |= FlagTest.Flag1 | FlagTest.Flag2
    assert isinstance(val, FlagTest)
    assert str(val) == "FlagTest.Flag2|Flag1"
    assert val.name is None
    assert val.value == 3

    val &= FlagTest.Flag1
    assert isinstance(val, FlagTest)
    assert str(val) == "FlagTest.Flag1"
    assert val.name == "Flag1"
    assert val.value == 1

    val = (FlagTest.Flag1 | FlagTest.Flag2) ^ FlagTest.Flag1
    assert isinstance(val, FlagTest)
    assert str(val) == "FlagTest.Flag2"
    assert val.value == 2

    val = val << 2
    assert val == FlagTest.Flag4
    assert str(val) == "FlagTest.Flag4"
    assert val.name == "Flag4"
    assert val.value == 8

    val = val >> 2
    assert val == FlagTest.Flag2
    assert str(val) == "FlagTest.Flag2"
    assert val.name == "Flag2"
    assert val.value == 2

    val = ~val
    assert isinstance(val, FlagTest)
    assert str(val) == "FlagTest.Flag4|Flag3|Flag1"
    assert val.name is None
    assert val.value == -3


def test_ps_enum_not_inheriting_int_base():
    expected = re.escape("PSEnumType InvalidEnum base_type must be a subclass of PSIntegerBase")
    with pytest.raises(TypeError, match=expected):

        @PSType(type_names=["Test"])
        class InvalidEnum(ps_enum.PSEnumBase, base_type=PSString):
            none = 0


def test_ps_enum_to_ps_ps_baseint():
    @PSType(type_names=["System.EnumToInt"])
    class EnumToInt(ps_enum.PSEnumBase):

        none = 0
        Value1 = 1

    value = PSInt(EnumToInt.Value1)
    assert isinstance(value, PSInt)
    assert value == 1

    value = PSInt64(EnumToInt.Value1)
    assert isinstance(value, PSInt64)
    assert value == 1
