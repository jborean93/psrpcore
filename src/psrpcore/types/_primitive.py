# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""PSRP/.NET Primitive Types.

The PSRP/.NET Primitive Type class definitions. A primitive type is a
fundamental type, like strings, ints, etc, that typically only represent a
single value. Some of the lines are blurred with certain types but the ones
defined here are what is documented under
`MS-PSRP 2.2.5.1 Serialization of Primitive Type Objects`_ with the exception
of the Progress and Information records which are complex types.

.. _MS-PSRP 2.2.5.1 Serialization of Primitive Type Objects:
    https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/c8c85974-ffd7-4455-84a8-e49016c20683
"""

import base64
import datetime
import decimal
import enum
import operator
import re
import struct
import typing
import uuid

from psrpcore.types._base import PSCryptoProvider, PSObject, PSType

# Used by PSVersion to validate the string input. Must be int.int with an optional 3rd and 4th integer values.
_VERSION_PATTERN = re.compile(
    r"""
^
(?P<major>0|[1-9]\d*)               # The major version, can only have a leading 0 if that's the only value.
\.
(?P<minor>0|[1-9]\d*)               # The minor version.
(?:
    \.(?P<build>0|[1-9]\d*)         # The optional build version.
    (?:
        \.(?P<revision>0|[1-9]\d*)  # The optional revision version.
    )?
)?                                  # The 3rd and 4th versions are optional, we just require major.minor.
$
""",
    re.VERBOSE,
)


def _ensure_types_and_self(
    valid_types: typing.Union[type, typing.List[type]],
) -> typing.Callable:
    """Decorator that validates the first and only argument is either the current instance or the supplied types."""
    types_to_check: typing.List[typing.Type] = valid_types if isinstance(valid_types, list) else [valid_types]

    def decorator(func: typing.Callable) -> typing.Callable:
        def wrapped(self: PSObject, other: object) -> typing.Any:
            types_to_check.append(type(self))
            if not isinstance(other, tuple(types_to_check)):
                return NotImplemented

            return func(self, other)

        return wrapped

    return decorator


def _timedelta_total_nanoseconds(
    timedelta: typing.Union["PSDuration", datetime.timedelta],
) -> int:
    """Get the duration in nanoseconds of a timedelta object.

    The datetime.timedelta class has a `total_seconds()` func but on some
    platforms it looses microsecond accuracy when the duration exceeds 270
    years. This can be an issue because a .NET TimeSpan can span to ~30000
    years. So this provides the total nanoseconds as one integer rather than
    the seconds as a float with limited decimal precision. This is used by both
    the PSDuration `__new__()` method and by the serializer.py code.

    Args:
        timedelta: The PSDuration or timedelta object to get the total
            nanosecond duration for.

    Returns:
        int: The total number of nanoseconds the timedelta represents.
    """
    # nanoseconds are an extra attribute added by PSDuration but not present in datetime.timedelta
    nanoseconds = getattr(timedelta, "nanoseconds", 0)
    nanoseconds += timedelta.microseconds * 1000
    nanoseconds += timedelta.seconds * 1000000000
    nanoseconds += timedelta.days * 86400000000000

    return nanoseconds


class PSIntegerBase(PSObject, int):
    """Base class for integer based primitive types.

    This is the base class to use for primitive integer types. It defines
    common functions required to seamlessly use numerical operators like
    `|`, `<`, `&`, etc while preserving the type. It should not be initialised
    directly but is inherited by the various primitive integer types.
    """

    MinValue = 0
    MaxValue = 0

    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> "PSIntegerBase":
        if cls == PSIntegerBase:
            raise TypeError(
                f"Type {cls.__qualname__} cannot be instantiated; it can be used only as a base class for "
                f"integer types."
            )

        num = None
        if args:
            if args[0] is None:
                # In .NET integer cannot be null and PowerShell casts it to 0.
                num = 0

            elif isinstance(args[0], enum.Enum):
                num = args[0].value

        if num is None:
            num = super().__new__(cls, *args, **kwargs)

        if cls != type(num):
            # If the value is not the exact instance recreate it from an actual int.
            return super().__new__(cls, int(num))

        if num < cls.MinValue or num > cls.MaxValue:
            raise ValueError(
                f"Cannot create {cls.__qualname__} with value '{num}': Value must be between "
                f"{cls.MinValue} and {cls.MaxValue}."
            )

        return num

    def __init__(
        self,
        x: typing.Union[int, str],
        base: int = 10,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(*args, **kwargs)

    def __repr__(self) -> str:
        return int.__repr__(self)

    def __str__(self) -> str:
        # Use the PSObject.to_string in case this was a deserialized enum
        return self.PSObject._to_string if self.PSObject._to_string is not None else int.__str__(self)

    def __abs__(self) -> "PSIntegerBase":
        return type(self)(super().__abs__())

    def __and__(self, n: int) -> "PSIntegerBase":
        return type(self)(super().__and__(n))

    def __add__(self, x: int) -> "PSIntegerBase":
        return type(self)(super().__add__(x))

    def __divmod__(self, x: int) -> typing.Tuple["PSIntegerBase", int]:
        quotient, remainder = super().__divmod__(x)
        return type(self)(quotient), remainder

    def __floordiv__(self, x: int) -> "PSIntegerBase":
        return type(self)(super().__floordiv__(x))

    def __invert__(self) -> "PSIntegerBase":
        return type(self)(super().__invert__())

    def __lshift__(self, n: int) -> "PSIntegerBase":
        return type(self)(super().__lshift__(n))

    def __mod__(self, x: int) -> "PSIntegerBase":
        return type(self)(super().__mod__(x))

    def __mul__(self, x: int) -> "PSIntegerBase":
        return type(self)(super().__mul__(x))

    def __neg__(self) -> "PSIntegerBase":
        return type(self)(super().__neg__())

    def __or__(self, n: int) -> "PSIntegerBase":
        return type(self)(super().__or__(n))

    def __pos__(self) -> "PSIntegerBase":
        return type(self)(super().__pos__())

    def __pow__(self, *args: typing.Any, **kwargs: typing.Any) -> "PSIntegerBase":  # type: ignore[override]
        val = super().__pow__(*args, **kwargs)
        return type(self)(val)

    def __rshift__(self, n: int) -> "PSIntegerBase":
        return type(self)(super().__rshift__(n))

    def __sub__(self, x: int) -> "PSIntegerBase":
        return type(self)(super().__sub__(x))

    def __xor__(self, n: int) -> "PSIntegerBase":
        return type(self)(super().__xor__(n))


class PSStringBase(PSObject, str):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__()

    def __repr__(self) -> str:
        return str.__repr__(self)

    def __str__(self) -> str:
        return str.__str__(self)

    def __getitem__(self, item: typing.Union[int, str, "typing.SupportsIndex", slice]) -> "PSStringBase":
        # Allows slicing alongside getting extended properties which preserves the underlying type.
        if isinstance(item, str):
            return super().__getitem__(item)

        else:
            # String indexing, need to preserve the type.
            return type(self)(str.__getitem__(self, item))


@PSType(["System.String"], tag="S")
class PSString(PSStringBase):
    """The String primitive type.

    This is the string primitive type which represents the following types:

        Python: :class:`str`

        Native Serialization: yes

        PSRP: `[MS-PSRP] 2.2.5.1.1 String`_

        .NET: `System.String`_

    .. _[MS-PSRP] 2.2.5.1.1 String:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/052b8c32-735b-49c0-8c24-bb32a5c871ce

    .. _System.String:
        https://docs.microsoft.com/en-us/dotnet/api/system.string?view=net-5.0
    """


@PSType(["System.Char", "System.ValueType"], tag="C")
class PSChar(PSObject, int):
    """The Char primitive type.

    This is the char primitive type which represents the following types:

        Python: :class:`int`

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.1.2 Character`_

        .NET: `System.Char`_

    A char in .NET represents a UTF-16 codepoint from `u0000` to `uFFFF`.
    The codepoint may represent an invalid unicode character, say it's 1 half
    of a surrogate pair, but it's still a valid Char. A PSChar can be
    initialized just like an `int()` as long as the value is from `0` to
    `65535` inclusive. A PSChar can also be initialized from a single string
    character like `PSChar('a')`, any byte strings will be encoded as UTF-8
    when getting the character. If a decimal value is used as a string then the
    PSChar instance will be the value of that codepoint of the character and
    not the decimal value itself.

    .. _[MS-PSRP] 2.2.5.1.2 Character:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/ff6f9767-a0a5-4cca-b091-4f15afc6e6d8

    .. _System.Char:
        https://docs.microsoft.com/en-us/dotnet/api/system.char?view=net-5.0
    """

    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> "PSChar":
        raw_args = list(args)

        if isinstance(raw_args[0], bytes):
            raw_args[0] = raw_args[0].decode("utf-8")

        if isinstance(raw_args[0], str):
            # Ensure we are dealing with a UTF-8 string before converting to UTF-16
            b_value = raw_args[0].encode("utf-16-le")
            if len(b_value) > 2:
                raise ValueError("A PSChar must be 1 UTF-16 codepoint.")

            raw_args[0] = struct.unpack("<H", b_value)[0]

        char = super().__new__(cls, *raw_args, **kwargs)
        if char < 0 or char > 65535:
            raise ValueError("A PSChar must be between 0 and 65535.")

        return char

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__()

    def __str__(self) -> str:
        # While backed by an int value, the str representation should be the char it represents.
        return str(chr(self))

    def __repr__(self) -> str:
        return int.__repr__(self)


PSBool = bool
"""The Boolean primitive type.

This is the bool primitive type which represents the following types:

    Python: :class:`bool`

    Native Serialization: yes

    PSRP: `[MS-PSRP] 2.2.5.1.3 Boolean`_

    .NET: `System.Boolean`_

Cannot subclass bool due to a limitation on Python. This unfortunately means
we can't represent an extended primitive object of this type in Python as well.

.. _[MS-PSRP] 2.2.5.1.3 Boolean:
    https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/8b4b1067-4b58-46d5-b1c9-b881b6e7a0aa

.. _System.Boolean:
    https://docs.microsoft.com/en-us/dotnet/api/system.boolean?view=net-5.0
"""


@PSType(["System.DateTime", "System.ValueType"], tag="DT")
class PSDateTime(PSObject, datetime.datetime):
    """The Date/Time primitive type.

    This is the datetime primitive type which represents the following types:

        Python: obj:`datetime.datetime`

        Native Serialization: yes

        PSRP: `[MS-PSRP] 2.2.5.1.4 Date/Time`_

        .NET: `System.DateTime`_


    This extends the Python datetime.datetime class and adds a `nanosecond`
    attribute to track the nanoseconds. While the class can have a nanosecond
    precision, a serialized DateTime object can only go up to a .NET Tick which
    is 100s of nanoseconds.

    .. _[MS-PSRP] 2.2.5.1.4 Date/Time:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/a3b75b8d-ad7e-4649-bb82-cfa70f54fb8c

    .. _System.DateTime:
        https://docs.microsoft.com/en-us/dotnet/api/system.datetime?view=net-5.0
    """

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__()
        self.nanosecond = getattr(self, "nanosecond", None) or 0

    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> "PSDateTime":
        nanosecond = 0
        if "nanosecond" in kwargs:
            nanosecond = kwargs.pop("nanosecond")

        if args and isinstance(args[0], datetime.datetime):
            dt = args[0]
            instance = super().__new__(
                cls,
                dt.year,
                dt.month,
                dt.day,
                hour=dt.hour,
                minute=dt.minute,
                second=dt.second,
                microsecond=dt.microsecond,
                tzinfo=dt.tzinfo,
                fold=dt.fold,
            )

        else:
            instance = super().__new__(cls, *args, **kwargs)

        instance.nanosecond = nanosecond
        return instance

    def __repr__(self) -> str:
        datetime_repr = datetime.datetime.__repr__(self)[:-1]
        return f"{datetime_repr}, nanosecond={self.nanosecond})"

    def __str__(self) -> str:
        date = f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

        time = f"{self.hour:02d}:{self.minute:02d}:{self.second:02d}"
        if self.microsecond or self.nanosecond:
            nanosecond = f"{self.nanosecond:03d}" if self.nanosecond else ""
            microsecond = f"{self.microsecond:06d}"
            time += f".{microsecond}{nanosecond}"

        offset = ""
        off = self.utcoffset()
        if off is not None:
            plus_or_minus = "+" if off.days >= 0 else "-"
            off = abs(off)
            hours, minutes_off = divmod(off, datetime.timedelta(hours=1))
            minutes, seconds = divmod(minutes_off, datetime.timedelta(minutes=1))

            # While Python does support tz with an offset of less than minutes, .NET does not.
            offset = f"{plus_or_minus}{hours:02d}:{minutes:02d}"

        return f"{date} {time}{offset}"

    def __add__(
        self,
        other: datetime.timedelta,
    ) -> "PSDateTime":
        nanosecond_diff = self.nanosecond + getattr(other, "nanoseconds", 0)
        new_date = PSDateTime(super().__add__(other))

        # If the nanoseconds exceed 1000 we need to add the microseconds to our new date before setting the nanosecond
        # property.
        if nanosecond_diff > 999:
            microseconds, nanosecond_diff = divmod(nanosecond_diff, 1000)
            new_date += datetime.timedelta(microseconds=microseconds)

        new_date.nanosecond = nanosecond_diff

        return new_date

    def __sub__(  # type: ignore[override] # cannot seem to document NotImplemented as a return type
        self,
        other: typing.Union[datetime.datetime, datetime.timedelta],
    ) -> typing.Union["PSDateTime", "PSDuration"]:
        if isinstance(other, (PSDuration, datetime.timedelta)):
            return self + -other

        duration = PSDuration(super().__sub__(other))  # type: ignore[call-overload]
        nanosecond_diff = self.nanosecond - getattr(other, "nanosecond", 0)
        return duration + PSDuration(nanoseconds=nanosecond_diff)

    @classmethod
    def strptime(
        cls,
        date_string: str,
        format: str,
    ) -> "PSDateTime":
        return cls(super().strptime(date_string, format))


@PSType(["System.TimeSpan", "System.ValueType"], tag="TS")
class PSDuration(PSObject, datetime.timedelta):
    """The Duration primitive type.

    This is the duration primitive type which represents the following types:

        Python: :class:`datetime.timedelta`

        Native Serialization: yes

        PSRP: `[MS-PSRP] 2.2.5.1.5 Duration`_

        .NET: `System.TimeSpan`_

    This extends the Python datetime.timespan class and adds a `nanoseconds`
    attribute to track the nanoseconds. While the class can have a nanosecond
    precision, a serialized Duration object can only go up to a .NET Tick which
    is 100s of nanoseconds.

    .. _[MS-PSRP] 2.2.5.1.5 Duration:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/434cd15d-8fb3-462c-a004-bcd0d3a60201

    .. _System.TimeSpan:
        https://docs.microsoft.com/en-us/dotnet/api/system.timespan?view=net-5.0
    """

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__()
        self.nanoseconds = getattr(self, "nanoseconds", None) or 0

    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> "PSDuration":
        nanoseconds = 0
        if "nanoseconds" in kwargs:
            nanoseconds = kwargs.pop("nanoseconds")

        # Need to get the total seconds and microseconds and add our custom nanoseconds to the amount before we create
        # the final duration object.
        if args and isinstance(args[0], datetime.timedelta):
            td = args[0]
        else:
            td = datetime.timedelta(*args, **kwargs)

        nanoseconds += _timedelta_total_nanoseconds(td)
        microseconds = nanoseconds // 1000
        nanoseconds %= 1000

        instance = super().__new__(cls, microseconds=microseconds)
        instance.nanoseconds = int(nanoseconds)

        return instance

    def __repr__(self) -> str:
        values = []
        for field in ["days", "seconds", "microseconds", "nanoseconds"]:
            value = getattr(self, field, None)
            if value:
                values.append(f"{field}={value}")

        if not values:
            values.append("0")

        kwargs = ", ".join(values)
        return f"{type(self).__name__}({kwargs})"

    def __str__(self) -> str:
        s = ""
        if self.days:
            plural = "s" if abs(self.days) != 1 else ""
            s = f"{self.days} day{plural}, "

        minutes, seconds = divmod(self.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        s += f"{hours}:{minutes:02d}:{seconds:02d}"

        if self.microseconds or self.nanoseconds:
            nanoseconds = f"{self.nanoseconds:03d}" if self.nanoseconds else ""
            microseconds = f"{self.microseconds:06d}"
            s += f".{microseconds}{nanoseconds}"

        return s

    @_ensure_types_and_self(datetime.timedelta)
    def __add__(
        self,
        other: datetime.timedelta,
    ) -> "PSDuration":
        new_nano = _timedelta_total_nanoseconds(self) + _timedelta_total_nanoseconds(other)
        return PSDuration(nanoseconds=new_nano)

    @_ensure_types_and_self(datetime.timedelta)
    def __sub__(
        self,
        other: datetime.timedelta,
    ) -> "PSDuration":
        new_nano = _timedelta_total_nanoseconds(self) - _timedelta_total_nanoseconds(other)
        return PSDuration(nanoseconds=new_nano)

    @_ensure_types_and_self(datetime.timedelta)
    def __rsub__(
        self,
        other: datetime.timedelta,
    ) -> "PSDuration":
        return -self + other

    def __neg__(self) -> "PSDuration":
        return PSDuration(nanoseconds=-(_timedelta_total_nanoseconds(self)))

    def __pos__(self) -> "PSDuration":
        return self

    @_ensure_types_and_self(datetime.timedelta)
    def __eq__(
        self,
        other: datetime.timedelta,
    ) -> bool:
        return _timedelta_total_nanoseconds(self) == _timedelta_total_nanoseconds(other)

    @_ensure_types_and_self(datetime.timedelta)
    def __ne__(
        self,
        other: datetime.timedelta,
    ) -> bool:
        return _timedelta_total_nanoseconds(self) != _timedelta_total_nanoseconds(other)

    @_ensure_types_and_self(datetime.timedelta)
    def __le__(
        self,
        other: datetime.timedelta,
    ) -> bool:
        return _timedelta_total_nanoseconds(self) <= _timedelta_total_nanoseconds(other)

    @_ensure_types_and_self(datetime.timedelta)
    def __lt__(
        self,
        other: datetime.timedelta,
    ) -> bool:
        return _timedelta_total_nanoseconds(self) < _timedelta_total_nanoseconds(other)

    @_ensure_types_and_self(datetime.timedelta)
    def __ge__(
        self,
        other: datetime.timedelta,
    ) -> bool:
        return _timedelta_total_nanoseconds(self) >= _timedelta_total_nanoseconds(other)

    @_ensure_types_and_self(datetime.timedelta)
    def __gt__(
        self,
        other: datetime.timedelta,
    ) -> bool:
        return _timedelta_total_nanoseconds(self) > _timedelta_total_nanoseconds(other)


# '[TimeSpan]::MaxValue.Ticks' and '[TimeSpan]::MinValue.Ticks' (*100 to make it nanoseconds).
PSDuration.min = PSDuration(nanoseconds=-922337203685477580800)
PSDuration.max = PSDuration(nanoseconds=922337203685477580700)

# .NET Tick is 100 nanoseconds, while we can compute up to a nanosecond precision, we can only serialize up to a 100
# nanosecond precision.
PSDuration.resolution = PSDuration(nanoseconds=100)


@PSType(["System.Byte", "System.ValueType"], tag="By")
class PSByte(PSIntegerBase):
    """The Unsigned byte primitive type.

    This is the unsigned byte primitive type which represents the following
    types:

        Python: :class:`int`

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.1.6 Unsigned Byte`_

        .NET: `System.Byte`_

    While this represents an int in Python it is artificially limited to values
    between 0 and 255 like a Byte on .NET.

    .. _[MS-PSRP] 2.2.5.1.6 Unsigned Byte:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/6e25153d-77b6-4e21-b5fa-6f986895171a

    .. _System.Byte:
        https://docs.microsoft.com/en-us/dotnet/api/system.byte?view=net-5.0
    """

    MinValue = 0
    MaxValue = 255


@PSType(["System.SByte", "System.ValueType"], tag="SB")
class PSSByte(PSIntegerBase):
    """The Signed byte primitive type.

    This is the signed byte primitive type which represents the following
    types:

        Python: :class:`int`

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.1.7 Signed Byte`_

        .NET: `System.SByte`_

    While this represents an int in Python it is artificially limited to values
    between -128 and 127 like an SByte on .NET.

    .. _[MS-PSRP] 2.2.5.1.7 Signed Byte:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/8046c418-1531-4c43-9b9d-fb9bceace0db

    .. _System.SByte:
        https://docs.microsoft.com/en-us/dotnet/api/system.sbyte?view=net-5.0
    """

    MinValue = -128
    MaxValue = 127


@PSType(["System.UInt16", "System.ValueType"], tag="U16")
class PSUInt16(PSIntegerBase):
    """The Unsigned short primitive type.

    This is the unsigned short primitive type which represents the following
    types:

        Python: :class:`int`

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.1.8 Unsigned Short`_

        .NET: `System.UInt16`_

    While this represents an int in Python it is artificially limited to values
    between 0 and 65535 like a UInt16 on .NET.

    .. _[MS-PSRP] 2.2.5.1.8 Unsigned Short:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/33751ca7-90d0-4b5e-a04f-2d8798cfb419

    .. _System.UInt16:
        https://docs.microsoft.com/en-us/dotnet/api/system.uint16?view=net-5.0
    """

    MinValue = 0
    MaxValue = 65535


@PSType(["System.Int16", "System.ValueType"], tag="I16")
class PSInt16(PSIntegerBase):
    """The Signed short primitive type.

    This is the signed short primitive type which represents the following
    types:

        Python: :class:`int`

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.1.9 Signed Short`_

        .NET: `System.Int16`_

    While this represents an int in Python it is artificially limited to values
    between -32768 and 32767 like an Int16 on .NET.

    .. _[MS-PSRP] 2.2.5.1.9 Signed Short:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/e0ed596d-0aea-40bb-a254-285b71188214

    .. _System.Int16:
        https://docs.microsoft.com/en-us/dotnet/api/system.int16?view=net-5.0
    """

    MinValue = -32768
    MaxValue = 32767


@PSType(["System.UInt32", "System.ValueType"], tag="U32")
class PSUInt(PSIntegerBase):
    """The Unsigned int primitive type.

    This is the unsigned integer primitive type which represents the following
    types:

        Python: :class:`int`

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.1.10 Unsigned Int`_

        .NET: `System.UInt32`_

    While this represents an int in Python it is artificially limited to values
    between 0 and 4294967295 like a UInt32 on .NET.

    .. _[MS-PSRP] 2.2.5.1.10 Unsigned Int:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/7b904471-3519-4a6a-900b-8053ad975c08

    .. _System.UInt32:
        https://docs.microsoft.com/en-us/dotnet/api/system.uint32?view=net-5.0
    """

    MinValue = 0
    MaxValue = 4294967295


@PSType(["System.Int32", "System.ValueType"], tag="I32")
class PSInt(PSIntegerBase):
    """The Signed int primitive type.

    This is the signed int primitive type which represents the following types:

        Python: :class:`int`

        Native Serialization: yes

        PSRP: `[MS-PSRP] 2.2.5.1.11 Signed Int`_

        .NET: `System.Int32`_

    While this represents an int in Python it is artificially limited to values
    between -2147483648 and 2147483647 like an Int32 on .NET.

    .. _[MS-PSRP] 2.2.5.1.11 Signed Int:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/9eef96ba-1876-427b-9450-75a1b28f5668

    .. _System.Int32:
        https://docs.microsoft.com/en-us/dotnet/api/system.int32?view=net-5.0
    """

    MinValue = -2147483648
    MaxValue = 2147483647


@PSType(["System.UInt64", "System.ValueType"], tag="U64")
class PSUInt64(PSIntegerBase):
    """The Unsigned long primitive type.

    This is the unsigned long primitive type which represents the following
    types:

        Python: :class:`int`

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.1.12 Unsigned Long`_

        .NET: `System.UInt64`_

    While this represents an int in Python it is artificially limited to values
    between 0 and 18446744073709551615 like a UInt64 on .NET.

    .. _[MS-PSRP] 2.2.5.1.12 Unsigned Long:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/d92cd5d2-59c6-4a61-b517-9fc48823cb4d

    .. _System.UInt64:
        https://docs.microsoft.com/en-us/dotnet/api/system.uint64?view=net-5.0
    """

    MinValue = 0
    MaxValue = 18446744073709551615


@PSType(["System.Int64", "System.ValueType"], tag="I64")
class PSInt64(PSIntegerBase):
    """The Signed long primitive type.

    This is the signed long primitive type which represents the following
    types:

        Python: :class:`int`

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.1.13 Signed Long`_

        .NET: `System.Int64`_

    While this represents an int in Python it is artificially limited to values
    between -9223372036854775808 and 9223372036854775807 like an Int64 on .NET.

    .. _[MS-PSRP] 2.2.5.1.13 Signed Long:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/de124e86-3f8c-426a-ab75-47fdb4597c62

    .. _System.Int64:
        https://docs.microsoft.com/en-us/dotnet/api/system.int64?view=net-5.0
    """

    MinValue = -9223372036854775808
    MaxValue = 9223372036854775807


@PSType(["System.Single", "System.ValueType"], tag="Sg")
class PSSingle(PSObject, float):
    """The Single primitive type.

    This is the single primitive type which represents the following types:

        Python: :class:`float`

        Native Serialization: yes

        PSRP: `[MS-PSRP] 2.2.5.1.14 Float`_

        .NET: `System.Single`_

    .. _[MS-PSRP] 2.2.5.1.14 Float:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/d8a5a9ab-5f52-4175-96a3-c29afb7b82b8

    .. _System.Single:
        https://docs.microsoft.com/en-us/dotnet/api/system.single?view=net-5.0
    """

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__()

    def __repr__(self) -> str:
        return float.__repr__(self)

    def __str__(self) -> str:
        return float.__str__(self)


@PSType(["System.Double", "System.ValueType"], tag="Db")
class PSDouble(PSObject, float):
    """The Double primitive type.

    This is the double primitive type which represents the following types:

        Python: :class:`float`

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.1.15 Double`_

        .NET: `System.Single`_

    .. _[MS-PSRP] 2.2.5.1.15 Double:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/02fa08c5-139c-4e98-a13e-45784b4eabde

    .. _System.Double:
        https://docs.microsoft.com/en-us/dotnet/api/system.double?view=net-5.0
    """

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__()

    def __repr__(self) -> str:
        return float.__repr__(self)

    def __str__(self) -> str:
        return float.__str__(self)


@PSType(["System.Decimal", "System.ValueType"], tag="D")
class PSDecimal(PSObject, decimal.Decimal):
    """The Decimal primitive type.

    This is the decimal primitive type which represents the following types:

        Python: :class:`decimal.Decimal`

        Native Serialization: yes

        PSRP: `[MS-PSRP] 2.2.5.1.16 Decimal`_

        .NET: `System.Decimal`_

    .. _[MS-PSRP] 2.2.5.1.16 Decimal:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/0f760f90-fa46-49bd-8868-001e2c29eb50

    .. _System.Decimal:
        https://docs.microsoft.com/en-us/dotnet/api/system.decimal?view=net-5.0
    """

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__()

    def __repr__(self) -> str:
        return decimal.Decimal.__repr__(self)

    def __str__(self) -> str:
        return decimal.Decimal.__str__(self)


@PSType(["System.Byte[]", "System.Array"], tag="BA")
class PSByteArray(PSObject, bytes):
    """The Byte Array primitive type.

    This is the byte array primitive type which represents the following types:

        Python: :class:`bytes`

        Native Serialization: yes

        PSRP: `[MS-PSRP] 2.2.5.1.17 Array of Bytes`_

        .NET: System.Byte[]

    .. _[MS-PSRP] 2.2.5.1.17 Array of Bytes:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/489ed886-34d2-4306-a2f5-73843c219b14
    """

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__()

    def __getitem__(  # type: ignore[override]  # The __mro__ is confusing mypy
        self,
        item: typing.Union[str, int, slice],
    ) -> "PSByteArray":
        # Allows slicing alongside getting extended properties which preserves the underlying type.
        if isinstance(item, str):
            return super().__getitem__(item)

        else:
            # String indexing, need to preserve the type.
            return type(self)(bytes.__getitem__(self, item))

    def __repr__(self) -> str:
        return bytes.__repr__(self)

    def __str__(self) -> str:
        return bytes.__str__(self)


@PSType(["System.Guid", "System.ValueType"], tag="G")
class PSGuid(PSObject, uuid.UUID):
    """The GUID/UUID primitive type.

    This is the GUID/UUID primitive type which represents the following types:

        Python: :class:`uuid.UUID`

        Native Serialization: yes

        PSRP: `[MS-PSRP] 2.2.5.1.18 GUID`_

        .NET: `System.Guid`_

    .. _[MS-PSRP] 2.2.5.1.18 GUID:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/c30c37fa-692d-49c7-bb86-b3179a97e106

    .. _System.Guid:
        https://docs.microsoft.com/en-us/dotnet/api/system.guid?view=net-5.0
    """

    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> "PSGuid":
        return super().__new__(cls)

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__()

        # UUID does not support __init__ with a UUID instance. Just rewrite the args to support this here.
        if len(args) == 1 and isinstance(args[0], uuid.UUID):
            kwargs = {"int": args[0].int}
            args = ()

        # Python 3.6 and 3.7 uses a __dict__ for a UUID whereas newer ones use __slots. We adjust the way we initialise
        # the UUID props based on this behaviour.
        if hasattr(uuid.UUID, "__slots__"):  # pragma: no cover
            uuid.UUID.__init__(self, *args, **kwargs)
        else:  # pragma: no cover
            uuid_val = uuid.UUID(*args, **kwargs)
            uuid.UUID.__getattribute__(self, "__dict__").update(uuid.UUID.__getattribute__(uuid_val, "__dict__"))

    def __setattr__(self, name: str, value: typing.Any) -> None:
        # UUID raises TypeError on __setattr__ and there are cases where we need to override the psobject attribute.
        if name == "PSObject":
            # Because PSObject returns a copy when requesting a __dict__ we need to go a step further to ensure we can
            # manipulate the actual __dict__ for this object.
            object.__getattribute__(self, "__dict__")["PSObject"] = value
            return

        super().__setattr__(name, value)

    def __repr__(self) -> str:
        return uuid.UUID.__repr__(self)

    def __str__(self) -> str:
        return uuid.UUID.__str__(self)


@PSType(["System.Uri"], tag="URI")
class PSUri(PSStringBase):
    """The URI primitive type.

    This is the URI primitive type which represents the following types:

        Python: :class:`str`

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.1.19 URI`_

        .NET: `System.Uri`_

    While the primitive type represents a URI, this is merely a URI as a string
    in Python. You will need need to use a separate function to parse this URI
    like :func:`urllib.parse.urlparse`.

    .. _[MS-PSRP] 2.2.5.1.19 URI:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/4ac73ac2-5cf7-4669-b4de-c8ba19a13186

    .. _System.Uri:
        https://docs.microsoft.com/en-us/dotnet/api/system.uri?view=net-5.0
    """


PSNull = None
"""The Null Value primitive type.

