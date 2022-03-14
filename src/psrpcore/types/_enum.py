# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""PSRP/.NET Enum Types.

The base classes for any .NET enum type.
"""

import enum
import typing

from psrpcore.types._base import PSType
from psrpcore.types._primitive import PSInt, PSIntegerBase


class PSEnumMeta(enum.EnumMeta):
    """The meta type for all PowerShell enum objects.

    This is the meta type that extends the enum meta type to support .NET enum
    specific info. Any .NET enum type can specify ``base_type`` as a PS integer
    type to change the fundamental integer type each enum value is based on. By
    default it is :class:`PSInt`.

    This class is used internally and is not designed for public consumption.
    You should inherit from the existing base classes that have already set
    this as their metaclass.
    """

    @classmethod
    def __prepare__(
        metacls,
        __name: str,
        __bases: typing.Tuple[type, ...],
        **kwds: typing.Any,
    ) -> typing.Mapping[str, typing.Any]:
        # Python <3.9 will fail when passing the kwds if base_type was specified, it's omitted entirely here.
        return super().__prepare__(__name, __bases)

    def __new__(
        mcls,
        name: str,
        bases: typing.Tuple[type, ...],
        namespace: typing.Dict[str, typing.Any],
        **kw: typing.Type[PSIntegerBase],
    ) -> "PSEnumMeta":
        # Ensure the enum values are casted to the PS integer type for serialization.
        base_type = kw.get("base_type", PSInt)
        if not isinstance(base_type, type) or not issubclass(base_type, PSIntegerBase):
            raise TypeError(f"PSEnumType {name} base_type must be a subclass of PSIntegerBase")

        def new(cls: typing.Type, val: typing.Any) -> typing.Type:
            val = base_type(val)
            obj = int.__new__(cls, val)
            obj._value_ = val

            return obj

        namespace["__new__"] = new

        return super().__new__(
            mcls,
            name,
            bases,
            namespace,  # type: ignore[arg-type] # _EnumDict is private so cannot be used properly
        )


@PSType(["System.Enum", "System.ValueType"], rehydrate=False)
class PSEnumBase(PSIntegerBase, enum.Enum, metaclass=PSEnumMeta):
    """The base enum PSObject type.

    This is the base enum PSObject type that all enum complex objects should
    inherit from. Any objects that inherit `PSEnumBase` and require a base type
    that is not :class:`PSInt` should set `base_type=...` when declaring the
    class.

    An example enum would look like:

    .. code-block:: python

        @PSType(["System.MyEnum"])
        class MyEnum(PSEnumBase):
            Label = 1
            Other = 2

        @PSType(["System.MyUIntEnum"])
        class MyUIntEnum(PSEnumBase, base_type=PSUInt):
            Label = 1
            Other = 0xFFFFFFFF

    A user of that enum would then access it like `MyEnum.Label` or
    `MyEnum.Other`. This class is designed for enums that allow only 1 value,
    if you require a flag like enum, use :class:`PSFlagBase` as the base type.
    """

    def __repr__(self) -> str:
        return enum.Enum.__repr__(self)

    def __str__(self) -> str:
        return enum.Enum.__str__(self)


@PSType(["System.Enum", "System.ValueType"], rehydrate=False)
class PSFlagBase(PSIntegerBase, enum.Flag, metaclass=PSEnumMeta):
    """The base flags enum PSObject type.

    This is like :class:`PSEnumBase` but supports having multiple values set
    like `[Flags]` on an enum in .NET. Using any bitwise operations will
    preserve the type so `MyFlags.Flag1 | MyFlags.Flag2` will still be an
    instance of `MyFlags`.

    Like :class:`PSEnumBase`, an implementing type can set `base_type` to
    another PS integer type if the base integer type is not Int32. An example
    flag enum would look like:

    .. code-block:: python

        @PSType(["System.MyFlags"])
        class MyFlags(PSFlagBase):
            Flag1 = 1
            Flag2 = 2
            Flag3 = 4

        @PSType(["System.MyUIntFlags"])
        class MyUIntFlags(PSFlagBase, base_type=PSUInt):
            Flag1 = 1
            Flag2 = 2
            Flag3 = 4
            All = 0xFFFFFFFF
    """

    # We ignore most of these mypy errors due to the weird __mro__ setup

    @classmethod
    def _missing_(cls, value):  # type: ignore[no-untyped-def]
        # Calls the unbound func so it runs the operations against our class.
        return enum.IntFlag._missing_.__func__(cls, value)  # type: ignore[attr-defined]

    @classmethod
    def _create_pseudo_member_(cls, value):  # type: ignore[no-untyped-def]
        # Calls the unbound func so it runs the operations against our class.
        return enum.IntFlag._create_pseudo_member_.__func__(cls, value)  # type: ignore[attr-defined]

    def __or__(self, other):  # type: ignore[no-untyped-def]
        return enum.IntFlag.__or__(self, other)

    def __and__(self, other):  # type: ignore[no-untyped-def]
        return enum.IntFlag.__and__(self, other)

    def __xor__(self, other):  # type: ignore[no-untyped-def]
        return enum.IntFlag.__xor__(self, other)

    def __ror__(self, other):  # type: ignore[no-untyped-def]
        return enum.IntFlag.__or__(self, other)

    def __rand__(self, other):  # type: ignore[no-untyped-def]
        return enum.IntFlag.__and__(self, other)

    def __rxor__(self, other):  # type: ignore[no-untyped-def]
        return enum.IntFlag.__xor__(self, other)

    def __invert__(self):  # type: ignore[no-untyped-def]
        return enum.IntFlag.__invert__(self)

    def __repr__(self) -> str:
        return enum.IntFlag.__repr__(self)

    def __str__(self) -> str:
        return enum.IntFlag.__str__(self)
