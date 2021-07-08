# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import re
import xml.etree.ElementTree as ElementTree

import pytest

import psrpcore.types._base as ps_base
from psrpcore.types import PSCustomObject, PSInt, PSString, PSUInt

from ..conftest import deserialize, serialize


def test_ps_note_property_set_value():
    prop = ps_base.PSNoteProperty("Property", ps_type=PSInt)
    prop.set_value("1", None)
    actual = prop.get_value(None)
    assert actual == 1
    assert isinstance(actual, PSInt)

    prop.set_value(None, None)
    assert prop.get_value(None) is None

    expected = re.escape("invalid literal for int() with base 10: 'a'")
    with pytest.raises(ValueError, match=expected):
        prop.set_value("a", None)


def test_ps_property_with_value_and_getter():
    class MasterProperty(ps_base.PSPropertyInfo):
        def copy(self):
            return self

    with pytest.raises(ValueError, match="Cannot set property value for 'Name' with a getter"):
        MasterProperty("Name", value="value", getter=lambda s: None)


def test_ps_property_set_getter_with_value():
    prop = ps_base.PSNoteProperty("Name", "value")

    with pytest.raises(ValueError, match="Cannot add getter for 'Name': existing value already set"):
        prop.getter = lambda s: None


def test_ps_property_set_getter_as_none():
    prop = ps_base.PSScriptProperty("Name", lambda s: None)

    with pytest.raises(ValueError, match="Cannot unset property getter for 'Name'"):
        prop.getter = None


def test_ps_property_unset_setter():
    prop = ps_base.PSScriptProperty("Name", lambda s: None, lambda s, v: None)
    prop.setter = None

    with pytest.raises(ValueError, match="Cannot set value for a getter property 'Name' without a setter callable"):
        prop.set_value("test", None)


def test_ps_property_getter_as_none():
    with pytest.raises(TypeError, match="Cannot create script property 'Name' with getter as None"):
        ps_base.PSScriptProperty("Name", None)


def test_ps_property_no_setter_but_mandatory():
    expected = "Cannot create mandatory PSScriptProperty property 'Name' without a setter callable"
    with pytest.raises(TypeError, match=expected):
        ps_base.PSScriptProperty("Name", lambda s: None, mandatory=True)


def test_ps_script_property_invalid_getter():
    def no_params():
        assert False

    def two_params(this, other):
        assert False

    def args_params(this, other, *args):
        assert False

    expected = re.escape(
        "Invalid getter callable for property 'Callable': signature expected 1 parameter but 0 " "parameters were found"
    )
    with pytest.raises(TypeError, match=expected):
        ps_base.PSScriptProperty("Callable", no_params)

    expected = re.escape(
        "Invalid getter callable for property 'Callable': signature expected 1 parameter but 2 "
        "required parameters were found"
    )
    with pytest.raises(TypeError, match=expected):
        ps_base.PSScriptProperty("Callable", two_params)

    expected = re.escape(
        "Invalid getter callable for property 'Callable': signature expected 1 parameter but 2 "
        "required parameters were found"
    )
    with pytest.raises(TypeError, match=expected):
        ps_base.PSScriptProperty("Callable", args_params)

    with pytest.raises(TypeError, match=expected):
        ps_base.PSScriptProperty("Callable", lambda x, y: None)

    expected = re.escape("Invalid getter callable for property 'Callable': expecting callable not str")
    with pytest.raises(TypeError, match=expected):
        ps_base.PSScriptProperty("Callable", "string")


