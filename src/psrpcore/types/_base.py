# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""Defines the base objects used for PSObjects.

This file contains the base classes and the various metadata/glue that is used
to represent a PSObject as a PowerShell class. It also contains the code
required to define a custom .NET type and add properties to those types that
is known by the serializer.

Also define some helper functions to replicate functionality in PowerShell/.NET
like `-is`, `Add-Member` and so on.
"""

import abc
import enum
import inspect
import types
import typing

T = typing.TypeVar("T", bound=typing.Type["PSObject"])


class _UnsetValue(object):
    """Used to mark a property with an unset value."""

    def __new__(  # type: ignore[misc]  # This is a sentinel value so it's expected
        cls,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> typing.Type["_UnsetValue"]:
        return cls  # pragma: no cover


class _Singleton(type):
    """Singleton used by TypeRegistry to ensure only 1 registry exists."""

    __instances: typing.Dict[typing.Type, object] = {}

    def __call__(cls, *args: typing.Any, **kwargs: typing.Any) -> object:
        if cls not in cls.__instances:
            cls.__instances[cls] = super().__call__(*args, **kwargs)

        return cls.__instances[cls]


class TypeRegistry(metaclass=_Singleton):
    """Registry of all the Python classes that implement PSObject.

    This singleton is used to store all the classes that implement PSObject
    and the .NET type it implements. This is used for deserialization to
    provide a dynamic list of Python classes that can be dehydrated.
    """

    def __init__(self) -> None:
        self.type_registry: typing.Dict[str, typing.Type["PSObject"]] = {}
        self.element_registry: typing.Dict[str, typing.Type["PSObject"]] = {}

    def rehydrate(
        self,
        type_names: typing.List[str],
    ) -> typing.Union["PSObject", typing.Type[enum.Enum]]:
        """Rehydrate a blank instance based on the type names."""
        obj: typing.Union[PSObject, typing.Type[enum.Enum]]

        type_name = type_names[0] if type_names else None
        if type_name and type_name in self.type_registry:
            # Cannot call __init__ as it may be validating input arguments which the serializer does not specify when
            # rehydrating that type.
            cls = self.type_registry[type_name]
            if issubclass(cls, enum.Enum):
                # The deserializer will rehydrate the object by providing the value.
                obj = cls

            else:
                obj = cls.__new__(cls)

        else:
            # The type is not registered, return a PSObject with the type names set to 'Deserialized.<TN>'.
            obj = PSObject()
            obj.PSObject.type_names = [f"Deserialized.{tn}" for tn in type_names]

        return obj


class PSObjectMeta:
    """The PowerShell PSObject metadata.

    This describes the metadata around the PSObject such as the properties and
    ETS info. This information is used by Python to (de)serialize the Python
    class to a .NET type through CLIXML. This is typically assigned internally
    by the `:class:PSType` class decorator and shouldn't be
    assigned directly.

    Using `rehydrate=True` (default) will register the type_name of the class
    so the deserializer will return an instance of that class when it comes to
    deserializing that type. A rehydrated object is created without calling
    __init__() so any validation or set up that occurs in that function when
    normally creating the class instance will not occur during deserialization
    and only the properties in CLIXML will be set on the class instance. When
    `rehydrate=False` then the deserialized object will be an instance of
    `class:PSObject` with the type names containing the `Deserialized.` prefix.

    Args:
        type_names: List of .NET type names that the type implements, this
            should contain at least 1 type.
        adapted_properties: List of adapted properties, these are native to
            the .NET type.
        extended_properties: List of extended properties, these are added to
            the .NET type by PowerShell.
        rehydrate: Whether the type should be registered as rehydratable or
            not.

    Attributes:
        type_names (List[str]): See args.
        adapted_properties (List[PSPropertyInfo]): See args.
        extended_properties (List[PSPropertyInfo]): See args.
        rehydrate (bool): See args.
    """

    def __init__(
        self,
        type_names: typing.List[str],
        adapted_properties: typing.Optional[typing.List["PSPropertyInfo"]] = None,
        extended_properties: typing.Optional[typing.List["PSPropertyInfo"]] = None,
        *,
        rehydrate: bool = True,
    ):
        self.type_names = type_names
        self.adapted_properties = adapted_properties or []
        self.extended_properties = extended_properties or []
        self.rehydrate = rehydrate

        self._to_string: typing.Optional[str] = None
        self._instance: typing.Optional[PSObject] = None

    @property
    def to_string(self) -> typing.Optional[str]:
        """The string representation of the object.

        The value to use for the `<ToString>` element of the serialized object.
        Will favour an explicit `to_string` value if set otherwise it will fall
        back to the value of `str(instance)` that the meta is for.
        """
        if self._instance is None or self._to_string is not None:
            return self._to_string

        # If the instance class of this object has an explicit __str__ method defined we use that as the to_string
        # value. We only want to check up to the PSObject() parent class in the mro because that falls back to this
        # property.
        for cls in type(self._instance).__mro__:
            if cls == PSObject:
                break

            if "__str__" in cls.__dict__:
                return str(self._instance)

        return None

    @to_string.setter
    def to_string(
        self,
        value: str,
    ) -> None:
        """Explicitly set the `to_string` value."""
        self._to_string = value

    def set_instance(
        self,
        instance: typing.Union["PSObject", typing.Type["PSObject"]],
    ) -> None:
        """Creates a copy of meta and assign to the class or instance."""
        kwargs: typing.Dict[str, typing.Any] = {
            "adapted_properties": [],
            "extended_properties": [],
        }
        for prop_name, prop_value in kwargs.items():
            for prop in getattr(self, prop_name):
                prop_value.append(prop.copy())

        kwargs["type_names"] = list(self.type_names)
        kwargs["rehydrate"] = self.rehydrate
        copy = type(self)(**kwargs)

        # If setting on an instance fo a PSObject, assign the instance to the copy.
        if isinstance(instance, PSObject):
            copy._instance = instance

        setattr(instance, "PSObject", copy)


class PSPropertyInfo(metaclass=abc.ABCMeta):
    """Base metadata for an object property.

    This is an abstract class that defines the property behaviour when it comes
    to getting and setting a property. There are three types of properties that
    have been implemented:

        :class:`PSAliasProperty`:
            A property that points to another property, or Python attribute.
            This essentially creates a getter that calls `ps_object['target']`.

        :class:`PSNoteProperty`:
            A property that contains it's own value like a normal
            attribute/property in Python.

        :class:`PSScriptProperty`:
            A property that uses a callable to get and optionally set a value
            on the ps_object.

    The `mandatory` option controls whether the default `__init__()` function
    added to PSObjects without their own `__init__()` will validate that
    property was specified by the caller. This has no control over the
    serialization behaviour and any classes that define their own `__init__()`
    need to do their own validation.

    Args:
        name: The name of the property.
        mandatory: The property must be defined when creating a PSObject.
        ps_type: If set, the property value will be casted to this PSObject
            type.
        value: The default value to set for the property.
        getter: A callable to get the property value based on the caller's
            desired logic. Must not be set with `value`.
        setter: A callable to set the property value based on the caller's
            desired logic. Must not be set with `value`.

    Attributes:
        name (str): See args.
        ps_type (type): See args.
        mandatory (bool): See args.
    """

    def __init__(
        self,
        name: str,
        mandatory: bool = False,
        ps_type: typing.Optional[type] = None,
        value: typing.Optional[typing.Any] = _UnsetValue,
        getter: typing.Optional[typing.Callable[["PSObject"], typing.Any]] = None,
        setter: typing.Optional[typing.Callable[["PSObject", typing.Any], None]] = None,
    ):
        self.name = name
        self.ps_type = ps_type
        self.mandatory = mandatory

        self._value: typing.Union[typing.Type[_UnsetValue], PSObject] = _UnsetValue

        self._getter: typing.Optional[typing.Callable[["PSObject"], typing.Any]] = None
        if getter:
            self.getter = getter

        self._setter: typing.Optional[typing.Callable[["PSObject", typing.Any], None]] = None
        if setter:
            self.setter = setter

        if value != _UnsetValue:
            if getter:
                raise ValueError(f"Cannot set property value for '{self.name}' with a getter")

            # The PSObject is required when setting a value for a custom setter. Because we do not set a value if there
            # is a getter/setter present then this can be a random object without causing any issues.
            self.set_value(value, PSObject())

    @abc.abstractmethod
    def copy(self) -> "PSPropertyInfo":
        """Create a copy of the property."""
        pass  # pragma: no cover

    @property
    def getter(self) -> typing.Optional[typing.Callable[["PSObject"], typing.Any]]:
        """Returns the getter callable for the property if one was set."""
        return self._getter

    @getter.setter
    def getter(
        self,
        getter: typing.Callable[["PSObject"], None],
    ) -> None:
        if self._value != _UnsetValue:
            raise ValueError(f"Cannot add getter for '{self.name}': existing value already set")

        if getter is None:
            raise ValueError(f"Cannot unset property getter for '{self.name}'")

        self._validate_callable(getter, 1, "getter")
        self._getter = getter

    @property
    def setter(self) -> typing.Optional[typing.Callable[["PSObject", typing.Any], None]]:
        """Returns the setter callable for the property if one was set."""
        return self._setter

    @setter.setter
    def setter(
        self,
        setter: typing.Optional[typing.Callable[["PSObject", typing.Any], None]],
    ) -> None:
        if self.getter is None:
            raise ValueError(f"Cannot set property setter for '{self.name}' without an existing getter")

        elif setter is None:
            self._setter = None

        else:
            self._validate_callable(setter, 2, "setter")
            self._setter = setter

    def get_value(
        self,
        ps_object: "PSObject",
    ) -> typing.Any:
        """Get the property value.

        Gets the value of the property. If the property value is a callable
        then the value is invoked with the ps_object as an argument and the
        resulting value is casted to the `ps_type` if it is set.

        Args:
            ps_object: The PSObject instance the property is on. This is used
                when invoking a getter callable.

        Returns:
            (typing.Any): The value of the property.
        """
        getter = self.getter
        value: typing.Optional[typing.Union[typing.Type[_UnsetValue], PSObject]]

        if getter:
            raw_value = getter(ps_object)
            value = self._cast(raw_value)

        else:
            value = self._value

        if value == _UnsetValue:
            value = None

        return value

    def set_value(
        self,
        value: typing.Any,
        ps_object: "PSObject",
    ) -> None:
        """Set the property value.

        Sets the value of the property to the value specified. The value will
        be casted to the property's `ps_type` if defined unless it is a
        callable or `None`. Trying to set `None` on a `mandatory` property will
        also fail.

        Args:
            value: The value to set on the property.
            ps_object: The PSObject instance the property is on. This is used
                when invoking the setter callable.
        """
        setter = self.setter
        if setter:
            setter(ps_object, value)

        elif self.getter:
            raise ValueError(f"Cannot set value for a getter property '{self.name}' without a setter callable")

        else:
            self._value = self._cast(value)

    def _cast(self, value: typing.Any) -> "PSObject":
        """Try to cast the raw value to the property's ps_type if possible."""
        if value is not None and self.ps_type is not None and not isinstance(value, self.ps_type):
            return self.ps_type(value)

        else:
            return value

    def _validate_callable(
        self,
        func: typing.Callable,
        expected_count: int,
        use: str,
    ) -> None:
        """Validates the callable has the required argument count for use as a property getter/setter."""
        if not isinstance(func, types.FunctionType):
            raise TypeError(
                f"Invalid {use} callable for property '{self.name}': expecting callable not "
                f"{type(func).__qualname__}"
            )

        parameters = list(inspect.signature(func).parameters.values())
        required_count = 0
        total_count = 0

        for param in parameters:
            if param.kind in [inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD]:
                # func(arg1, .., /) or func(arg1, ...) - keep track of how many and if they must be set.
                total_count += 1
                if param.default == inspect.Parameter.empty:
                    required_count += 1

            elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                # Once we've reached *args we've counted all the positional args that could be used. It also means the
                # callable accepts an arbitrary amount of args so our expected count will be met.
                total_count = expected_count
                break

        def plural(name: str, count: int) -> str:
            s = "" if count == 1 else "s"
            return f"{count} {name}{s}"

        base_err = (
            f"Invalid {use} callable for property '{self.name}': signature expected "
            f"{plural('parameter', expected_count)} but"
        )
        if required_count > expected_count:
            raise TypeError(f"{base_err} {plural('required parameter', required_count)} were found")

        elif total_count < expected_count:
            raise TypeError(f"{base_err} {plural('parameter', total_count)} were found")


