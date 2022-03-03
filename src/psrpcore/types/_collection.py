# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""PSRP/.NET Collection Types.

Contains the base class for the various collection types, list/dict/stack/queue,
in PowerShell as well as the default class for each of those types.
"""

import queue
import typing

from psrpcore.types._base import PSObject, PSType


class PSDictBase(PSObject, dict):
    """The base dictionary type.

    This is the base dictionary PSObject type that all dictionary like objects
    should inherit from. It cannot be instantiated directly and is meant to be
    used as a base class for any .NET dictionary types.

    Note:
        While you can implement your own custom dictionary .NET type like
        `System.Collections.Generic.Dictionary<TKey, TValue>`, any dictionary
        based .NET types will be deserialized by the remote PowerShell runspace
        as `System.Collections.Hashtable`_. This .NET type is represented by
        :class:`PSDict`.

    .. _System.Collections.Hashtable:
        https://docs.microsoft.com/en-us/dotnet/api/system.collections.hashtable?view=net-5.0
    """

    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> "PSDictBase":
        if cls == PSDictBase:
            raise TypeError(
                f"Type {cls.__qualname__} cannot be instantiated; it can be used only as a base class for "
                f"dictionary types."
            )
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        dict.__init__(self, *args, **kwargs)

    def __getitem__(self, item: typing.Any) -> object:
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            return super().__getitem__(item)

    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        dict.__setitem__(self, key, value)

    def __repr__(self) -> str:
        return dict.__repr__(self)

    def __str__(self) -> str:
        return dict.__str__(self)


class _PSListBase(PSObject, list):
    """Common list base class for PSListBase and PSStackBase."""

    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> "_PSListBase":
        if cls in [_PSListBase, PSListBase, PSStackBase]:
            raise TypeError(
                f"Type {cls.__qualname__} cannot be instantiated; it can be used only as a base class for "
                f"list types."
            )
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, seq: typing.Iterable = (), *args: typing.Any, **kwargs: typing.Any):
        super().__init__(*args, **kwargs)
        list.__init__(self, seq)

    def __getitem__(self, item: typing.Any) -> typing.Any:
        try:
            return list.__getitem__(self, item)
        except TypeError:
            return super().__getitem__(item)

    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        if isinstance(key, str):
            return super().__setitem__(key, value)
        else:
            return list.__setitem__(self, key, value)

    def __repr__(self) -> str:
        return list.__repr__(self)

    def __str__(self) -> str:
        return list.__str__(self)


class PSListBase(_PSListBase):
    """The base list type.

    This is the base list PSObject type that all list like objects should
    inherit from. It cannot be instantiated directly and is meant to be used as
    a base class for any .NET list types.

    Note:
        While you can implement your own custom list .NET type like
        `System.Collections.Generic.List<T>`, any list based .NET types will be
        deserialized by the remote PowerShell runspace as
        `System.Collections.ArrayList`_. This .NET type is represented by
        :class:`PSList`.

    .. _System.Collections.ArrayList:
        https://docs.microsoft.com/en-us/dotnet/api/system.collections.arraylist?view=net-5.0
    """


class PSQueueBase(PSObject, queue.Queue):
    """The base queue type.

    This is the base queue PSObject type that all queue like objects should
    inherit from. It cannot be instantiated directly and is meant to be used as
    a base class for any .NET queue types.

    Note:
        While you can implement your own custom queue .NET type like
        `System.Collections.Generic.Queue<T>`, any queue based .NET types will
        be deserialized by the remote PowerShell runspace as
        `System.Collections.Queue`_. This .NET type is represented by
        :class:`PSQueue`.

    .. _System.Collections.Queue:
        https://docs.microsoft.com/en-us/dotnet/api/system.collections.queue?view=net-5.0
    """

    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> "PSQueueBase":
        if cls == PSQueueBase:
            raise TypeError(
                f"Type {cls.__qualname__} cannot be instantiated; it can be used only as a base class for "
                f"queue types."
            )

        que = super().__new__(cls)

        # Need to make sure __init__ is always called when creating the instance as rehydration will only call __new__
        # and certain props are set in __init__ to make a queue useful.
        queue.Queue.__init__(que, *args, **kwargs)

        return que

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        pass  # We cannot call the base __init__() function in ase any properties are set.

    def __repr__(self) -> str:
        return queue.Queue.__repr__(self)

    def __str__(self) -> str:
        return queue.Queue.__str__(self)


class PSStackBase(_PSListBase):
    """The base stack type.

    This is the base stack PSObject type that all stack like objects should
    inherit from. It cannot be instantiated directly and is meant to be used as
    the base class for any .NET stack types. A stack is a last-in, first out
    collection but Python does not have a native stack type so this just
    replicates the a Python list.

    Note:
        While you can implement your own custom stack .NET type like
        `System.Collections.Generic.Stack<T>`, any stack based .NET types will
        be deserialized by the remote PowerShell runspace as
        `System.Collections.Stack`_. This .NET type is represented by
        :class:`PSStack`.

    .. System.Collections.Stack:
        https://docs.microsoft.com/en-us/dotnet/api/system.collections.stack?view=net-5.0
    """


@PSType(["System.Collections.Stack"], tag="STK")
class PSStack(PSStackBase):
    """The Stack complex type.

    This is the stack complex type which represents the following types:

        Python: :class:`list`

        Native Serialization: no

        PSRP: `[MS-PSRP] 2.2.5.2.6.1 Stack`_

        .NET: `System.Collections.Stack`_

    A stack is a last-in, first-out setup but Python does not have a native
    stack type so this just uses a :class:`list`.

    .. _[MS-PSRP] 2.2.5.2.6.1 Stack:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/e9cf648e-38fe-42ba-9ca3-d89a9e0a856a

    .. _System.Collections.Stack:
        https://docs.microsoft.com/en-us/dotnet/api/system.collections.stack?view=net-5.0
    """


@PSType(["System.Collections.Queue"], tag="QUE")
class PSQueue(PSQueueBase):
    """The Queue complex type.

    This is the queue complex type which represents the following types:

        Python: :class:`queue.Queue`

        Native Serialization: yes

        PSRP: `[MS-PSRP] 2.2.5.2.6.2 Queue`_

        .NET: `System.Collections.Queue`_

    .. _[MS-PSRP] 2.2.5.2.6.2 Queue:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/ade9f023-ac30-4b7e-be17-900c02a6f837

    .. _System.Collections.Queue:
        https://docs.microsoft.com/en-us/dotnet/api/system.collections.queue?view=net-5.0
    """


# Would prefer an Generic.List<T> but regardless of the type a list is always deserialized by PowerShell as an
# ArrayList so just do that here.
@PSType(["System.Collections.ArrayList"], tag="LST")
class PSList(PSListBase):
    """The List complex type.

    This is the queue complex type which represents the following types:

        Python: :class:`list`

        Native Serialization: yes

        PSRP: `[MS-PSRP] 2.2.5.2.6.3 List`_

        .NET: `System.Collections.ArrayList`_

    .. _[MS-PSRP] 2.2.5.2.6.3 List:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/f4bdb166-cefc-4d49-848c-7d08680ae0a7

    .. _System.Collections.ArrayList:
        https://docs.microsoft.com/en-us/dotnet/api/system.collections.arraylist?view=net-5.0
    """


@PSType(["System.Collections.Hashtable"], tag="DCT")
class PSDict(PSDictBase):
    """The Dictionary complex type.

    This is the dictionary complex type which represents the following types:

        Python: :class:`dict`

        Native Serialization: yes

        PSRP: `[MS-PSRP] 2.2.5.2.6.4 Dictionaries`_

        .NET: `System.Collections.Hashtable`_

    .. _[MS-PSRP] 2.2.5.2.6.4 Dictionaries:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/c4e000a2-21d8-46c0-a71b-0051365d8273

    .. _System.Collections.Hashtable:
        https://docs.microsoft.com/en-us/dotnet/api/system.collections.hashtable?view=net-5.0
    """


@PSType(["System.Collections.IEnumerable"], tag="IE")
class PSIEnumerable(_PSListBase):
    """The IEnumerable complex type.

    This is the IEnumerable complex type which represents the following types:

        Python: :class:`list`

        Native Serialization: no

        PSRP: N/A - Mentioned in :class:`PSList`

        .NET `System.Collections.IEnumerable`_

    .. _System.Collections.IEnumerable:
        https://docs.microsoft.com/en-us/dotnet/api/system.collections.ienumerable?view=net-5.0
    """