def test_ps_script_property_invalid_setter():
    def no_params():
        assert False

    def one_param(this):
        assert False

    def only_kwargs(this, *, key=None):
        assert False

    def three_params(this, other, third):
        assert False

    expected = re.escape(
        "Invalid setter callable for property 'Callable': signature expected 2 parameters but 0 "
        "parameters were found"
    )
    with pytest.raises(TypeError, match=expected):
        ps_base.PSScriptProperty("Callable", one_param, no_params)

    expected = re.escape(
        "Invalid setter callable for property 'Callable': signature expected 2 parameters but 1 " "parameter were found"
    )
    with pytest.raises(TypeError, match=expected):
        ps_base.PSScriptProperty("Callable", one_param, one_param)

    with pytest.raises(TypeError, match=expected):
        ps_base.PSScriptProperty("Callable", one_param, only_kwargs)

    expected = re.escape(
        "Invalid setter callable for property 'Callable': signature expected 2 parameters but 3 "
        "required parameters were found"
    )
    with pytest.raises(TypeError, match=expected):
        ps_base.PSScriptProperty("Callable", one_param, three_params)

    with pytest.raises(TypeError, match=expected):
        ps_base.PSScriptProperty("Callable", one_param, lambda x, y, z: None)


def test_ps_script_property_setter_without_getter():
    prop = ps_base.PSNoteProperty("Callable")

    expected = re.escape("Cannot set property setter for 'Callable' without an existing getter")
    with pytest.raises(ValueError, match=expected):
        prop.setter = lambda s, v: None


def test_ps_object_with_script_property():
    @ps_base.PSType(
        type_names=["ScriptablePSObject"],
        extended_properties=[
            ps_base.PSScriptProperty(
                "ScriptMandatory", lambda s: s.world, lambda s, v: setattr(s, "world", v), mandatory=True
            ),
            ps_base.PSNoteProperty("NoteProperty", value="note value"),
            ps_base.PSScriptProperty("ScriptProperty", lambda s: s.test, ps_type=PSInt),
            ps_base.PSScriptProperty(
                "ScriptToNote", lambda s: s.NoteProperty, lambda s, v: setattr(s, "NoteProperty", v)
            ),
        ],
    )
    class ScriptablePSObject(ps_base.PSObject):
        @property
        def test(self):
            return "1"

        @property
        def world(self):
            return getattr(self, "_world", None)

        @world.setter
        def world(self, value):
            setattr(self, "_world", value)

    expected = re.escape("missing 1 required arguments: 'ScriptMandatory'")
    with pytest.raises(TypeError, match=expected):
        ScriptablePSObject()

    obj = ScriptablePSObject("hello")
    assert obj.ScriptProperty == 1
    assert isinstance(obj.ScriptProperty, PSInt)

    element = serialize(obj)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0"><T>ScriptablePSObject</T><T>System.Object</T></TN>'
        "<MS>"
        '<S N="ScriptMandatory">hello</S>'
        '<S N="NoteProperty">note value</S>'
        '<I32 N="ScriptProperty">1</I32>'
        '<S N="ScriptToNote">note value</S>'
        "</MS>"
        "</Obj>"
    )

    obj = deserialize(element)
    assert isinstance(obj, ScriptablePSObject)
    assert isinstance(obj.PSObject.extended_properties[0], ps_base.PSNoteProperty)
    assert isinstance(obj.PSObject.extended_properties[1], ps_base.PSNoteProperty)
    assert isinstance(obj.PSObject.extended_properties[2], ps_base.PSNoteProperty)
    # Not in the CLIXML so the original type was preservedy)
    assert isinstance(obj.PSObject.extended_properties[3], ps_base.PSNoteProperty)

    assert obj.world is None
    assert obj.ScriptMandatory == "hello"
    assert obj.NoteProperty == "note value"
    assert obj.ScriptProperty == 1
    assert isinstance(obj.ScriptProperty, PSInt)
    assert obj.ScriptToNote == "note value"

    obj = ScriptablePSObject("hello", ScriptToNote="other note")
    obj.world = None

    element = serialize(obj)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0"><T>ScriptablePSObject</T><T>System.Object</T></TN>'
        "<MS>"
        '<Nil N="ScriptMandatory" />'
        '<S N="NoteProperty">other note</S>'
        '<I32 N="ScriptProperty">1</I32>'
        '<S N="ScriptToNote">other note</S>'
        "</MS>"
        "</Obj>"
    )