class PSAliasProperty(PSPropertyInfo):
    """Alias Property

    This is a property that gets a value based on another property or attribute
    of the PSObject. It is designed to replicate the functionality of
    `PSAliasProperty`_. During serialization the alias property will just copy
    the value of the target it is pointing to. You cannot set a value to an
    alias property, see :class:`PSScriptProperty` which allows the caller
    to define a way to get and set properties on an object dynamically.

    Note:
        When an object that has an alias property is deserialized, the property
        is converted to a :class:`PSNoteProperty` and the alias will no longer
        exist.

    Args:
        name: The name of the property.
        alias: The name of the property or attribute to point to.
        ps_type: If set, the property value will be casted to this PSObject
            type.

    Attributes:
        alias (str): The target of the alias.

    .. _PSAliasProperty:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.psaliasproperty
    """

    def __init__(
        self,
        name: str,
        alias: str,
        ps_type: typing.Optional[type] = None,
    ):
        self.alias = alias
        super().__init__(name, ps_type=ps_type, getter=lambda s: s[alias])

    def copy(self) -> "PSAliasProperty":
        return PSAliasProperty(self.name, self.alias, self.ps_type)


class PSNoteProperty(PSPropertyInfo):
    """Note Property

    This is a property that stores a value as a name-value pair. Is is designed
    to replicate the functionality of `PSNoteProperty`_ and is typically the
    type of property to use when creating a PSObject.

    Note:
        See :class:`PSPropertyInfo` for more information on the `mandatory`
        argument.

    Args:
        name: The name of the property.
        value: The property value to set, if omitted the default is `None`.
        mandatory: The property must be defined when creating a PSObject.
        ps_type: If set, the property value will be casted to this PSObject type.

    .. _PSNoteProperty:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.psnoteproperty
    """

    def __init__(
        self,
        name: str,
        value: typing.Optional[typing.Any] = _UnsetValue,
        mandatory: bool = False,
        ps_type: typing.Optional[type] = None,
    ):
        super().__init__(name, mandatory=mandatory, ps_type=ps_type, value=value)

    def copy(self) -> "PSNoteProperty":
        return PSNoteProperty(self.name, self._value, self.mandatory, self.ps_type)


