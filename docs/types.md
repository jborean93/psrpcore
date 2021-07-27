# Python to .NET Type Information

This is a guide on how the .NET type system and serialization works in `psrpcore`.


## Behaviour of PowerShell Objects

PowerShell objects are effectively .NET types with an Extended Type System (ETS).
This allows an existing .NET types to be extended with extra properties and methods that don't exist in the base .NET type.
While there are many types of properties used in PowerShell, when an object is serialized it categorizes them into 2 different types:

+ Adapted Properties `<Props>`: The base properties that exist on the .NET type
+ Extended Properties `<MS>`: Extra properties added by the PowerShell ETS

Some key behaviours of PowerShell objects are:

+ An adapted and extended property can share the same name, when accessed in PowerShell the extended property is favoured
+ Property names can be any anything except `$null`, or one of the following reserved names
  + `PSObject` - the metadata of the object, i.e. properties, type names of the object
  + `PSBase` - the object but with the extended properties stripped out
  + `PSAdapted` - all the adapted properties
  + `PSExtended` - all the extended properties
  + `PSTypeNames` - a list of type names that the object implements
+ Property names in PowerShell are also case insensitive
+ Properties can be accessed through the dot notation but not as an index, i.e. `$obj.PropertyName` works but `$obj['PropertyName']` does not
  + If a dict like object has a propert with the same name as a key it contains, the property is favoured over the key value

_Note: While dict types can use both the dot and index notation to find key values, actual object properties are only accesible using the dot notation._

```powershell
$hash = @{foo = 'bar'}

# PowerShell can get the key/value using the dot notation normally
$hash.foo -eq 'bar'

# Adds a property to the hashtable - only accesible using the dot notation
Add-Member -InputObject $hash -NotePropertyName my_prop -NotePropertyValue prop_value
$hash.my_prop -eq 'prop_value'
$hash['my_prop'] -ne 'prop_value'

# Adds a property with the same name as a contained key
Add-Member -InputObject $hash -NotePropertyName foo -NotePropertyValue override

# Dot notation favours the property added
$hash.foo -eq 'override'

# Index still favours the index lookup behaviour of the object
$hash['foo'] -eq 'bar'
```

### Accessing Properties in Python

The goal of the type implementation in `psrpcore` is to try and replicate the same behaviour around .NET objects that are deserialized to a Python object as best as it can.
It is largely successful except for these key differences:

+ Properties are case sensitive in Python
+ When dealing with a dict and using the index lookup, it will lookup the dict elements first before it looks at the properties
  + This is unlike PowerShell where the index lookup never gets property values
  + This is only done to allow access to complex property names in Python that aren't allowed normally, e.g. properties with `-` or other illegal characters
+ A `System.Boolean/bool` in PowerShell can have extended properties, Python does not allow us to subclass the `bool` type so these properties are dropped
+ The `PSBase`, `PSAdapted`, and `PSExtended` properties are not implemented is not implemented
  + A `NotImplementedError()` will be raised when accessing these properties to reserve it for future use
+ PowerShell automatically adds the `PSComputerName` and `RunspaceId` extended properties to each object returned from a remote runspace, `psrpcore` does not

Accessing a property for a .NET aware object in Python can be done in 3 ways:

```python
# Using the dot notation
obj.PropertyName

# Using an index lookup
obj['PropertyName']

# Accesing it through the PSObject metdata
obj.PSObject.adapted_properties  # List of adapted properties, filter by name
obj.PSObject.extended_properties  # List of extended properties, filter by name
```

One major caveat to consider is that legal attribute names in Python is a tiny subset of what's legal in .NET/PowerShell.
For example the property `Property Name` (with a space) is a illegal attribute in Python.
To access this, use the index lookup notation

```python
# Does not work!
obj."Property Name"

# Works
obj["Property Name"]
```

This also applies to properties with other illegal characters like `-`, pure integers, non-ASCII characters, etc.

You can also access the same reserved property names like `PSObject` and `PSTypeNames`, etc on a Python instance of a .NET object.
The information it returns is similar to PowerShell but not exactly the same.

If you want to see all the properties of an object, similar to how `$obj | Select-Object -Property *` works you can use the `vars(obj)` function just like a normal Python object.