def test_ps_object_with_aliases():
    @ps_base.PSType(
        type_names=["AliasPSObject"],
        extended_properties=[
            ps_base.PSNoteProperty("NoteProperty", mandatory=True),
            ps_base.PSAliasProperty("AliasToNote", "NoteProperty"),
            ps_base.PSAliasProperty("AliasWithType", "NoteProperty", ps_type=PSInt),
            ps_base.PSAliasProperty("AliasToAttr", "test"),
        ],
    )
    class AliasPSObject(ps_base.PSObject):
        def __str__(self):
            return self.__class__.__name__

        @property
        def test(self):
            return "abc"

        @property
        def none(self):
            return getattr(self, "_none", None)

        @none.setter
        def none(self, value):
            setattr(self, "_none", value)

    obj = AliasPSObject("1")
    assert obj.AliasToNote == "1"
    assert obj.AliasWithType == 1
    assert isinstance(obj.AliasWithType, PSInt)
    assert obj.AliasToAttr == "abc"

    element = serialize(obj)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0"><T>AliasPSObject</T><T>System.Object</T></TN>'
        "<MS>"
        '<S N="NoteProperty">1</S>'
        '<S N="AliasToNote">1</S>'
        '<I32 N="AliasWithType">1</I32>'
        '<S N="AliasToAttr">abc</S>'
        "</MS>"
        "<ToString>AliasPSObject</ToString>"
        "</Obj>"
    )

    obj = deserialize(element)
    assert isinstance(obj, AliasPSObject)
    assert isinstance(obj.PSObject.extended_properties[0], ps_base.PSNoteProperty)
    assert isinstance(obj.PSObject.extended_properties[1], ps_base.PSNoteProperty)
    assert isinstance(obj.PSObject.extended_properties[2], ps_base.PSNoteProperty)
    assert isinstance(obj.PSObject.extended_properties[3], ps_base.PSNoteProperty)
    assert obj.NoteProperty == "1"
    assert obj.AliasToNote == "1"
    assert obj.AliasWithType == 1
    assert isinstance(obj.AliasWithType, PSInt)
    assert obj.AliasToAttr == "abc"


def test_ps_object_invalid_init_args():
    @ps_base.PSType(
        type_names=["MyPSObject"],
        adapted_properties=[
            ps_base.PSNoteProperty("Property1"),
        ],
        extended_properties=[
            ps_base.PSNoteProperty("Property2"),
            ps_base.PSNoteProperty("Property3", value="default value"),
        ],
    )
    class MyPSObject(ps_base.PSObject):
        pass

    expected = re.escape("takes 4 positional arguments but 5 were given")
    with pytest.raises(TypeError, match=expected):
        MyPSObject(1, 2, 3, 4)

    expected = re.escape("got multiple values for argument 'Property2'")
    with pytest.raises(TypeError, match=expected):
        MyPSObject(1, 2, Property2="other")

    expected = re.escape("got an unexpected keyword argument 'Other'")
    with pytest.raises(TypeError, match=expected):
        MyPSObject(Other="fake")


def test_ps_object_shadowed_property():
    @ps_base.PSType(
        type_names=["MyPSShadowedObject"],
        adapted_properties=[
            ps_base.PSNoteProperty("Property"),
        ],
        extended_properties=[
            ps_base.PSNoteProperty("Property"),
        ],
    )
    class MyPSShadowedObject(ps_base.PSObject):
        def __str__(self):
            return "mock"

    obj = MyPSShadowedObject("positional")
    assert obj.Property == "positional"
    assert obj.PSObject.adapted_properties[0].get_value(None) is None  # ETS is favoured over Adapted props
    assert obj.PSObject.extended_properties[0].get_value(None) == "positional"

    element = serialize(obj)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0"><TN RefId="0"><T>MyPSShadowedObject</T><T>System.Object</T></TN>'
        '<Props><Nil N="Property" /></Props>'
        '<MS><S N="Property">positional</S></MS>'
        "<ToString>mock</ToString></Obj>"
    )

    obj = deserialize(element)
    assert isinstance(obj, ps_base.PSObject)
    assert isinstance(obj, MyPSShadowedObject)
    assert obj.PSObject.adapted_properties[0].get_value(None) is None
    assert obj.PSObject.extended_properties[0].get_value(None) == "positional"
    assert obj.Property == "positional"
    assert obj.PSTypeNames == ["MyPSShadowedObject", "System.Object"]

    obj = MyPSShadowedObject(Property="kwarg")
    assert obj.Property == "kwarg"
    assert obj.PSObject.adapted_properties[0].get_value(None) is None
    assert obj.PSObject.extended_properties[0].get_value(None) == "kwarg"