class PSScriptProperty(PSPropertyInfo):
    """Script Property

    This is a property that can get and optionally set another property or
    attribute of a PSObject at runtime. It is designed to replicate the
    functionality of `PSScriptProperty`_.

    The getter callable must be a callable that has only 1 argument that is the
    PSObject the property is a member of. This allows the caller to retrieve a
    property of the PSObject at runtime or any other source as needed.

    The setter callable must be a callable that has only 2 arguments, the first
    being the value that needs to be set and the second is the PSObject the
    property is a member of. A setter must be defined on the property for a
    value to be set.

    Args:
        name: The name of the property.
        getter: The callable to run when getting a value for this property.
        setter: The callable to run when setting a value for this property.
        mandatory: The property must be defined when creating a PSObject.
        ps_type: If set, the property value will be casted to this PSObjec
             type.

    .. _PSScriptProperty:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.psscriptproperty
    """

    def __init__(
        self,
        name: str,
        getter: typing.Callable[["PSObject"], typing.Any],
        setter: typing.Optional[typing.Callable[["PSObject", typing.Any], None]] = None,
        mandatory: bool = False,
        ps_type: typing.Optional[type] = None,
    ):
        if getter is None:
            raise TypeError(f"Cannot create script property '{name}' with getter as None")

        if mandatory and not setter:
            raise TypeError(
                f"Cannot create mandatory {self.__class__.__qualname__} property '{name}' without a " f"setter callable"
            )

        super().__init__(name, mandatory=mandatory, ps_type=ps_type, getter=getter, setter=setter)

    def copy(self) -> "PSScriptProperty":
        return PSScriptProperty(
            self.name,
            self.getter,  # type: ignore[arg-type] # The class does not allow self.getter to be None
            self.setter,
            self.mandatory,
            self.ps_type,
        )


