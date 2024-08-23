# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import collections
import queue
import re
import xml.etree.ElementTree as ElementTree

import pytest

import psrpcore.types._collection as collection
from psrpcore.types import PSChar, PSInt64, PSNoteProperty

from ..conftest import (
    COMPLEX_ENCODED_STRING,
    COMPLEX_STRING,
    assert_xml_diff,
    deserialize,
    serialize,
)


def test_ps_dict_instantiation():
    expected = re.escape(
        "Type PSDictBase cannot be instantiated; it can be used only as a base class for dictionary " "types."
    )
    with pytest.raises(TypeError, match=expected):
        collection.PSDictBase()


def test_ps_list_instantiation():
    expected = re.escape(
        "Type PSListBase cannot be instantiated; it can be used only as a base class for list " "types."
    )
    with pytest.raises(TypeError, match=expected):
        collection.PSListBase()


def test_ps_queue_instantiation():
    expected = re.escape(
        "Type PSQueueBase cannot be instantiated; it can be used only as a base class for queue " "types."
    )
    with pytest.raises(TypeError, match=expected):
        collection.PSQueueBase()


def test_ps_stack_instantiation():
    expected = re.escape(
        "Type PSStackBase cannot be instantiated; it can be used only as a base class for list " "types."
    )
    with pytest.raises(TypeError, match=expected):
        collection.PSStackBase()


def test_ps_stack():
    ps_value = collection.PSStack(["abc", 123, PSInt64(1)])
    ps_value.append(True)
    assert isinstance(ps_value, collection.PSStack)
    assert isinstance(ps_value, list)

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8", method="xml").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0"><T>System.Collections.Stack</T><T>System.Object</T></TN>'
        "<STK><S>abc</S><I32>123</I32><I64>1</I64><B>true</B></STK>"
        "</Obj>"
    )

    actual = deserialize(element)
    assert isinstance(actual, collection.PSStack)
    assert isinstance(actual, list)
    assert str(actual) == "['abc', 123, 1, True]"
    assert repr(actual) == "['abc', 123, 1, True]"
    assert actual == ["abc", 123, PSInt64(1), True]
    # Verify we can still index the list
    assert actual[0] == "abc"
    assert actual[1] == 123
    assert actual[2] == PSInt64(1)
    assert actual[3] is True
    assert actual.PSTypeNames == ["System.Collections.Stack", "System.Object"]


def test_ps_stack_with_properties():
    ps_value = collection.PSStack([0, 2, PSChar("a")])
    ps_value.PSObject.extended_properties.append(PSNoteProperty("1"))
    ps_value[1] = 1
    ps_value["1"] = collection.PSStack(["123", 123])

    # Make sure we can access the stack using an index and the properties with a string.
    assert ps_value[1] == 1
    assert isinstance(ps_value["1"], collection.PSStack)
    assert ps_value["1"] == ["123", 123]

    # Check that appending an item doesn't clear our properties
    ps_value.append(2)

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8", method="xml").decode()
    expected = (
        '<Obj RefId="0"><TN RefId="0"><T>System.Collections.Stack</T><T>System.Object</T></TN>'
        "<MS>"
        '<Obj RefId="1" N="1"><TNRef RefId="0" />'
        "<STK><S>123</S><I32>123</I32></STK>"
        "</Obj>"
        "</MS>"
        "<STK><I32>0</I32><I32>1</I32><C>97</C><I32>2</I32></STK>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    actual = deserialize(element)
    assert isinstance(actual, collection.PSStack)
    assert isinstance(actual, list)
    assert str(actual) == "[0, 1, 97, 2]"
    assert repr(actual) == "[0, 1, 97, 2]"
    assert actual == [0, 1, PSChar("a"), 2]
    # Verify we can still index the list
    assert actual[0] == 0
    assert actual[1] == 1
    assert actual[2] == PSChar("a")
    assert actual[3] == 2

    # Verify we can access the extended prop using a string index.
    assert isinstance(actual["1"], collection.PSStack)
    assert actual["1"] == collection.PSStack(["123", 123])

    assert actual.PSTypeNames == ["System.Collections.Stack", "System.Object"]


def test_ps_queue():
    ps_value = collection.PSQueue()
    ps_value.put("abc")
    ps_value.put(123)
    ps_value.put(PSInt64(1))
    ps_value.put(collection.PSQueue())
    assert isinstance(ps_value, collection.PSQueue)
    assert isinstance(ps_value, queue.Queue)

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8", method="xml").decode()
    assert (
        actual == '<Obj RefId="0"><TN RefId="0"><T>System.Collections.Queue</T><T>System.Object</T></TN>'
        "<QUE>"
        "<S>abc</S>"
        "<I32>123</I32>"
        "<I64>1</I64>"
        '<Obj RefId="1"><TNRef RefId="0" /><QUE /></Obj>'
        "</QUE>"
        "</Obj>"
    )

    actual = deserialize(element)
    assert isinstance(actual, collection.PSQueue)
    assert isinstance(actual, queue.Queue)
    assert str(actual) == queue.Queue.__str__(actual)
    assert repr(actual) == queue.Queue.__repr__(actual)

    assert actual.get() == "abc"
    assert actual.get() == 123
    assert actual.get() == PSInt64(1)

    queue_entry = actual.get()
    assert isinstance(queue_entry, collection.PSQueue)
    assert isinstance(queue_entry, queue.Queue)
    with pytest.raises(queue.Empty):
        queue_entry.get(block=False)

    with pytest.raises(queue.Empty):
        actual.get(block=False)

    assert actual.PSTypeNames == ["System.Collections.Queue", "System.Object"]


def test_ps_queue_from_queue():
    q = queue.Queue()
    q.put(1)
    q.put("1")
    q.put("a")

    element = serialize(q)
    actual = ElementTree.tostring(element, encoding="utf-8", method="xml").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0"><T>System.Collections.Queue</T><T>System.Object</T></TN>'
        "<QUE><I32>1</I32><S>1</S><S>a</S></QUE>"
        "</Obj>"
    )