def test_ps_object_mandatory():
    @ps_base.PSType(
        type_names=["MandatoryPSObject"],
        extended_properties=[
            ps_base.PSNoteProperty("Mandatory", mandatory=True),
            ps_base.PSNoteProperty("MandatoryTyped", mandatory=True, ps_type=PSUInt),
        ],
    )
    class MandatoryPSObject(ps_base.PSObject):
        def __str__(self):
            # Ensure our serialization has a common value.
            return "mock"

    expected = re.escape("missing 2 required arguments: 'Mandatory', 'MandatoryTyped'")
    with pytest.raises(TypeError, match=expected):
        MandatoryPSObject()

    expected = re.escape("missing 1 required arguments: 'MandatoryTyped'")
    with pytest.raises(TypeError, match=expected):
        MandatoryPSObject("Mandatory")

    # With positional
    obj = MandatoryPSObject("Mandatory", 1)
    assert obj.Mandatory == "Mandatory"
    assert obj.MandatoryTyped == 1
    assert isinstance(obj.MandatoryTyped, PSUInt)

    # With kwargs
    obj = MandatoryPSObject(Mandatory="Mandatory", MandatoryTyped=1)
    assert obj.Mandatory == "Mandatory"
    assert obj.MandatoryTyped == 1
    assert isinstance(obj.MandatoryTyped, PSUInt)

    # With mixture
    obj = MandatoryPSObject("Mandatory", MandatoryTyped=1)
    assert obj.Mandatory == "Mandatory"
    assert obj.MandatoryTyped == 1
    assert isinstance(obj.MandatoryTyped, PSUInt)

    element = serialize(obj)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0"><TN RefId="0"><T>MandatoryPSObject</T><T>System.Object</T></TN>'
        '<MS><S N="Mandatory">Mandatory</S>'
        '<U32 N="MandatoryTyped">1</U32></MS>'
        "<ToString>mock</ToString>"
        "</Obj>"
    )

    obj = deserialize(element)
    assert isinstance(obj, ps_base.PSObject)
    assert isinstance(obj, MandatoryPSObject)
    assert obj.Mandatory == "Mandatory"
    assert isinstance(obj.Mandatory, PSString)
    assert obj.MandatoryTyped == 1
    assert isinstance(obj.MandatoryTyped, PSUInt)
    assert obj.PSTypeNames == ["MandatoryPSObject", "System.Object"]


def test_ps_object_with_init():
    @ps_base.PSType(
        type_names=["ObjectWithInit"],
        extended_properties=[
            ps_base.PSNoteProperty("Property"),
            ps_base.PSNoteProperty("Mandatory", mandatory=True),
        ],
    )
    class ObjectWithInit(ps_base.PSObject):
        def __init__(self, value):
            self.value = value

    # If __init__ is defined on the type then automatic validation and setting of props during init is not done.
    obj = ObjectWithInit("value")
    assert not obj.PSObject.extended_properties[0].mandatory
    assert obj.PSObject.extended_properties[1].mandatory
    assert obj.value == "value"
    assert obj.Property is None
    assert obj.Mandatory is None


def test_ps_object_with_multi_inheritance():
    class OtherObj:
        def __init__(self):
            self.value = "other"

    @ps_base.PSType(
        type_names=["MultiObj"],
        extended_properties=[
            ps_base.PSNoteProperty("Mandatory", mandatory=True),
            ps_base.PSNoteProperty("Property"),
        ],
    )
    class MultiObj(ps_base.PSObject, OtherObj):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            OtherObj.__init__(self)  # Needed to MultiObj __init__ is called.

    # If a class inherits PSObject and another class the automatic __init__ isn't called.
    with pytest.raises(TypeError, match="missing 1 required arguments: 'Mandatory'"):
        MultiObj()

    obj = MultiObj("value")
    assert obj.Mandatory == "value"
    assert obj.Property is None
    assert obj.PSObject.extended_properties[0].mandatory
    assert not obj.PSObject.extended_properties[1].mandatory
    assert obj.value == "other"