class PSObject:
    """The base PSObject type.

    This is the base PSObject type that all PS object classes must inherit. It
    controls all the behaviour around getting and setting attributes that are
    based on PowerShell properties in a way that is similar to PowerShell
    itself.

    When initialised directly this is a plain object without any properties.
    User :meth:`add_member` to add new properties dynamically.
    """

    PSObject = PSObjectMeta(
        type_names=[
            "System.Object",
        ]
    )  #: Class and instance attribute that defines the objects ETS.

    def __new__(  # type: ignore[no-untyped-def]  # Trying to set PSObject here sends mypy into haywire
        cls,
        *args: typing.Any,
        **kwargs: typing.Any,
    ):
        if super().__new__ is object.__new__ and cls.__init__ is not object.__init__:
            obj = super().__new__(cls)
        else:
            obj = super().__new__(cls, *args, **kwargs)

        # Make sure the class instance has a copy of the class PSObject so they aren't shared. Also add a reference to
        # the instance for that PSObject.
        cls.PSObject.set_instance(obj)

        return obj

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        # Skip creating a new object if we are trying to cast to the same type again.
        # if len(args) == 1 and type(args[0]) == cls:
        #    return args[0]

        # Favour extended properties in case there is one with the same name. This is how PowerShell's ETS works.
        prop_entries = {p.name: p for p in self.PSObject.adapted_properties}
        prop_entries.update({p.name: p for p in self.PSObject.extended_properties})

        # Make sure the number of positional args specified do not exceed the number of kwargs present.
        if len(args) > len(prop_entries):
            raise TypeError(
                f"__init__() takes {len(prop_entries) + 1} positional arguments but {len(args) + 1} " f"were given"
            )

        # Convert the args to kwargs based on the property order and check that they aren't also defined as a kwarg.
        caller_args = dict(zip(prop_entries.keys(), args))
        for name in caller_args.keys():
            if name in kwargs:
                raise TypeError(f"__init__() got multiple values for argument '{name}'")
        caller_args.update(kwargs)

        # Validate that any mandatory props were specified.
        # Cannot use set as it breaks the ordering which we want to preserve for the error msg.
        mandatory_props = [p.name for p in prop_entries.values() if p.mandatory]
        specified_props = list(caller_args.keys())
        missing_props = [p for p in mandatory_props if p not in specified_props]
        if missing_props:
            missing_list = "', '".join(missing_props)
            raise TypeError(f"__init__() missing {len(missing_props)} required arguments: '{missing_list}'")

        # Check that all the kwargs match the existing properties of the object and set the properties.
        for prop_name, raw_value in caller_args.items():
            if prop_name not in prop_entries:
                raise TypeError(f"__init__() got an unexpected keyword argument '{prop_name}'")

            setattr(self, prop_name, raw_value)

    @property
    def PSBase(self) -> None:
        """The raw .NET object without the extended type system properties."""
        raise NotImplementedError()  # pragma: no cover

    @property
    def PSAdapted(self) -> None:
        """A dict of all the adapted properties."""
        raise NotImplementedError()  # pragma: no cover

    @property
    def PSExtended(self) -> None:
        """A dict of all the extended properties."""
        raise NotImplementedError()  # pragma: no cover

    @property
    def PSTypeNames(self) -> typing.List[str]:
        """Shortcut to PSObject.type_names, one of PowerShell's reserved properties."""
        return self.PSObject.type_names

    def __setattr__(self, key: str, value: typing.Any) -> None:
        # __getattribute__ uses PSObject so bypass all that and just set it directly.
        if key == "PSObject":
            return super().__setattr__(key, value)

        # Get the raw untainted __dict__ value which does not include our object's PS properties that self.__dict__
        # will return. We use this to see whether we need to set the PSObject property or the Python object attribute.
        d = super().__getattribute__("__dict__")

        if key not in d:
            ps_object = self.PSObject

            # Extended props take priority, once we find a match we stopped checking.
            for prop_type in ["extended", "adapted"]:
                properties = getattr(ps_object, f"{prop_type}_properties")
                for prop in properties:
                    if prop.name == key:
                        prop.set_value(value, self)
                        return

        # If the key already exists in the __dict__ or it's a new attribute that's not a registered property, just
        # set the key/value to the object itself.
        super().__setattr__(key, value)

    def __getattribute__(self, item: str) -> typing.Any:
        # Use __getattribute__ instead of self.PSObject to avoid a recursive call.
        ps_object = super().__getattribute__("PSObject")

        # Extended props take priority over adapted props, by checking that last we ensure the prop will have that
        # value if there are duplicates.
        ps_properties = {}
        for prop_type in ["adapted", "extended"]:
            properties = getattr(ps_object, f"{prop_type}_properties")
            for prop in properties:
                ps_properties[prop.name] = prop

        # We want to favour the normal attributes Python would return before falling back to the properties on the
        # PSObject.
        try:
            val = super().__getattribute__(item)
        except AttributeError:
            if item not in ps_properties:
                raise

            return ps_properties[item].get_value(self)

        # A special case exists when returning __dict__. We want to have __dict__ return both the Python attributes as
        # well as the PSObject properties. This allows debuggers and people calling functions like vars()/dirs() to see
        # the PSObject properties automatically.
        if item == "__dict__":
            val = val.copy()  # Make sure we don't actually mutate the pure __dict__.
            val.update({name: prop.get_value(self) for name, prop in ps_properties.items()})

        return val

    def __getitem__(self, item: str) -> typing.Any:
        """Allow getting properties using the index syntax.

        By overriding __getitem__ you can access properties on an object using
        the index syntax, i.e. obj['PropertyName']. This matches the PowerShell
        behaviour where properties can be retrieved either by dot notation or
        by index notation.

        It also makes it easier to get properties with a name that aren't valid
        Python attribute names. By allowing a string field someone can do
        `obj['1 Invalid Attribute$']`. An alternative option is through
        getattr() as that accepts a string. This works because PSObject also
        override :func:`__getattr__` and :func:`__setattr__` and it edits the
        `__dict__` directly.

        This is complicated by the Dict/List/Stack/Queue types as we need this
        to preserve the actual lookup values. In those cases the __getitem__
        lookup will favour the base object items before falling back to looking
        at the attributes.
        """
        return getattr(self, item)

    def __setitem__(self, key: str, value: typing.Any) -> None:
        setattr(self, key, value)

    def __str__(self) -> str:
        if self.PSObject.to_string is not None:
            return self.PSObject.to_string

        else:
            return super().__str__()

    def __repr__(self) -> str:
        prop_entries = {p.name: p for p in self.PSObject.adapted_properties}
        prop_entries.update({p.name: p for p in self.PSObject.extended_properties})

        kw = ", ".join(f"{k}={v.get_value(self)!r}" for k, v in prop_entries.items())
        return f"{type(self).__name__}({kw})"