This is the Null Value primitive type which represents the following types:

    Python: None

    Native Serialization: yes

    PSRP: `[MS-PSRP] 2.2.5.1.20 Null Value`_

    .NET: null/$null

This isn't a type but rather just a placeholder for `None` in PSRP.

.. _[MS-PSRP] 2.2.5.1.20 Null Value:
    https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/402f2a78-5771-45ae-bf33-59f6e57767ca
"""


@PSType(["System.Version"], tag="Version")
class PSVersion(PSObject):
    """The Version primitive type.

    This is the Version primitive type which represents the following types:

        Python: N/A

        Native Serialization: yes

        PSRP: `[MS-PSRP] 2.2.5.1.21 Version`_

        .NET: `System.Version`_

    This is a custom implementation of a basic Version structure that matches
    the .NET System.Version class. A valid .NET Version must have the major and
    minor values defined as an integer and the build and revision are optional
    integer values.

    This class is able to sort multiple PSVersions but not with other Python
    version structures.

    Args:
        version_str: The version as a string, e.g. '1.2', '0.0.1', '1.2.3.4',
            '10.0.123.10'.
        major: The major version when not using version_str.
        minor: The minor version when not using version_str.
        build: The optional build version when not using version_str.
        revision: The optional revision when not using version_str.

    Attributes:
        major (:class:`int`): See parameters.
        minor (:class:`int`): See parameters.
        build (:class:`int`, optional): See parameters.
        revision (:class:`int`, optional): See parameters.

    .. _[MS-PSRP] 2.2.5.1.21 Version:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/390db910-e035-4f97-80fd-181a008ff6f8

    .. _System.Version:
        https://docs.microsoft.com/en-us/dotnet/api/system.version?view=net-5.0
    """

    def __init__(
        self,
        version_str: typing.Optional[str] = None,
        major: typing.Optional[int] = None,
        minor: typing.Optional[int] = None,
        build: typing.Optional[int] = None,
        revision: typing.Optional[int] = None,
    ) -> None:
        super().__init__()

        if version_str:
            version_match = _VERSION_PATTERN.match(version_str)
            if not version_match:
                raise ValueError(
                    f"Invalid PSVersion string '{version_str}': must be 2 to 4 groups of numbers that "
                    f"are separated by '.'"
                )

            matches = version_match.groupdict()
            major = int(matches["major"])
            minor = int(matches["minor"])
            build = int(matches["build"]) if matches["build"] is not None else None
            revision = int(matches["revision"]) if matches["revision"] is not None else None

        elif major is None or minor is None:
            raise ValueError(
                f"The major and minor versions must be specified when creating a " f"{self.__class__.__qualname__}"
            )

        elif revision is not None and build is None:
            raise ValueError(f"The build version must be set when revision is set.")

        self.major = major
        self.minor = minor
        self.build = build
        self.revision = revision

    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> "PSVersion":
        return super().__new__(cls)

    def __repr__(self) -> str:
        values = []
        for field in ["major", "minor", "build", "revision"]:
            value = getattr(self, field, None)
            if value is not None:
                values.append(f"{field}={value}")

        kwargs = ", ".join(values)
        return f"{type(self).__name__}({kwargs})"

    def __str__(self) -> str:
        parts = [self.major, self.minor, self.build, self.revision]
        return ".".join([str(p) for p in parts if p is not None])

    def __eq__(
        self,
        other: object,
    ) -> bool:
        if not isinstance(other, (PSVersion, str)):
            return False

        return self._cmp(other, operator.eq, "==")

    def __ge__(
        self,
        other: typing.Union["PSVersion", str],
    ) -> bool:
        return self._cmp(other, operator.ge, ">=")

    def __gt__(
        self,
        other: typing.Union["PSVersion", str],
    ) -> bool:
        return self._cmp(other, operator.gt, ">")

    def __le__(
        self,
        other: typing.Union["PSVersion", str],
    ) -> bool:
        return self._cmp(other, operator.le, "<=")

    def __lt__(
        self,
        other: typing.Union["PSVersion", str],
    ) -> bool:
        return self._cmp(other, operator.lt, "<")

    def _cmp(
        self,
        other: typing.Union["PSVersion", str],
        cmp: typing.Callable[[typing.Tuple[int, ...], typing.Tuple[int, ...]], bool],
        op_symbol: str,
    ) -> bool:
        if isinstance(other, str):
            other = PSVersion(version_str=other)

        if not isinstance(other, PSVersion):
            raise TypeError(
                f"'{op_symbol}' not supported between instances of 'PSVersion' and " f"'{type(other).__name__}"
            )

        def version_tuple(version: "PSVersion") -> typing.Tuple[int, ...]:
            parts = [version.major, version.minor, version.build, version.revision]
            return tuple([p for p in parts if p is not None])

        self_tuple = version_tuple(self)
        other_tuple = version_tuple(other)

        return cmp(self_tuple, other_tuple)


@PSType(["System.Xml.XmlDocument", "System.Xml.XmlNode"], tag="XD")
class PSXml(PSStringBase):
    """The XML Document primitive type.

    This is the XML Document primitive type which represents the following
    types:

        Python: :class:`str`

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.1.22 XML Document`_

        .NET: `System.Xml.XmlDocument`_

    While the primitive type represents an XML Document, this is merely an XML
    value as a string in Python. You will still need to use an XML library to
    parse the value.

    .. _[MS-PSRP] 2.2.5.1.22 XML Document:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/df5908ab-bb4d-45e4-8adc-7258e5a9f537

    .. _System.Xml.XmlDocument:
        https://docs.microsoft.com/en-us/dotnet/api/system.xml.xmldocument?view=net-5.0
    """


@PSType(["System.Management.Automation.ScriptBlock"], tag="SBK")
class PSScriptBlock(PSStringBase):
    """The ScriptBlock primitive type.

    This is the PowerShell ScriptBlock primitive type which represents the
    following types:

        Python: :class:`str`

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.1.23 ScriptBlock`_

        .NET: `System.Management.Automation.ScriptBlock`_

    While the primitive type represents a ScriptBlock in PowerShell there are
    some limitations when it comes to sending a scriptblock over a remote
    PSSession. The PSRP server will automatically convert the instance to a
    string so this type is mostly useless.

    .. _[MS-PSRP] 2.2.5.1.23 ScriptBlock:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/306af1be-6be5-4074-acc9-e29bd32f3206

    .. _System.Management.Automation.ScriptBlock:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.scriptblock?view=powershellsdk-7.0.0
    """


@PSType(["System.Security.SecureString"], tag="SS")
class PSSecureString(PSObject):
    """The Secure String primitive type.

    This is the PowerShell secure string primitive type which represents the
    following types:

        Python: N/A

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.1.24 Secure String`_

        .NET: `System.Security.SecureString`_

    It is designed to mark a string as a secure string which will be encrypted
    as it is serialized. The plaintext value can be retrieved using the
    :meth:`PSSecureString.decrypt` function.

    Note:
        Before a `PSSecureString` can be created or decrypted from the peer,
        the session key must be exchanged.

    Note:
        There are no guarantees of security when using this class. It is only
        useful when trying to encrypt data as it goes over the wire rather than
        marking it as sensitive data in Python. Because the plaintext value is
        cached the data may remain behind in memory before Python cleans up the
        value.

    Args:
        value: The plaintext value to encrypt (when `cipher` is `None`) or the
            encrypted value (when `cipher` is not `None`).
        cipher: The :class:`PSCryptoProvider` cipher used to encrypt or decrypt
            the secure string. If omitted then the `value` specified is
            treated as the plaintext and will be encrypted during
            serialization.

    .. _[MS-PSRP] 2.2.5.1.24 Secure String:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/69b9dc01-a843-4f91-89f8-0205f021a7dd

    .. _System.Security.SecureString:
        https://docs.microsoft.com/en-us/dotnet/api/system.security.securestring?view=net-5.0
    """

    def __init__(
        self,
        value: str,
        cipher: typing.Optional[PSCryptoProvider] = None,
    ) -> None:
        super().__init__()
        self._value: str = value
        self._cipher = cipher
        self._encrypted = cipher is not None

    def decrypt(self) -> PSString:
        """Decrypts a PSSecureString into the plaintext string."""
        if self._cipher:
            b_enc = base64.b64decode(self._value)
            b_dec = self._cipher.decrypt(b_enc)
            raw = b_dec.decode("utf-16-le")

        else:
            raw = self._value

        dec_str = PSString(raw)
        dec_str.PSObject = self.PSObject
        return dec_str

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def __str__(self) -> str:
        return (str(self._value) if self._encrypted else self.PSObject.type_names[0]) or ""

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "PSSecureString",
        cipher: PSCryptoProvider,
        **kwargs: typing.Any,
    ) -> PSObject:
        if not instance._encrypted:
            # The value was provided by the user without a cipher. Use the one passed in by the serializer to encrypt
            # the value and return that for serialization.
            b_value = instance._value.encode("utf-16-le")
            b_enc = cipher.encrypt(b_value)
            enc_value = base64.b64encode(b_enc).decode()

            return cls(enc_value, cipher)

        else:
            return instance