def test_ps_object_init_with_nested_inheritance():
    @ps_base.PSType(["EmptyParentPSObject"])
    class EmptyParentPSObject(ps_base.PSObject):
        pass

    @ps_base.PSType(
        type_names=["YounglingPSObject"],
        extended_properties=[
            ps_base.PSNoteProperty("Property"),
            ps_base.PSNoteProperty("Mandatory", mandatory=True),
        ],
    )
    class YounglingPSObject(EmptyParentPSObject):
        pass

    assert YounglingPSObject.PSObject.type_names == ["YounglingPSObject", "EmptyParentPSObject", "System.Object"]
    assert EmptyParentPSObject.PSObject.type_names == ["EmptyParentPSObject", "System.Object"]

    obj = YounglingPSObject("prop", "man")
    assert obj.Property == "prop"
    assert obj.Mandatory == "man"
    assert obj.PSObject.type_names == ["YounglingPSObject", "EmptyParentPSObject", "System.Object"]

    element = serialize(obj)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0"><T>YounglingPSObject</T><T>EmptyParentPSObject</T><T>System.Object</T></TN>'
        "<MS>"
        '<S N="Property">prop</S>'
        '<S N="Mandatory">man</S>'
        "</MS>"
        "</Obj>"
    )

    with pytest.raises(TypeError, match="missing 1 required arguments: 'Mandatory'"):
        YounglingPSObject()


def test_ps_object_init_properties_nested():
    @ps_base.PSType(
        type_names=["Nested1"],
        adapted_properties=[
            ps_base.PSNoteProperty("Adapted1Mandatory", mandatory=True),
            ps_base.PSNoteProperty("Adapted1"),
        ],
        extended_properties=[
            ps_base.PSNoteProperty("Extended1", ps_type=PSInt),
        ],
    )
    class Nested1(ps_base.PSObject):
        pass

    @ps_base.PSType(
        type_names=["Nested2"],
        extended_properties=[
            ps_base.PSNoteProperty("Extended2", mandatory=True),
        ],
    )
    class Nested2(Nested1):
        def __str__(self):
            return self.Adapted1Mandatory

    @ps_base.PSType(
        type_names=["Nested3"],
        extended_properties=[
            ps_base.PSNoteProperty("Extended3"),
        ],
    )
    class Nested3(Nested2):
        pass

    assert Nested1.PSObject.type_names == ["Nested1", "System.Object"]
    assert len(Nested1.PSObject.adapted_properties) == 2
    assert Nested1.PSObject.adapted_properties[0].name == "Adapted1Mandatory"
    assert Nested1.PSObject.adapted_properties[1].name == "Adapted1"
    assert len(Nested1.PSObject.extended_properties) == 1
    assert Nested1.PSObject.extended_properties[0].name == "Extended1"

    assert Nested2.PSObject.type_names == ["Nested2", "Nested1", "System.Object"]
    assert len(Nested2.PSObject.adapted_properties) == 2
    assert len(Nested2.PSObject.extended_properties) == 2
    assert Nested2.PSObject.extended_properties[0].name == "Extended2"

    assert Nested3.PSObject.type_names == ["Nested3", "Nested2", "Nested1", "System.Object"]
    assert len(Nested3.PSObject.adapted_properties) == 2
    assert len(Nested3.PSObject.extended_properties) == 3
    assert Nested3.PSObject.extended_properties[0].name == "Extended3"

    expected = re.escape("missing 2 required arguments: 'Adapted1Mandatory', 'Extended2'")
    with pytest.raises(TypeError, match=expected):
        Nested3()

    with pytest.raises(TypeError, match=expected):
        Nested3(Extended3="test")

    obj = Nested3(Adapted1Mandatory="adapted", Extended1="1", Extended2="extended 2")
    assert obj.Adapted1Mandatory == "adapted"
    assert obj.Adapted1 is None
    assert obj.Extended1 == 1
    assert obj.Extended2 == "extended 2"
    assert obj.Extended3 is None
    assert str(obj) == "adapted"

    element = serialize(obj)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0"><T>Nested3</T><T>Nested2</T><T>Nested1</T><T>System.Object</T></TN>'
        "<Props>"
        '<S N="Adapted1Mandatory">adapted</S>'
        '<Nil N="Adapted1" />'
        "</Props>"
        "<MS>"
        '<Nil N="Extended3" />'
        '<S N="Extended2">extended 2</S>'
        '<I32 N="Extended1">1</I32>'
        "</MS>"
        "<ToString>adapted</ToString>"
        "</Obj>"
    )

    obj = deserialize(element)
    assert isinstance(obj, Nested3)
    assert isinstance(obj, Nested2)
    assert isinstance(obj, Nested1)
    assert isinstance(obj, ps_base.PSObject)
    assert str(obj) == "adapted"
    assert obj.Adapted1Mandatory == "adapted"
    assert obj.Adapted1 is None
    assert obj.Extended1 == 1
    assert obj.Extended2 == "extended 2"
    assert obj.Extended3 is None