class PSType:
    """PSType class decorator.

    This is a class decorator that should be added to any Python class that
    represents a .NET type. It modifies the class to use the PowerShell type
    system like extended properties. A class that uses this decorator must
    inherit from :class:`PSObject`.

    If the class also has a base `PSType` class it will inherit all the types
    and properties of that base class unless `skip_inheritance=True` is set.

    Args:
        type_names: A list of .NET types the class represents.
        adapted_properties: A list of :class:`PSPropertyInfo` to denote the
            native .NET properties the class has.
        extended_properties: A list of :class:`PSPropertyInfo` to denote the
            extended PowerShell properties the class has.
        skip_inheritance: Skip inheriting the type and properties from the base
            class.
        rehydrate: Registers the type for deserialisation.
        tag: Used internally to denote the CLIXML element tag value.
    """

    def __init__(
        self,
        type_names: typing.List[str] = None,
        adapted_properties: typing.List[PSPropertyInfo] = None,
        extended_properties: typing.List[PSPropertyInfo] = None,
        *,
        skip_inheritance: bool = False,
        rehydrate: bool = True,
        tag: typing.Optional[str] = None,
    ):
        self.type_names = type_names or []
        self.adapted_properties = adapted_properties or []
        self.extended_properties = extended_properties or []
        self.skip_inheritance = skip_inheritance
        self.rehydrate = rehydrate
        self.tag = tag

    def __call__(
        self,
        cls: T,
    ) -> T:
        if not issubclass(cls, PSObject):
            raise TypeError(f"PSType class {cls.__module__}.{cls.__qualname__} must be a subclass of PSObject")

        if not self.skip_inheritance:
            self.type_names.extend(cls.PSObject.type_names)
            self.adapted_properties.extend(cls.PSObject.adapted_properties)
            self.extended_properties.extend(cls.PSObject.extended_properties)

        cls.PSObject = PSObjectMeta(self.type_names, self.adapted_properties, self.extended_properties)

        registry = TypeRegistry()

        if self.rehydrate and self.type_names and self.type_names[0] not in registry.type_registry:
            registry.type_registry[self.type_names[0]] = cls

        if self.tag is not None and self.tag not in registry.element_registry:
            registry.element_registry[self.tag] = cls

        return cls