def test_ps_queue_with_properties():
    ps_value = collection.PSQueue()
    ps_value.put("abc")
    ps_value.put(123)
    ps_value.put(PSInt64(1))
    ps_value.put(collection.PSQueue())

    ps_value.PSObject.extended_properties.append(PSNoteProperty("1"))
    ps_value["1"] = collection.PSQueue()
    ps_value["1"].put("entry")

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8", method="xml").decode()
    expected = (
        '<Obj RefId="0"><TN RefId="0"><T>System.Collections.Queue</T><T>System.Object</T></TN>'
        "<MS>"
        '<Obj RefId="1" N="1"><TNRef RefId="0" /><QUE><S>entry</S></QUE></Obj>'
        "</MS>"
        "<QUE>"
        "<S>abc</S>"
        "<I32>123</I32>"
        "<I64>1</I64>"
        '<Obj RefId="2"><TNRef RefId="0" /><QUE /></Obj>'
        "</QUE>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    actual = deserialize(element)
    assert isinstance(actual, collection.PSQueue)
    assert isinstance(actual, queue.Queue)
    assert str(actual) == queue.Queue.__str__(actual)
    assert repr(actual) == queue.Queue.__repr__(actual)

    assert actual.get() == "abc"
    assert actual.get() == 123
    assert actual.get() == PSInt64(1)

    queue_entry = actual.get()
    assert isinstance(queue_entry, collection.PSQueue)
    assert isinstance(queue_entry, queue.Queue)
    with pytest.raises(queue.Empty):
        queue_entry.get(block=False)

    with pytest.raises(queue.Empty):
        actual.get(block=False)

    prop_queue = actual["1"]
    assert isinstance(prop_queue, collection.PSQueue)
    assert isinstance(prop_queue, queue.Queue)
    assert prop_queue.get() == "entry"
    with pytest.raises(queue.Empty):
        prop_queue.get(block=False)

    assert actual.PSTypeNames == ["System.Collections.Queue", "System.Object"]


def test_ps_list():
    ps_value = collection.PSList(["abc", 123, PSInt64(1)])
    ps_value.append(True)
    assert isinstance(ps_value, collection.PSList)
    assert isinstance(ps_value, list)

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8", method="xml").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0"><T>System.Collections.ArrayList</T><T>System.Object</T></TN>'
        "<LST><S>abc</S><I32>123</I32><I64>1</I64><B>true</B></LST>"
        "</Obj>"
    )

    actual = deserialize(element)
    assert isinstance(actual, collection.PSList)
    assert isinstance(actual, list)
    assert str(actual) == "['abc', 123, 1, True]"
    assert repr(actual) == "['abc', 123, 1, True]"

    assert actual == ["abc", 123, PSInt64(1), True]
    # Verify we can still index the list
    assert actual[0] == "abc"
    assert actual[1] == 123
    assert actual[2] == PSInt64(1)
    assert actual[3] is True
    assert actual.PSTypeNames == ["System.Collections.ArrayList", "System.Object"]