def test_ps_object_init_with_parent_init_inheritance():
    @ps_base.PSType(["OtherPSObject"])
    class OtherPSObject(ps_base.PSObject):
        def __init__(self, value):
            self.value = value

    @ps_base.PSType(
        type_names=["GrandPSObject"],
        extended_properties=[
            ps_base.PSNoteProperty("Property"),
            ps_base.PSNoteProperty("Mandatory", mandatory=True),
        ],
    )
    class GrandPSObject(OtherPSObject):
        pass

    # Needs to be a direct descendant to get the auto __init__ function
    with pytest.raises(TypeError, match="got an unexpected keyword argument 'Property'"):
        GrandPSObject("other", Property="abc")

    obj = GrandPSObject("other")
    assert not obj.PSObject.extended_properties[0].mandatory
    assert obj.PSObject.extended_properties[1].mandatory
    assert obj.value == "other"
    assert obj.Property is None
    assert obj.Mandatory is None


def test_dynamic_ps_object():
    obj = ps_base.PSObject()
    obj.PSObject.type_names = ["Type1", "Type2"]
    ps_base.add_note_property(obj, "NoteProperty", "note value")
    ps_base.add_alias_property(obj, "AliasProperty", "NoteProperty")

    element = serialize(obj)
    actual = ElementTree.tostring(element, encoding="utf-8").decode()
    assert (
        actual == '<Obj RefId="0">'
        '<TN RefId="0"><T>Type1</T><T>Type2</T></TN>'
        "<MS>"
        '<S N="NoteProperty">note value</S>'
        '<S N="AliasProperty">note value</S>'
        "</MS>"
        "</Obj>"
    )


def test_ps_object_dict():
    obj = ps_base.PSObject()
    obj.PSObject.type_names = ["Type1"]
    ps_base.add_note_property(obj, "NoteProperty", "note value")

    # The raw __dict__ does not contain our note properties, we add that to a copy.
    raw_dict = object.__getattribute__(obj, "__dict__")
    assert list(raw_dict.keys()) == ["PSObject"]

    actual = vars(obj)
    assert id(actual) != id(raw_dict)
    assert list(actual.keys()) == ["PSObject", "NoteProperty"]
    assert actual["NoteProperty"] == "note value"

    # Adding a value to our copy of __dict__ won't affect the obj itself
    actual["other"] = "other value"
    assert "other" not in object.__getattribute__(obj, "__dict__")

    with pytest.raises(AttributeError):
        obj.other