class PSCryptoProvider(metaclass=abc.ABCMeta):
    """PSRemoting crypto provider

    The CryptoProvider used by PSRemoting that can encrypt and decrypt secure
    exchanged in that PSSession. The key must be registered once it has been
    generated using :meth:`PSCryptoProvider.register_key`.
    """

    @abc.abstractmethod
    def decrypt(self, value: bytes) -> bytes:
        """Decrypts the encrypted bytes.

        Decrypts the encrypted bytes passed in.

        Args:
            value: The encrypted bytes to decrypt.

        Returns:
            bytes: The decrypted bytes.
        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def encrypt(self, value: bytes) -> bytes:
        """Encrypted the bytes.

        Encrypts the bytes passed in.

        Args:
            value: The bytes to encrypt.

        Returns:
            bytes: The encrypted bytes.
        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def register_key(
        self,
        key: bytes,
    ) -> None:
        """Registers the session key.

        Registers the session key that is used to encrypt and decrypt secure
        strings for PSRP.

        Args:
            key: The session key negotiated between the client and server.
        """
        pass  # pragma: no cover


def add_member(
    obj: typing.Union[PSObject, typing.Type[PSObject]],
    prop: PSPropertyInfo,
    force: bool = False,
) -> None:
    """Add an extended property.

    This can add an extended property to a PSObject class or a specific
    instance of a class. This replicates some of the functionality in
    `Update-TypeData`_ and `Add-Member`_ in PowerShell. If a property under the
    same name already exists under that PSObject then `force=True` is required
    to replace it. The same applies if there is an existing adapted property on
    the object.

    See :meth:`add_alias_property`, :meth:`add_note_property`, and
    :meth:`add_script_property` for simplified versions of this function.

    Args:
        obj: The PSObject class or an instance of a PSObject class to add the
            extended property to.
        prop: The property to add to the object or class.
        force: Overwrite the existing property ``True`` or fail ``False``.

    .. _Update-TypeData:
        https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/update-typedata
    .. _Add-Member:
        https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/add-member
    """
    ps_object = getattr(obj, "PSObject", None)
    if not ps_object:
        raise ValueError("The passing in object does not contain the required PSObject attribute")

    prop_name = prop.name
    adapted_properties = {p.name: i for i, p in enumerate(ps_object.adapted_properties)}
    extended_properties = {p.name: i for i, p in enumerate(ps_object.extended_properties)}

    insert_idx = len(ps_object.extended_properties)
    if prop_name in adapted_properties or prop_name in extended_properties:
        if not force:
            raise RuntimeError(f"Property '{prop_name}' already exists on PSObject, use force=True to overwrite it")

        # If we had a duplicated extended prop, swap the older with the new one, adapted props stays the same.
        if prop_name in extended_properties:
            insert_idx = extended_properties[prop_name]
            ps_object.extended_properties.pop(insert_idx)

    ps_object.extended_properties.insert(insert_idx, prop)