def test_ps_list_from_list():
    element = serialize([1, "1", "a"])
    actual = ElementTree.tostring(element, encoding="utf-8", method="xml").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0"><T>System.Collections.ArrayList</T><T>System.Object</T></TN>'
        "<LST><I32>1</I32><S>1</S><S>a</S></LST>"
        "</Obj>"
    )


def test_ps_list_with_properties():
    ps_value = collection.PSList([0, 2, PSChar("a")])
    ps_value.PSObject.extended_properties.append(PSNoteProperty("1"))
    ps_value[1] = 1
    ps_value["1"] = collection.PSList(["123", 123])

    # Make sure we can access the stack using an index and the properties with a string.
    assert ps_value[1] == 1
    assert isinstance(ps_value["1"], collection.PSList)
    assert ps_value["1"] == ["123", 123]

    # Check that appending an item doesn't clear our properties
    ps_value.append(2)

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8", method="xml").decode()
    expected = (
        '<Obj RefId="0"><TN RefId="0"><T>System.Collections.ArrayList</T><T>System.Object</T></TN>'
        "<MS>"
        '<Obj RefId="1" N="1"><TNRef RefId="0" />'
        "<LST><S>123</S><I32>123</I32></LST>"
        "</Obj>"
        "</MS>"
        "<LST><I32>0</I32><I32>1</I32><C>97</C><I32>2</I32></LST>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)

    actual = deserialize(element)
    assert isinstance(actual, collection.PSList)
    assert isinstance(actual, list)
    assert actual == [0, 1, PSChar("a"), 2]
    # Verify we can still index the list
    assert actual[0] == 0
    assert actual[1] == 1
    assert actual[2] == PSChar("a")
    assert actual[3] == 2

    # Verify we can access the extended prop using a string index.
    assert isinstance(actual["1"], collection.PSList)
    assert actual["1"] == collection.PSList(["123", 123])

    assert actual.PSTypeNames == ["System.Collections.ArrayList", "System.Object"]


@pytest.mark.parametrize(
    "input_value, expected",
    [
        ({}, "<DCT />"),
        ({"a": "a"}, '<DCT><En><S N="Key">a</S><S N="Value">a</S></En></DCT>'),
        ({"a": 1}, '<DCT><En><S N="Key">a</S><I32 N="Value">1</I32></En></DCT>'),
        (
            {1: PSChar("a"), PSInt64(10): ["abc", 456]},
            '<DCT><En><I32 N="Key">1</I32><C N="Value">97</C></En>'
            '<En><I64 N="Key">10</I64><Obj RefId="1" N="Value">'
            '<TN RefId="1"><T>System.Collections.ArrayList</T><T>System.Object</T></TN>'
            "<LST><S>abc</S><I32>456</I32></LST></Obj></En></DCT>",
        ),
    ],
)
def test_ps_dict(input_value, expected):
    ps_value = collection.PSDict(input_value)
    assert isinstance(ps_value, collection.PSDict)
    assert isinstance(ps_value, dict)

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8", method="xml").decode()
    expected = (
        f'<Obj RefId="0"><TN RefId="0"><T>System.Collections.Hashtable</T><T>System.Object</T></TN>'
        f"{expected}"
        f"</Obj>"
    )
    assert_xml_diff(actual, expected)

    actual = deserialize(element)
    assert isinstance(actual, collection.PSDict)
    assert isinstance(actual, dict)
    assert actual == input_value
    assert actual.PSTypeNames == ["System.Collections.Hashtable", "System.Object"]


def test_ps_dict_from_dict():
    element = serialize({"abc": "def", 1: 2, PSChar("a"): collection.PSList([1, 2])})
    actual = ElementTree.tostring(element, encoding="utf-8", method="xml").decode()
    expected = (
        '<Obj RefId="0"><TN RefId="0"><T>System.Collections.Hashtable</T><T>System.Object</T></TN>'
        "<DCT>"
        "<En>"
        '<S N="Key">abc</S>'
        '<S N="Value">def</S>'
        "</En>"
        "<En>"
        '<I32 N="Key">1</I32>'
        '<I32 N="Value">2</I32>'
        "</En>"
        "<En>"
        '<C N="Key">97</C>'
        '<Obj RefId="1" N="Value">'
        '<TN RefId="1"><T>System.Collections.ArrayList</T><T>System.Object</T></TN>'
        "<LST><I32>1</I32><I32>2</I32></LST>"
        "</Obj>"
        "</En>"
        "</DCT>"
        "</Obj>"
    )
    assert_xml_diff(actual, expected)


def test_ps_dict_with_properties():
    ps_value = collection.PSDict({})
    ps_value.PSObject.extended_properties.append(PSNoteProperty("key"))

    complex_prop = PSNoteProperty(COMPLEX_STRING)
    ps_value.PSObject.extended_properties.append(complex_prop)

    other_prop = PSNoteProperty("other", "prop")
    ps_value.PSObject.extended_properties.append(other_prop)

    # Setting a value will always set it in the dict, even adding a new dict entry if the prop exists
    ps_value["key"] = "dict"
    ps_value[COMPLEX_STRING] = "dict"

    # We can still set a property using dot notation like in PowerShell
    ps_value.key = "prop"

    # Or on the property object itself if we cannot access it like a Python attribute
    complex_prop.set_value("prop", ps_value)

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8", method="xml").decode()
    assert (
        actual == f'<Obj RefId="0"><TN RefId="0"><T>System.Collections.Hashtable</T><T>System.Object</T></TN>'
        f"<MS>"
        f'<S N="key">prop</S>'
        f'<S N="{COMPLEX_ENCODED_STRING}">prop</S>'
        f'<S N="other">prop</S>'
        f"</MS>"
        f"<DCT>"
        f'<En><S N="Key">key</S><S N="Value">dict</S></En>'
        f'<En><S N="Key">{COMPLEX_ENCODED_STRING}</S><S N="Value">dict</S></En>'
        f"</DCT>"
        f"</Obj>"
    )

    actual = deserialize(element)
    assert isinstance(actual, collection.PSDict)
    assert isinstance(actual, dict)
    assert str(actual) == f"{{'key': 'dict', {COMPLEX_STRING!r}: 'dict'}}"
    assert repr(actual) == f"{{'key': 'dict', {COMPLEX_STRING!r}: 'dict'}}"

    # In the case of a prop shadowing a dict, [] will favour the dict, and . will only get props
    assert actual["key"] == "dict"
    assert actual.key == "prop"

    # If only the prop exists under that name both [] and . will work
    assert actual["other"] == "prop"
    assert actual.other == "prop"

    # Because we cannot use special characters using the dot notation, we can only get shadowed props using the raw
    # PSObject property list
    assert actual.PSObject.extended_properties[1].name == COMPLEX_STRING
    assert actual.PSObject.extended_properties[1].get_value(actual) == "prop"


def test_ps_ienumerable():
    ps_value = collection.PSIEnumerable([0, 1, 2, 3, 4])
    assert isinstance(ps_value, collection.PSIEnumerable)
    assert isinstance(ps_value, list)

    element = serialize(ps_value)
    actual = ElementTree.tostring(element, encoding="utf-8", method="xml").decode()
    expected = (
        '<Obj RefId="0">'
        '<TN RefId="0">'
        "<T>System.Collections.IEnumerable</T>"
        "<T>System.Object</T>"
        "</TN>"
        "<IE>"
        "<I32>0</I32>"
        "<I32>1</I32>"
        "<I32>2</I32>"
        "<I32>3</I32>"
        "<I32>4</I32>"
        "</IE>"
        "</Obj>"
    )
    assert actual == expected

    actual = deserialize(element)
    assert isinstance(actual, collection.PSIEnumerable)
    assert isinstance(actual, list)
    assert str(actual) == "[0, 1, 2, 3, 4]"
    assert repr(actual) == "[0, 1, 2, 3, 4]"

    assert actual == [0, 1, 2, 3, 4]
    assert actual.PSTypeNames == ["System.Collections.IEnumerable", "System.Object"]