def test_add_member_properties():
    # Set up a base object for up to play with
    obj = PSCustomObject(Existing="value", Integer="1")
    obj.PSObject.adapted_properties.append(ps_base.PSNoteProperty("Adapted", "test"))

    ps_base.add_alias_property(obj, "Alias", "Existing")
    ps_base.add_alias_property(obj, "AliasTyped", "Integer", ps_type=PSInt)
    ps_base.add_note_property(obj, "Note", "note value")
    ps_base.add_script_property(obj, "Script", lambda s: s.Note)
    ps_base.add_script_property(obj, "ScriptSet", lambda s: s.AliasTyped, lambda s, v: setattr(s, "Integer", v))

    assert len(obj.PSObject.adapted_properties) == 1
    assert len(obj.PSObject.extended_properties) == 7
    assert isinstance(obj.PSObject.extended_properties[0], ps_base.PSNoteProperty)
    assert obj.PSObject.extended_properties[0].name == "Existing"
    assert isinstance(obj.PSObject.extended_properties[1], ps_base.PSNoteProperty)
    assert obj.PSObject.extended_properties[1].name == "Integer"
    assert isinstance(obj.PSObject.extended_properties[2], ps_base.PSAliasProperty)
    assert obj.PSObject.extended_properties[2].name == "Alias"
    assert isinstance(obj.PSObject.extended_properties[3], ps_base.PSAliasProperty)
    assert obj.PSObject.extended_properties[3].name == "AliasTyped"
    assert isinstance(obj.PSObject.extended_properties[4], ps_base.PSNoteProperty)
    assert obj.PSObject.extended_properties[4].name == "Note"
    assert isinstance(obj.PSObject.extended_properties[5], ps_base.PSScriptProperty)
    assert obj.PSObject.extended_properties[5].name == "Script"
    assert isinstance(obj.PSObject.extended_properties[6], ps_base.PSScriptProperty)
    assert obj.PSObject.extended_properties[6].name == "ScriptSet"

    assert obj.Alias == "value"
    assert obj.AliasTyped == 1
    assert isinstance(obj.AliasTyped, PSInt)
    assert obj.Note == "note value"
    assert obj.Script == "note value"
    assert obj.ScriptSet == 1
    assert isinstance(obj.ScriptSet, PSInt)

    obj.ScriptSet = "2"
    assert obj.AliasTyped == 2
    assert obj.ScriptSet == 2

    # Make sure the members were only added to that instance
    obj = PSCustomObject()
    assert obj.PSObject.adapted_properties == []
    assert obj.PSObject.adapted_properties == []


def test_add_member_against_existing():
    obj = PSCustomObject(Extended="extended")
    obj.PSObject.adapted_properties.append(ps_base.PSNoteProperty("Adapted", "adapted"))

    assert obj.Adapted == "adapted"
    assert obj.Extended == "extended"

    expected = re.escape("Property 'Adapted' already exists on PSObject, use force=True to overwrite it")
    with pytest.raises(RuntimeError, match=expected):
        ps_base.add_note_property(obj, "Adapted", "new adapted")

    expected = re.escape("Property 'Extended' already exists on PSObject, use force=True to overwrite it")
    with pytest.raises(RuntimeError, match=expected):
        ps_base.add_note_property(obj, "Extended", "new extended")

    ps_base.add_note_property(obj, "Adapted", "new adapted", force=True)
    ps_base.add_note_property(obj, "Extended", "new extended", force=True)

    assert obj.Adapted == "new adapted"
    assert obj.Extended == "new extended"

    assert len(obj.PSObject.adapted_properties) == 1
    assert obj.PSObject.adapted_properties[0].name == "Adapted"
    assert obj.PSObject.adapted_properties[0].get_value(obj) == "adapted"

    assert len(obj.PSObject.extended_properties) == 2
    assert obj.PSObject.extended_properties[0].name == "Extended"
    assert obj.PSObject.extended_properties[0].get_value(obj) == "new extended"
    assert obj.PSObject.extended_properties[1].name == "Adapted"
    assert obj.PSObject.extended_properties[1].get_value(obj) == "new adapted"