def add_alias_property(
    obj: typing.Union[PSObject, typing.Type[PSObject]],
    name: str,
    alias: str,
    ps_type: typing.Optional[type] = None,
    force: bool = False,
) -> None:
    """Add an alias property to a PSObject.

    Adds an alias as an extended property to a PSObject class or a specific
    instance of a class.

    Args:
        obj: The PSObject to add the alias to.
        name: The name of the new alias property.
        alias: The alias target.
        ps_type: Optional PSObject type that the alias value will get casted to.
        force: Overwrite the existing property ``True`` or fail ``False``.
    """
    add_member(obj, PSAliasProperty(name, alias, ps_type=ps_type), force=force)


def add_note_property(
    obj: typing.Union[PSObject, typing.Type[PSObject]],
    name: str,
    value: typing.Any,
    ps_type: typing.Optional[type] = None,
    force: bool = False,
) -> None:
    """Add a note property to a PSObject.

    Adds a note property as an extended property to a PSObject class or a
    specific instance of a class. A note property is a simple key/value pair
    with a static value.

    Args:
        obj: The PSObject to add the note property to.
        name: The name of the new note property.
        value: The value of the new note property
        ps_type: Optional PSObject type that the value will get casted to.
        force: Overwrite the existing property ``True`` or fail ``False``.
    """
    add_member(obj, PSNoteProperty(name, value, ps_type=ps_type), force=force)