```python
import psrpcore

record = psrpcore.types.VerboseRecord("message")
vars(record)

# {
#     'PSObject': <psrpcore.types._base.PSObjectMeta object at 0x7fb9ed36b220>,
#     'serialize_extended_info': False,
#     'Message': 'message',
#     'InvocationInfo': None,
#     'PipelineIterationInfo': None
# }
```

You could also loop through `obj.PSObject.adapted_properties` and `obj.PSObject.extended_properties` and view each property manually.


## Class Mapping

So far we've covered object properties in PowerShell and how they work in their Python equivalents.
The next step is to talk about the underlying class types and how they translate into Python and vice versa.

In [MS-PSRP](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/602ee78e-9a19-45ad-90fa-bb132b7cecec) there are three different type classes:

* [Primitive types](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/c8c85974-ffd7-4455-84a8-e49016c20683)
* [Complex types](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/406ad572-1ede-43e0-b063-e7291cda3e63)
* Enum types - they are complex types but we consider them separate here

### Primitive Types

Primitive types are the fundamental types that contain a value and optional properties.
When it comes to working with primitive types for PSRP in Python, there exists a Python class for each primitive in `psrpcore.types` that subclasses both `PSObject` as well as the Python type it closely resembles.
Here is the mapping of the primitive types:

| .NET | psrpcore.type | Python Type | Native |
|-|-|-|-|
| [System.String](https://docs.microsoft.com/en-us/dotnet/api/system.string) | [PSString](./source/psrpcore.types.html#psrpcore.types.PSString) | str | Y |
| [System.Char](https://docs.microsoft.com/en-us/dotnet/api/system.char) | [PSChar](./source/psrpcore.types.html#psrpcore.types.PSChar) | int¹ | N |
| [System.Boolean](https://docs.microsoft.com/en-us/dotnet/api/system.boolean) | [PSBool](./source/psrpcore.types.html#psrpcore.types.PSBool)² | bool | Y |
| [System.DateTime](https://docs.microsoft.com/en-us/dotnet/api/system.datetime) | [PSDateTime](./source/psrpcore.types.html#psrpcore.types.PSDateTime) | datetime.datetime | Y |
| [System.TimeSpan](https://docs.microsoft.com/en-us/dotnet/api/system.timespan) | [PSDuration](./source/psrpcore.types.html#psrpcore.types.PSDuration) | str | N |
| [System.Byte](https://docs.microsoft.com/en-us/dotnet/api/system.byte) | [PSByte](./source/psrpcore.types.html#psrpcore.types.PSByte) | int | N |
| [System.SByte](https://docs.microsoft.com/en-us/dotnet/api/system.sbyte) | [PSSByte](./source/psrpcore.types.html#psrpcore.types.PSSByte) | int | N |
| [System.UInt16](https://docs.microsoft.com/en-us/dotnet/api/system.uint16) | [PSUInt16](./source/psrpcore.types.html#psrpcore.types.PSUInt16) | int | N |
| [System.Int16](https://docs.microsoft.com/en-us/dotnet/api/system.int16) | [PSInt16](./source/psrpcore.types.html#psrpcore.types.PSInt16) | int | N |
| [System.UInt32](https://docs.microsoft.com/en-us/dotnet/api/system.uint32) | [PSUInt](./source/psrpcore.types.html#psrpcore.types.PSUInt) | int | N |
| [System.Int32](https://docs.microsoft.com/en-us/dotnet/api/system.int32) | [PSInt](./source/psrpcore.types.html#psrpcore.types.PSInt) | int | Y |
| [System.UInt64](https://docs.microsoft.com/en-us/dotnet/api/system.uint64) | [PSUInt64](./source/psrpcore.types.html#psrpcore.types.PSUInt64) | int | N |
| [System.Int64](https://docs.microsoft.com/en-us/dotnet/api/system.int64) | [PSInt64](./source/psrpcore.types.html#psrpcore.types.PSInt64) | int | N |
| [System.Single](https://docs.microsoft.com/en-us/dotnet/api/system.single) | [PSSingle](./source/psrpcore.types.html#psrpcore.types.PSSingle) | float | Y |
| [System.Double](https://docs.microsoft.com/en-us/dotnet/api/system.double) | [PSDouble](./source/psrpcore.types.html#psrpcore.types.PSDouble) | float | N |
| [System.Decimal](https://docs.microsoft.com/en-us/dotnet/api/system.decimal) | [PSDecimal](./source/psrpcore.types.html#psrpcore.types.PSDecimal) | decimal.Decimal | Y |
| `System.Byte[]` - Array | [PSByteArray](./source/psrpcore.types.html#psrpcore.types.PSByteArray) | bytes | Y |
| [System.Guid](https://docs.microsoft.com/en-us/dotnet/api/system.guid) | [PSGuid](./source/psrpcore.types.html#psrpcore.types.PSGuid) | uuid.UUID | Y |
| [System.Uri](https://docs.microsoft.com/en-us/dotnet/api/system.uri) | [PSUri](./source/psrpcore.types.html#psrpcore.types.PSUri) | str | N |
| `$null` | `PSNull`² | None | Y |
| [System.Version](https://docs.microsoft.com/en-us/dotnet/api/system.version) | [PSVersion](./source/psrpcore.types.html#psrpcore.types.PSVersion) | N/A | N |
| [System.Xml.XmlDocument](https://docs.microsoft.com/en-us/dotnet/api/system.xml.xmldocument) | [PSXml](./source/psrpcore.types.html#psrpcore.types.PSXml) | str | N |
| [System.Management.Automation.ScriptBlock](https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.scriptblock) | [PSScriptBlock](./source/psrpcore.types.html#psrpcore.types.PSScriptBlock) | str | N |
| [System.Security.SecureString](https://docs.microsoft.com/en-us/dotnet/api/system.security.securestring) | [PSSecureString](./source/psrpcore.types.html#psrpcore.types.PSSecureString)³ | N/A | N |

¹ - While the base Python type is an `int`, doing `PSChar('1')` will get the char based on the string value. Do `PSChar(1)` if you want the `PSChar` to represent `\u0001`

² - While there is a `psrpcore.types` class for these .NET types, they do not inherit `PSObject` so they cannot handle extended properties

³ - A `PSSecureString` can be used to encrypt strings that traverse across the wire but the string in Python is not encrypted in memory

If `Native` is `Y`, then `psrpcore` will automatically convert that native Python type to the .NET type for you.
Otherwise the `psrpcore.types` implementation must be used if you want to serialize a particular .NET type.
For example if I was to pass in an `int` as an object, `psrpcore` will automatically serialize that to a `System.Int32` but say I wanted that to be a `System.UInt16` object I would need to pass in a `PSUInt16` instance instead.

When a primitive type is deserialized, the instance will be the `psrpcore.types` type.
Due to how inheritance works you can do all of the following:

```python
import psrpcore.types

...
output = ps.invoke()[0]  # Our example outputs an Int32 value

assert isinstance(output, psrpcore.types.PSObject)  # Works for all except bool and $null
assert isinstance(output, psrpcore.types.PSInt)
assert isinstance(output, int)
```

### Complex Types

Complex types are the opposite of a primitive type.
While primitive objects can be extended to include extended properties they are still considered a primitive object because it's a single value.
A complex object typically is a class instance that contains both adapted and extended properties.
They can also include container like object such as a dict, list, stack, queue, etc.

While `psrpcore` supports (de)serialization of effectively any complex object, there are a few important .NET complex types that are good to remember:

| .NET | psrpcore.type | Python Type | Native |
|-|-|-|-|
| [System.Collections.ArrayList](https://docs.microsoft.com/en-us/dotnet/api/system.collections.arraylist)¹ | [PSList](./source/psrpcore.types.html#psrpcore.types.PSList) | list | Y |
| [System.Collections.Hashtable](https://docs.microsoft.com/en-us/dotnet/api/system.collections.hashtable)¹ | [PSDict](./source/psrpcore.types.html#psrpcore.types.PSDict) | dict | Y |
| [System.Collections.Stack](https://docs.microsoft.com/en-us/dotnet/api/system.collections.stack)¹ | [PSStack](./source/psrpcore.types.html#psrpcore.types.PSStack) | list | N |
| [System.Collections.Queue](https://docs.microsoft.com/en-us/dotnet/api/system.collections.queue)¹ | [PSQueue](./source/psrpcore.types.html#psrpcore.types.PSQueue) | queue.Queue | Y |
| [System.Management.Automation.PSCustomObject](https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.pscustomobject) | [PSCustomObject](./source/psrpcore.types.html#psrpcore.types.PSCustomObject) | type² | Y |

¹ - Other .NET types that are similar to this type are always deserialized to this .NET type, `psrpcore` acts the same, e.g. an` [Object[]]` will become a `PSList`

² - Unless the Python type hash been marked as a specific .NET type, it will automatically be serialized as a `PSCustomObject`

Like a primitive object, when `Native` is `Y`, those Python types are automatically serialized to the .NET type it represents.
If you wish to use a specific .NET type that does not natively do this, you need to use the `psrpcore.types.*` class that represents the .NET type you desire or create your own.

### Enum Types

While technically a complex type I consider enums in PSRP to be a separate type of object that straddles both a primitive and complex type.
Because of its uniqueness they are implemented slightly differently and have a few caveats in Python.

There are 2 base enum types that can be used

* [psrpcore.types.PSEnumBase](./source/psrpcore.types.html#psrpcore.types.PSEnumBase): Inherits `PSObject`, used for enum types that should be set with a single value
* [psrpcore.types.PSFlagBase](./source/psrpcore.types.html#psrpcore.types.PSFlagBase): Same as `PSEnumBase` but has special behaviour to allow multiple values to be set

Like with .NET enums, the enums that inherit `PSEnumBase` or `PSFlagBase` must represent one of the [numeric types](https://docs.microsoft.com/en-us/dotnet/csharp/language-reference/builtin-types/integral-numeric-types) like:

* `psrpcore.types.PSByte`
* `psrpcore.types.PSSByte`
* `psrpcore.types.PSUInt16`
* `psrpcore.types.PSInt16`
* `psrpcore.types.PSUInt`
* `psrpcore.types.PSInt` - default
* `psrpcore.types.PSUInt64`
* `psrpcore.types.PSInt64`

This is defined by adding the `base_type` kwarg to the class definition:

```python
from psrpcore.types import PSEnumBase, PSType, PSUInt

@PSType(type_names=[f"System.MyEnum"])
class MyEnum(PSEnumBase, base_type=PSUInt):
    none = 0
    Value1 = 1
    Value2 = 2
    Value3 = 3
```

From there, the enum is defined as a normal Python enum class.
There are a few things when it comes to implementing your own enum type

* The enum names should match the .NET type, don't implement your own custom labels as the label is used to compute the `<ToString>` value in the CLIXML
* If there is an enum label called `None`, use `none` instead
* If the PSType is marked with `rehydrate=False` then a deserialized instance of that enum will just be the primitive value of whatever numeric type the enum is based on

Here is an example of an basic enum [System.IO.FileMode](https://docs.microsoft.com/en-us/dotnet/api/system.io.filemode?view=netcore-3.1):

```python
import psrpcore.types as pstype

@pstype.PSType(type_names=["System.IO.FileMode"])
class IOFileMode(pstype.PSEnumBase):
    Append = 6
    Create = 2
    CreateNew = 1
    Open = 3
    OpenOrCreate = 4
    Truncate = 5
```

When you want to get an enum value just do `IOFileMode.Append` or with whatever label you need.
Any instances of `PSEnumBase` will automatically convert the raw `int` value to an instance of that type, i.e. `IOFileMode.Append` will be `IOFileMode(6)`.

Here is an example of a basic enum [System.IO.FileShare](https://docs.microsoft.com/en-us/dotnet/api/system.io.fileshare?view=netcore-3.1) that uses the `[FlagsAttributes]` to allow multiple values to be set.

```python
import psrpcore.types as pstype

@pstype.PSType(type_names=["System.IO.FileShare"])
class IOFileShare(pstype.PSFlagBase):
    Delete = 4
    Inheritable = 16
    none = 0
    Read = 1
    ReadWrite = 3
    Write = 2
```

Enums, like primitive objects can have further extended properties added to it if that is desired.


## Implementing .NET Type in Python

When implementing your own Python class to represent a .NET type there are few things you need to consider/understand:

+ The property names of the .NET class must match up with the ones defined on the Python class
+ When an object is serialized, property values are sourced from the property object inside `PSObject`
  + Using a `@property` decorator to generate a calculated property value won't work
  + The workaround is to use a [PSAliasProperty](./source/psrpcore.types.html#psrpcore.types.PSAliasProperty) or [PSScriptProperty](./source/psrpcore.types.html#psrpcore.types.PSScriptProperty) that is automatically called during the serialization process
+ Methods defined on the Python class are not transferred to PowerShell, only properties are
+ Whether you want the type to be rehydrated on deserialization or not

All custom .NET types in PowerShell that you implement *SHOULD* inherit from [psrpcore.types.PSObject](./source/psrpcore.types.html#psrpcore.types.PSObject) and use the [psrpcore.types.PSType](./source/psrpcore.types.html#psrpcore.types.PSType) decorator to define the .NET metadata.
Any classes that do not do this will be treated as a `PSCustomObject` which is explained a bit later.
The `PSType` decorator accepts the following arguments:

+ `type_names`: A list of .NET types the object implements, i.e. `['System.String']`
+ `adapted_properties`: A list of [psrpcore.types.PSPropertyInfo](./source/psrpcore.types.html#psrpcore.types.PSPropertyInfo) instances that define the adapted properties of the object
+ `extended_properties`: A list of [psrpcore.types.PSPropertyInfo](./source/psrpcore.types.html#psrpcore.types.PSPropertyInfo) instances that define the extended properties of the object
+ `skip_inheritance`: Do not inherit the type names and properties of the base class
+ `rehydrate`: Whether this type can be rehydrated (deserialized to this type) or not (default: `True`)
+ `tag`: The CLIXML tag element value to use, this should not be used for end users as all complex types are `Obj`

The type names and properties of the base object will also be inherited onto the defined class.
For example `PSObject` defines the type names as `["System.Object"]` and thus anything that inherits `PSObject` will have those types appended on it's custom types, e.g. `["System.MyType", "System.Object"]`.
To skip this behaviour and have a blank starting slate, set `skip_inheritance=True`.

The `adapted_properties` and `extended_properties` kwargs take a list of [PSPropertyInfo](./source/psrpcore.types.html#psrpcore.types.PSPropertyInfo) objects that define the properties of the object itself.
Once a property has been defined on the object it is immediately gettable/settable like a normal attribute of an instance.

The `rehydrate` kwarg is used during serialization to determine the Python type that is used for the deserialized value.
If `True` then any .NET objects that implement the same `type_names` will be a Python instance of the actual type.
If `False` then the returned Python object will be a `psrpcore.types.PSCustomObject` with all the same properties set and the `obj.PSObject.type_names` will have `Deserialized.<type name>` on them.
The main benefit `rehydrate=True` offers is it allows you do an `isinstance(obj, MyType)` check and call methods defined on that object.

Here is an example of how `psrpcore` implemented the [PSCredential](https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.pscredential)
type.

```python
from psrpcore.type import (
    PSNoteProperty,
    PSObject,
    PSString,
    PSSecureString,
    PSType,
)


@PSType(
    type_names=["System.Management.Automation.PSCredential"],
    adapted_properties=[
        PSNoteProperty("UserName", mandatory=True, ps_type=PSString),
        PSNoteProperty("Password", mandatory=True, ps_type=PSSecureString),
    ],
)
class PSCredential(PSObject):
    pass
```

We can see that the `type_names` is set to the types that the object inherits starting from top down and the adapted properties and the types they should be coerced to when being serialized.

Creating your own types is usually just about getting the metadata of the type and defining it under `PSObject`.
You can expand on it however you wish.
To help with creating your own classes I've written a PowerShell function called `ConvertTo-PythonClass` that you can use to generate a skeleton class in Python.

```{eval-rst}
.. raw:: html

   <details>
   <summary><a>ConvertTo-PythonClass</a></summary>

.. literalinclude:: _static/ConvertTo-PythonClass.ps1
   :language: powershell

.. raw:: html

   </details><p>
```

The generated skeleton can adjusted based on your requirements to include extra methods/properties for use on the Python side.

```powershell
$obj = Get-Item -Path C:\Windows
$obj | ConvertTo-PythonClass -AddDoc

# import psrpcore.types
#
# @psrpcore.types.PSType(
#     type_names=[
#         'System.IO.DirectoryInfo',
#         'System.IO.FileSystemInfo',
#         'System.MarshalByRefObject',
#     ],
#     adapted_properties=[
#         psrpcore.types.PSNoteProperty('Name', ps_type=psrpcore.types.PSString),
#         psrpcore.types.PSNoteProperty('FullName', ps_type=psrpcore.types.PSString),
#         psrpcore.types.PSNoteProperty('Parent'),
#         psrpcore.types.PSNoteProperty('Exists', ps_type=psrpcore.types.PSBool),
#         psrpcore.types.PSNoteProperty('Root'),
#         psrpcore.types.PSNoteProperty('Extension', ps_type=psrpcore.types.PSString),
#         psrpcore.types.PSNoteProperty('CreationTime', ps_type=psrpcore.types.PSDateTime),
#         psrpcore.types.PSNoteProperty('CreationTimeUtc', ps_type=psrpcore.types.PSDateTime),
#         psrpcore.types.PSNoteProperty('LastAccessTime', ps_type=psrpcore.types.PSDateTime),
#         psrpcore.types.PSNoteProperty('LastAccessTimeUtc', ps_type=psrpcore.types.PSDateTime),
#         psrpcore.types.PSNoteProperty('LastWriteTime', ps_type=psrpcore.types.PSDateTime),
#         psrpcore.types.PSNoteProperty('LastWriteTimeUtc', ps_type=psrpcore.types.PSDateTime),
#         psrpcore.types.PSNoteProperty('Attributes'),
#     ],
#     extended_properties=[
#         psrpcore.types.PSNoteProperty('PSPath', ps_type=psrpcore.types.PSString),
#         psrpcore.types.PSNoteProperty('PSParentPath', ps_type=psrpcore.types.PSString),
#         psrpcore.types.PSNoteProperty('PSChildName', ps_type=psrpcore.types.PSString),
#         psrpcore.types.PSNoteProperty('PSDrive'),
#         psrpcore.types.PSNoteProperty('PSProvider'),
#         psrpcore.types.PSNoteProperty('PSIsContainer', ps_type=psrpcore.types.PSBool),
#         psrpcore.types.PSNoteProperty('Mode', ps_type=psrpcore.types.PSString),
#         psrpcore.types.PSNoteProperty('BaseName'),
#         psrpcore.types.PSNoteProperty('Target'),
#         psrpcore.types.PSNoteProperty('LinkType', ps_type=psrpcore.types.PSString),
#     ],
# )
# class PSDirectoryInfo(psrpcore.types.PSObject):
#     """Python class for System.IO.DirectoryInfo
#
#     This is an auto-generated Python class for the System.IO.DirectoryInfo .NET class.
#     """
#     pass
```

One really common type that is used in PowerShell is the [PSCustomObject](https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.pscustomobject) class.
This is typically created using `[PSCustomObject]@{ ... }` and `psrpcore` has 2 ways of implementing the same concept.

```python
from psrpcore.types import PSCustomObject

# Using PSObjectObject({'key': 'value'})
ps_custom_object = PSCustomObject(
    PropertyName='name',
    AnotherProperty=1,
)

# Using a plain Python class
class MyPSCustomObject:

    def __init__(self, PropertyName, AnotherProperty):
        self.PropertyName = PropertyName
        self.AnotherProperty = AnotherProperty

ps_custom_object = MyPSCustomObject('name', 1)
```

The first example is a lot simpler and works in a similar way to how `[PSCustomObject]$hash` works but the latter allows you to control more aspect when generating the object such as mandatory arguments, calculated properties, custom methods on the Python side, etc.
When the serializer detects an object that does not contain any of the .NET type metadata it does the following:

* If it's a known native type like `str`, `int`, it will serialize it as the [primitive type it maps to](#primitive-types)
* Otherwise is creates a `PSObject` with it's properties set to all the instances properties and attributes

When it comes to deserializing a `PSCustomObject`, there is no rehydration behaviour. It will always be deserialized as a `psrpcore.types.PSCustomObject`.


## Deserialization Behaviour

Here is a brief overview of how `psrpcore` deserializes CLIXML to an object

+ Check if the CLIXML is a basic primitive type or not (XML tag != `Obj`).
  + If it's a primitive type, create new instance for the matching type and return it
+ When it's a complex object, it will search the `TypeRegistry` to see if the type has been registered
  + If the type is registered a new blank instance of the registered class for that type is created
  + If the type is not registered, or the init above failed, a blank `PSObject` is created
  + In the latter case the `PSTypeNames` for the next object are prefixed with `Deserialized.<TypeName>`
+ If the CLIXML contains a `<ToString>` value, that is registered to the object's metadata so `str(obj)` outputs that value
+ It will scan all adapted and extended properties in the CLIXML and add them to the value
  + Even if a rehydrated object was used and did not have that property in the class metadata it will still be added to the new instance
  + This also applies to enums and extended primitive objects
+ If the object wraps a dictionary (XML tag == `DCT`)
  + The value becomes [psrpcore.types.PSDict](./source/psrpcore.types.html#psrpcore.types.PSDict) and is populated with the dict elements
+ If the object wraps a stack (XML tag == `STK`)
  + The value becomes [psrpcore.types.PSStack](./source/psrpcore.types.html#psrpcore.types.PSStack) and is populated with the stack elements
+ If the object wraps a queue (XML tag == `QUE`)
  + The value becomes [psrpcore.types.PSQueue](./source/psrpcore.types.html#psrpcore.types.PSQueue) and is populated with the queue elements
+ If the object wraps a list (XML tag == `LST`)
  + The value becomes [psrpcore.types.PSList](./source/psrpcore.types.html#psrpcore.types.PSList) and is populated with the list elements
+ If the object wraps a IEnumerable (XML tag == `IE`)
  + The value becomes [psrpcore.types.PSIEnumerable](./source/psrpcore.types.html#psrpcore.types.PSIEnumerable) and is populated with the enumerable elements
+ If the object contains a remaining value
  + If the type names match a *registered rehydratable* enum, the enum value is set to this primitive value
  + Else the value now becomes an instance of the primitive value specified instead of a `PSObject`

The end result is:

+ Primitive objects are returned as primitive objects with any extra extended properties that may be present
+ Enums are returned as that enum if the enum type was registered with `rehydrate=True` at the class definition, otherwise the returned object is the primitive value the enum represents
+ Dictionaries are returned as `PSDict`
+ Stacks are returned as `PSStack`
+ Queues are returned as `PSQueue`
+ Lists are returned as `PSList`
+ Other IEnumerables are returned `PSIEnumerable`
+ Other objects are returned as that object if the type was registered with `rehydrate=True` at the class definition, otherwise a `PSObject` is created and has the extended properties set

The `TypeRegistry` mentioned above is a special singleton created by `psrpcore` that contains all the known registered .NET types.
This registry is used to deserialize CLIXML to the proper Python type if available.
The only differences between a rehydrated and plain `PSObject` object are:

+ A rehydrated object is an instance of that registered type, so any methods or properties are accessible
+ A non-rehydrated object is an instance of `psrpcore.types.PSObject`, all the properties are still available
+ A rehydrated object keeps the type names under `obj.PSTypeNames` the way they were in the CLIXML
+ A non-rehydrated object will prefix all of its type names under `obj.PSTypeNames` with `Deserialized.`.


## Add-Member and Update-TypeData

In PowerShell you can add extra properties to an existing object using the [Add-Member](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/add-member?view=powershell-7) cmdlet.
The [Update-TypeData](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/update-typedata?view=powershell-7) does a similar thing but applies the type information to the type itself rather than a specific object.

You can achieve a similar thing in `psrpcore` by using one of the following methods:

+ [add_member](./source/psrpcore.types.html#psrpcore.types.add_member)
+ [add_alias_property](./source/psrpcore.types.html#psrpcore.types.add_alias_property)
+ [add_note_property](./source/psrpcore.types.html#psrpcore.types.add_note_property)
+ [add_script_property](./source/psrpcore.types.html#psrpcore.types.add_script_property)

```python
import psrpcore.types


# The property only applies to the object passed in
obj = psrpcore.types.PSString("testing")
psrpcore.types.add_note_property(obj, "MyProperty", "value")
obj.MyProperty == "value"


# When adding to a type, the property now applies to any new instance of that type
psrpcore.types.add_script_property(psrpcore.types.PSString, "Length", lambda o: len(o))
obj = psrpcore.types.PSString("testing")
obj.Length == 7
```