def test_add_member_against_object_class():
    @ps_base.PSType(
        type_names=["MutatedClass"],
    )
    class MutatedClass(ps_base.PSObject):
        pass

    first = MutatedClass()
    assert len(first.PSObject.adapted_properties) == 0
    assert len(first.PSObject.extended_properties) == 0

    ps_base.add_alias_property(MutatedClass, "Alias", "Note")
    ps_base.add_note_property(MutatedClass, "Note", "note value")
    ps_base.add_script_property(MutatedClass, "Script", lambda s: s.Alias)

    assert len(MutatedClass.PSObject.adapted_properties) == 0
    assert len(MutatedClass.PSObject.extended_properties) == 3
    assert isinstance(MutatedClass.PSObject.extended_properties[0], ps_base.PSAliasProperty)
    assert MutatedClass.PSObject.extended_properties[0].name == "Alias"
    assert isinstance(MutatedClass.PSObject.extended_properties[1], ps_base.PSNoteProperty)
    assert MutatedClass.PSObject.extended_properties[1].name == "Note"
    assert isinstance(MutatedClass.PSObject.extended_properties[2], ps_base.PSScriptProperty)
    assert MutatedClass.PSObject.extended_properties[2].name == "Script"

    # Verify existing classes aren't mutated
    assert len(first.PSObject.adapted_properties) == 0
    assert len(first.PSObject.extended_properties) == 0

    # Verify new class instances are
    second = MutatedClass()
    assert len(second.PSObject.adapted_properties) == 0
    assert len(second.PSObject.extended_properties) == 3
    assert isinstance(second.PSObject.extended_properties[0], ps_base.PSAliasProperty)
    assert second.PSObject.extended_properties[0].name == "Alias"
    assert isinstance(second.PSObject.extended_properties[1], ps_base.PSNoteProperty)
    assert second.PSObject.extended_properties[1].name == "Note"
    assert isinstance(second.PSObject.extended_properties[2], ps_base.PSScriptProperty)
    assert second.PSObject.extended_properties[2].name == "Script"

    assert second.Alias == "note value"
    assert second.Note == "note value"
    assert second.Script == "note value"


def test_ps_isinstance_from_string():
    ps_string = PSString()

    assert ps_base.ps_isinstance(ps_string, "System.String")
    assert ps_base.ps_isinstance(ps_string, ("System.Int32", "System.String"))
    assert ps_base.ps_isinstance(ps_string, "System.Object")
    assert not ps_base.ps_isinstance(ps_string, "System.Int32")


def test_ps_instance_from_ps_type():
    ps_string = PSString()

    assert ps_base.ps_isinstance(ps_string, PSString)
    assert ps_base.ps_isinstance(ps_string, (PSInt, PSString))
    assert not ps_base.ps_isinstance(ps_string, PSInt)


def test_ps_instance_with_deserialized_object():
    @ps_base.PSType(
        type_names=["Deserialized.My.Other", "Deserialized.Intermediate", "Deserialzied.Object"],
    )
    class MyDeserialized1(ps_base.PSObject):
        pass

    @ps_base.PSType(
        type_names=["Deserialized.Intermediate", "Deserialzied.Object"],
    )
    class MyDeserialized2(ps_base.PSObject):
        pass

    @ps_base.PSType(
        type_names=["My.Other", "Intermediate", "ect"],
    )
    class Serialized(ps_base.PSObject):
        pass

    obj = MyDeserialized1()
    assert ps_base.ps_isinstance(obj, MyDeserialized1)
    assert ps_base.ps_isinstance(obj, MyDeserialized2)
    assert not ps_base.ps_isinstance(obj, Serialized)
    assert ps_base.ps_isinstance(obj, Serialized, ignore_deserialized=True)


def test_fail_to_create_ps_type_without_ps_object():

    with pytest.raises(TypeError, match=r"PSType class [\w_\.<>]+ must be a subclass of PSObject"):

        @ps_base.PSType()
        class MyClass:
            pass


def test_fail_add_member_no_ps_object():
    expected = re.escape("The passing in object does not contain the required PSObject attribute")

    with pytest.raises(ValueError, match=expected):
        ps_base.add_note_property("", "test", "value")