def add_script_property(
    obj: typing.Union[PSObject, typing.Type[PSObject]],
    name: str,
    getter: typing.Callable[["PSObject"], typing.Any],
    setter: typing.Optional[typing.Callable[["PSObject", typing.Any], None]] = None,
    ps_type: typing.Optional[type] = None,
    force: bool = False,
) -> None:
    """Add a script property to a PSObject.

    Adds a script property as an extended property to a PSObject class or a
    specific instance of a class. A script property has a callable getter and
    optional setter function that is run when the property's value is requested
    or set.

    Args:
        obj: The PSObject to add the alias to.
        name: The name of the new alias property.
        getter: The callable to run when getting a value for this property.
        setter: The callable to run when setting a value for this property.
        ps_type: Optional PSObject type that the alias value will get casted to.
        force: Overwrite the existing property ``True`` or fail ``False``.
    """
    add_member(obj, PSScriptProperty(name, getter, setter=setter, ps_type=ps_type), force=force)


def ps_isinstance(
    obj: PSObject,
    other: typing.Union[typing.Type[PSObject], typing.Tuple[typing.Type[PSObject], ...], str, typing.Tuple[str, ...]],
    ignore_deserialized: bool = False,
) -> bool:
    """Checks the inheritance of a PSObject.

    This checks if a PSObject is an instance of another PSObject. Instead of
    checking based on the Python inheritance rules it checks based on the
    .NET TypeNames set for that instance. The check will loop through the
    `PSTypeNames` of the obj passed in and see if any of those types match the
    first `PSTypeName` of any of the `other` objects referenced.

    If `check_deserialized=True`, then any types starting with `Deserialized.`
    will also match against the non-deserialized types, e.g.
    `Deserialized.System.Collections.Hashtable` will be an instance of
    `System.Collections.Hashtable`.

    Args:
        obj: The object to check if it is inherited from the other types.
        other: The type to check if obj is inherited from. Can also be a list
            of .NET types as a string.
        ignore_deserialized: Whether to treat `Deserialized.*` instances as
            they would be serialized.

    Returns:
        bool: Whether the obj is inherited from any of the other types in .NET.
    """

    def strip_deserialized(type_names: typing.List[str]) -> typing.List[str]:
        if not ignore_deserialized:
            return type_names

        new_names = []
        for name in type_names:
            if name.startswith("Deserialized."):
                name = name[13:]

            new_names.append(name)

        return new_names

    other_instances = other if isinstance(other, (list, tuple)) else [other]
    raw_other_types = []
    for o in other_instances:
        if isinstance(o, str):
            raw_other_types.append(o)
        elif hasattr(o, "PSObject"):
            raw_other_types.append(o.PSObject.type_names[0])

    obj_types = set(strip_deserialized(obj.PSTypeNames))
    desired_types = set(strip_deserialized(raw_other_types))
    matching_types = obj_types & desired_types

    return bool(matching_types)
