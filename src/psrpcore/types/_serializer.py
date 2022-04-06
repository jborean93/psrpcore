# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import base64
import binascii
import datetime
import decimal
import enum
import logging
import queue
import re
import typing
import uuid
import weakref
from xml.etree import ElementTree

from psrpcore.types._base import (
    PSCryptoProvider,
    PSObject,
    PSObjectMeta,
    TypeRegistry,
    add_note_property,
)
from psrpcore.types._collection import (
    PSDict,
    PSDictBase,
    PSIEnumerable,
    PSList,
    PSListBase,
    PSQueue,
    PSQueueBase,
    PSStack,
    PSStackBase,
    _PSListBase,
)
from psrpcore.types._complex import ProgressRecord, ProgressRecordType, PSCustomObject
from psrpcore.types._enum import PSEnumBase, PSFlagBase
from psrpcore.types._primitive import (
    PSByte,
    PSByteArray,
    PSChar,
    PSDateTime,
    PSDecimal,
    PSDouble,
    PSDuration,
    PSGuid,
    PSInt,
    PSInt16,
    PSInt64,
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
    _timedelta_total_nanoseconds,
)

log = logging.getLogger(__name__)


# Finds _x in a case insensitive way which we need to escape first as '_x' is the escape code.
_STRING_SERIAL_ESCAPE_ESCAPE = re.compile("(?i)_(x)")

# Finds C0, C1, and surrogate pairs in a unicode string for us to encode according to the PSRP rules.
_STRING_SERIAL_ESCAPE = re.compile("[\u0000-\u001F\u007F-\u009F\U00010000-\U0010FFFF]")

# To support surrogate UTF-16 pairs we need to use a UTF-16 regex so we can replace the UTF-16 string representation
# with the actual UTF-16 byte value and then decode that.
_STRING_DESERIAL_FIND = re.compile(b"\\x00_\\x00x([\\0\\w]{8})\\x00_")

# Python datetime only supports up to microsecond precision but .NET can go to 100 nanoseconds. To support this level
# of precision we need to extract the fractional seconds part of a datetime ourselves and compute the value.
_DATETIME_FRACTION_PATTERN = re.compile(r"\.(\d+)(.*)")

# Python 3.6 strptime with '%z' doesn't support timezone offsets with : in it. This matches the offset at the end so
# the code can remove the : from it.
_DATETIME_TZ_OFFSET_PATTERN = re.compile(r"(?P<offset>\+|\-)(?P<hours>\d{1,2}):(?P<minutes>\d{1,2})$")

# Need to extract the Day, Hour, Minute, Second fields from a XML Duration format. Slightly modified from the below.
# Has named capturing groups, no years or months are allowed and the seconds can only be up to 7 decimal places.
# https://stackoverflow.com/questions/52644699/validate-a-xsduration-using-a-regular-expression-in-javascript
_DURATION_PATTERN = re.compile(
    r"""
^(?P<negative>-?)                         # Can start with - to denote a negative duration.
P(?=.)                                    # Must start with P and contain one of the following matches.
    ((?P<days>\d+)D)?                     # Number of days.
    (T(?=.)                               # Hours/Minutes/Seconds are located after T, must contain 1 of them.
        ((?P<hours>\d+)H)?                # Number of hours.
        ((?P<minutes>\d+)M)?              # Number of minutes.
        ((?P<seconds>\d*                  # Number of seconds, can be a decimal number up to 7 decimal places.
        (\.(?P<fraction>\d{1,7}))?)S)?    # Optional fractional seconds as a 2nd capturing group.
    )?                                    # T is optional, the pos lookahead ensures either T or days is present.
$""",
    re.VERBOSE,
)


def deserialize(
    value: ElementTree.Element,
    cipher: PSCryptoProvider,
    **kwargs: typing.Any,
) -> typing.Optional[typing.Union[bool, PSObject]]:
    """Deserialize CLIXML to a Python object.

    Deserializes a CLIXML XML Element from .NET to a Python object.

    Args:
        value: The CLIXML XML Element to deserialize to a Python object.
        cipher: The Runspace Pool cipher to use for SecureStrings.
        kwargs: Optional parameters to sent to the FromPSObjectForRemoting
            method on classes that use that.

    Returns:
        Optional[Union[bool, PSObject]]: The CLIXML as an XML Element object.
    """
    return _Serializer(cipher, **kwargs).deserialize(value)


def serialize(
    value: typing.Optional[typing.Any],
    cipher: PSCryptoProvider,
    **kwargs: typing.Any,
) -> ElementTree.Element:
    """Serialize the Python object to CLIXML.

    Serializes a Python object to a CLIXML element for use in .NET.

    Args:
        value: The value to serialize.
        cipher: The Runspace Pool cipher to use for SecureStrings.
        kwargs: Optional parameters to sent to the ToPSObjectForRemoting
            method on classes that use that.

    Returns:
        ElementTree.Element: The CLIXML as an XML Element object.
    """
    return _Serializer(cipher, **kwargs).serialize(value)


def _deserialize_datetime(
    value: str,
) -> PSDateTime:
    """Deserializes a CLIXML DateTime string.

    DateTime values from PowerShell are in the format
    'YYYY-MM-DDTHH:MM-SS[.100's of nanoseconds]Z'. Unfortunately Python's
    datetime type only supports up to a microsecond precision so we need to
    extract the fractional seconds and then parse as a string while calculating
    the nanoseconds ourselves.

    Args:
        value: The CLIXML datetime string value to deserialize.

    Returns:
        (PSDateTime): A PSDateTime of the .NET DateTime object.
    """
    datetime_str = value[:19]
    fraction_tz_section = value[19:]
    nanoseconds = 0

    fraction_match = _DATETIME_FRACTION_PATTERN.match(fraction_tz_section)
    if fraction_match:
        # We have fractional seconds, need to rewrite as microseconds and keep the nanoseconds ourselves.
        fractional_seconds = fraction_match.group(1)
        if len(fractional_seconds) > 6:
            # .NET should only be showing 100's of nanoseconds but just to be safe we will calculate that based
            # on the length of the fractional seconds found.
            nanoseconds = int(fractional_seconds[-1:]) * (10 ** (3 + 6 - len(fractional_seconds)))
            fractional_seconds = fractional_seconds[:-1]

        timezone_section = fraction_match.group(2)

        datetime_str += f".{fractional_seconds}{timezone_section}"
    else:
        # No fractional seconds, just use strptime on the original value.
        datetime_str = value

    offset_match = _DATETIME_TZ_OFFSET_PATTERN.search(datetime_str)
    if offset_match:
        matches = offset_match.groupdict()
        offset = matches["offset"]
        hours = int(matches["hours"])
        minutes = int(matches["minutes"])

        datetime_str = f"{datetime_str[:-len(offset_match.group())]}{offset}{hours:02}{minutes:02}"

    elif datetime_str.endswith("Z"):
        # Python 3.6 doesn't support '%z' matching 'Z' at the end of a string.
        datetime_str = datetime_str[:-1] + "+0000"

    try:
        dt = PSDateTime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        # Try without fractional seconds
        dt = PSDateTime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S%z")
    dt.nanosecond = nanoseconds

    return dt


def _deserialize_duration(
    value: str,
) -> PSDuration:
    """Deserializes a CLIXML Duration.

    Deserializes a CLIXML Duration into a PSDuration/timedelta object.

    Args:
        value: The CLIXML string value to deserialize.

    Returns:
        (PSDuration): The timedelta object.
    """
    duration_match = _DURATION_PATTERN.match(value)
    if not duration_match:
        raise ValueError(f"Duration input '{value}' is not valid, cannot deserialize")
    matches = duration_match.groupdict()

    is_negative = bool(matches["negative"])
    days = int(matches["days"] or 0)
    hours = int(matches["hours"] or 0)
    minutes = int(matches["minutes"] or 0)

    seconds = int(float(matches["seconds"] or 0))
    seconds += minutes * 60
    seconds += hours * 3600
    seconds += days * 86400
    nanoseconds = int((matches["fraction"] or "").ljust(7, "0")) * 100

    total = (seconds * 1000000000) + nanoseconds
    if is_negative:
        total *= -1

    return PSDuration(nanoseconds=total)


def _deserialize_progress_record(
    value: ElementTree.Element,
) -> ProgressRecord:
    """Deserializes a CLIXML ProgressRecord.

    Progress records in CLIXML are serialized in a different way compared to
    other .NET classes. This is not documented in the MS-PSRP docs so the logic
    is based on what was exchanged in a pwsh session.

    Args:
        value: The CLIXML element to deserialize.

    Returns:
        (ProgressRecord): The ProgressRecord value that was deserialized.
    """
    record_kwargs = {}
    for element_key, prop_name, prop_type in [
        ("AV", "Activity", str),
        ("AI", "ActivityId", int),
        ("S", "CurrentOperation", str),
        ("PI", "ParentActivityId", int),
        ("PC", "PercentComplete", int),
        ("T", "RecordType", ProgressRecordType),
        ("SR", "SecondsRemaining", int),
        ("SD", "StatusDescription", str),
    ]:
        element_value = value.find(element_key)
        if element_value is None or not element_value.text:
            continue

        prop_value: typing.Union[int, str, ProgressRecordType]
        if prop_type == int:
            prop_value = int(element_value.text)

        else:
            prop_value = _deserialize_string(element_value.text)

        if prop_type == ProgressRecordType:
            prop_value = ProgressRecordType[str(prop_value)]

        record_kwargs[prop_name] = prop_value

    return ProgressRecord(**record_kwargs)


def _deserialize_string(
    value: str,
) -> str:
    """Deserializes a CLIXML string value.

    String values in CLIXML have escaped values for control chars and
    characters that are represented as surrogate pairs in UTF-16. This converts
    the raw CLIXML string value into a Python string.

    Args:
        value: The CLIXML string element to deserialize.

    Returns:
        (str): The Python str value that represents the actual string
            represented by the CLIXML.
    """

    def rplcr(matchobj: typing.Any) -> bytes:
        # The matched object is the UTF-16 byte representation of the UTF-8 hex string value. We need to decode the
        # byte str to unicode and then unhexlify that hex string to get the actual bytes of the _x****_ value, e.g.
        # group(0) == b'\x00_\x00x\x000\x000\x000\x00A\x00_'
        # group(1) == b'\x000\x000\x000\x00A'
        # unicode (from utf-16-be) == '000A'
        # returns b'\x00\x0A'
        match_hex = matchobj.group(1)
        hex_string = match_hex.decode("utf-16-be")
        return binascii.unhexlify(hex_string)

    # Need to ensure we start with a unicode representation of the string so that we can get the actual UTF-16 bytes
    # value from that string.
    b_value = value.encode("utf-16-be")
    b_escaped = re.sub(_STRING_DESERIAL_FIND, rplcr, b_value)

    return b_escaped.decode("utf-16-be")


def _serialize_datetime(
    value: datetime.datetime,
) -> str:
    """Serializes a datetime to a .NET DateTime CLIXML value.

    .NET supports DateTime to a 100 nanosecond precision so we need to manually
    massage the data from Python to suit that precision if it is set.

    Args:
        value: The PSDateTime or datetime.datetime object to serialize as a
            .NET DateTime CLIXML string.

    Returns:
        str: The .NET DateTime CLIXML string value.
    """
    fraction_seconds = ""
    nanoseconds = getattr(value, "nanosecond", None)
    if value.microsecond or nanoseconds:
        fraction_seconds = value.strftime(".%f")

        if nanoseconds:
            fraction_seconds += str(nanoseconds // 100)

    timezone = "Z"
    if value.tzinfo:
        # Python's timezone strftime format doesn't quite match up with the .NET one.
        utc_offset = value.strftime("%z")
        timezone = f"{utc_offset[:3]}:{utc_offset[3:]}"

    dt_str = value.strftime(f"%Y-%m-%dT%H:%M:%S{fraction_seconds}{timezone}")

    return dt_str


def _serialize_duration(
    value: datetime.timedelta,
) -> str:
    """Serialzies a duration to a .NET TimeSpan CLIXML value.

    .NET TimeSpans supports a precision to 100 nanoseconds so we need to
    manually massage the timedelta object from Python to suit that precision if
    it is available.

    Args:
        value: The PSDuration or datetime.timedelta object to serialize as a
            .NET TimeSpan CLIXML string.

    Returns:
        str: The .NET TimeSpan CLIXML string value.
    """
    # We can only go to 100s of nanoseconds in .NET.
    total_ticks = _timedelta_total_nanoseconds(value) // 100

    negative_str = ""
    if total_ticks < 0:
        negative_str = "-"
        total_ticks *= -1

    days, total_ticks = divmod(total_ticks, 864000000000)

    days_str = f"{days}D" if days else ""
    time_str = ""
    if total_ticks or days == 0:
        hours, total_ticks = divmod(total_ticks, 36000000000)
        minutes, total_ticks = divmod(total_ticks, 600000000)
        seconds = total_ticks / 10000000

        days_str = f"{days}D" if days else ""
        hours_str = f"{hours}H" if hours else ""
        minutes_str = f"{minutes}M" if minutes else ""
        seconds_str = f"{seconds:.7f}" if (seconds or (not hours_str and not minutes_str)) else ""
        if seconds_str:
            seconds_str = seconds_str.rstrip(".0").zfill(1) + "S"

        time_str = f"T{hours_str}{minutes_str}{seconds_str}"

    return f"{negative_str}P{days_str}{time_str}"


def _serialize_enum_to_string(
    value: enum.Enum,
) -> str:
    flags: typing.List[enum.Enum]

    if isinstance(value, enum.Flag):
        flags = [f for f in type(value) if f in value]
    else:
        flags = [value]

    normalize_none = isinstance(value, (PSEnumBase, PSFlagBase))

    return ", ".join(
        ["None" if f.name == "none" and normalize_none else f.name for f in flags if f.value != 0 or len(flags) == 1]
    )


def _serialize_string(
    value: str,
) -> str:
    """Serializes a string like value to a .NET String CLIXML value.

    There are certain rules when it comes to escaping certain codepoints and
    chars that are surrogate pairs when UTF-16 encoded. This method escapes the
    string value and turns it into a valid CLIXML string value.

    Args:
        value: The string value to serialize to CLIXML.

    Returns:
        str: The string value as a valid CLIXML escaped string.
    """

    def rplcr(matchobj: typing.Any) -> str:
        surrogate_char = matchobj.group(0)
        byte_char = surrogate_char.encode("utf-16-be")
        hex_char = binascii.hexlify(byte_char).decode().upper()
        hex_split = [hex_char[i : i + 4] for i in range(0, len(hex_char), 4)]

        return "".join([f"_x{i}_" for i in hex_split])

    # Before running the translation we need to make sure _ before x is encoded, normally _ isn't encoded except
    # when preceding x. The MS-PSRP docs don't state this but the _x0000_ matcher is case insensitive so we need to
    # make sure we escape _X as well as _x.
    value = re.sub(_STRING_SERIAL_ESCAPE_ESCAPE, "_x005F_\\1", value)
    value = re.sub(_STRING_SERIAL_ESCAPE, rplcr, value)

    return value


class _Serializer:
    """The Python object serializer.

    This is used to encapsulate the (de)serialization of Python objects to and
    from CLIXML. An instance of this class should only be used once as it
    contains a reference map to objects that are serialized in that message.
    Use the :meth:`serialize` and :meth:`deserialize` instead of calling this
    directly.

    Args:
        cipher: The CryptoProvider that is used when serializing/deserializing
            SecureStrings.
    """

    def __init__(
        self,
        cipher: PSCryptoProvider,
        **kwargs: typing.Any,
    ) -> None:
        self._cipher = cipher
        self._kwargs = kwargs

        # Used for serialization to determine fi an object is already serialized or not.
        self._obj_ref: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._obj_ref_enum: typing.Dict[int, int] = {}
        self._obj_ref_id = 0
        self._tn_ref_list: typing.List[str] = []

        # Used for deserialization
        self._obj_ref_map: typing.Dict[str, typing.Any] = {}
        self._tn_ref_map: typing.Dict[str, typing.List[str]] = {}

        # The type registry stores this in reverse but there are a few times when this is looked up by type.
        self._type_to_element: typing.Dict[typing.Type[PSObject], str] = {
            ps_type: tag for tag, ps_type in TypeRegistry().element_registry.items()
        }

    def serialize(
        self,
        value: typing.Any,
    ) -> ElementTree.Element:
        """Serialize a Python object to a XML element based on the CLIXML value."""
        value_type = type(value)
        ps_object = getattr(value, "PSObject", None)
        ps_type: typing.Type[PSObject]  # To satisfy mypy
        is_enum = isinstance(value, enum.Enum)
        is_extended_primitive: typing.Optional[bool] = None

        # If the value type has a ToPSObjectForRemoting class method we use that to build our true PSObject that will
        # be serialized.
        if hasattr(value_type, "ToPSObjectForRemoting") and not isinstance(value, PSSecureString):
            value = value_type.ToPSObjectForRemoting(value, **self._kwargs)

            if ps_object and hasattr(value, "PSObject"):
                value.PSObject.type_names = ps_object.type_names
                value.PSObject.to_string = ps_object.to_string

            if hasattr(value, "PSObject"):
                ps_object = value.PSObject

        element = None
        if value is None:
            element = ElementTree.Element("Nil")

        elif isinstance(value, bool):
            element = ElementTree.Element("B")
            element.text = str(value).lower()

        elif isinstance(value, bytes):
            element = ElementTree.Element(self._type_to_element[PSByteArray])
            element.text = base64.b64encode(value).decode()

        elif isinstance(value, datetime.datetime):
            element = ElementTree.Element(self._type_to_element[PSDateTime])
            element.text = _serialize_datetime(value)

        elif isinstance(value, datetime.timedelta):
            element = ElementTree.Element(self._type_to_element[PSDuration])
            element.text = _serialize_duration(value)

        # We initially serialize the enum based on the raw value.
        elif is_enum:
            element = self.serialize(value.value)

        # Integer types
        elif isinstance(
            value,
            (
                int,
                float,
                decimal.Decimal,
                PSChar,
                PSSByte,
                PSInt16,
                PSInt,
                PSInt64,
                PSByte,
                PSUInt16,
                PSUInt,
                PSUInt64,
                PSSingle,
                PSDouble,
                PSDecimal,
            ),
        ):
            if isinstance(value, PSObject):
                ps_type = type(value)
            elif isinstance(value, int):
                ps_type = PSInt64 if value > PSInt.MaxValue else PSInt
            elif isinstance(value, float):
                ps_type = PSSingle
            else:
                ps_type = PSDecimal

            # Need to make sure int like types are represented by the int value.
            xml_value = value
            if not isinstance(xml_value, (decimal.Decimal, float)):
                xml_value = int(xml_value)

            element = ElementTree.Element(self._type_to_element[ps_type])
            element.text = str(xml_value).upper()  # upper() needed for the Double and Single types.

        # Naive strings
        elif isinstance(
            value,
            (
                uuid.UUID,
                PSGuid,
                PSVersion,
            ),
        ):
            if isinstance(value, PSObject):
                ps_type = type(value)
            else:
                ps_type = PSGuid

            element = ElementTree.Element(self._type_to_element[ps_type])
            element.text = str(value)

        elif isinstance(value, PSSecureString):
            # ToPSObjectForRemoting here handles the case when the SS was created without a cipher and already contains
            # the plaintext for encryption.
            secure_string = PSSecureString.ToPSObjectForRemoting(value, cipher=self._cipher, **self._kwargs)
            element = ElementTree.Element(self._type_to_element[PSSecureString])
            element.text = str(secure_string)

        # String types that need escaping
        elif isinstance(value, str):
            if isinstance(value, PSObject):
                ps_type = type(value)
            else:
                ps_type = PSString

            try:
                element_tag = self._type_to_element[ps_type]
            except KeyError:
                element_tag = self._type_to_element[PSString]

            element = ElementTree.Element(element_tag)
            element.text = _serialize_string(value)

        elif isinstance(value, ProgressRecord):
            element_tag = self._type_to_element[ProgressRecord]
            element = ElementTree.Element(element_tag)
            ElementTree.SubElement(element, "AV").text = _serialize_string(value.Activity)
            ElementTree.SubElement(element, "AI").text = str(value.ActivityId)

            if value.CurrentOperation is None:
                ElementTree.SubElement(element, "Nil")
            else:
                ElementTree.SubElement(element, "S").text = _serialize_string(value.CurrentOperation)

            ElementTree.SubElement(element, "PI").text = str(value.ParentActivityId)
            ElementTree.SubElement(element, "PC").text = str(value.PercentComplete)
            ElementTree.SubElement(element, "T").text = _serialize_string(value.RecordType.name)
            ElementTree.SubElement(element, "SR").text = str(value.SecondsRemaining)
            ElementTree.SubElement(element, "SD").text = _serialize_string(value.StatusDescription)

            # Special case here, a ProgressRecord is only considered extended if it contains more adapted props or any
            # extended props.
            is_extended_primitive = len(value.PSObject.adapted_properties) > 8 or bool(
                value.PSObject.extended_properties
            )

        # These types of objects need to be placed inside a '<Obj></Obj>' entry.
        if is_extended_primitive is None:
            is_extended_primitive = (
                element is not None
                and isinstance(value, PSObject)
                and bool(value.PSObject.adapted_properties or value.PSObject.extended_properties)
            )

        if element is not None and not is_extended_primitive and not is_enum:
            return element

        ref_id, use_ref = self._get_ref_id(value)
        if use_ref:
            return ElementTree.Element("Ref", RefId=str(ref_id))

        if element is None:
            is_complex = True
            element = ElementTree.Element("Obj", RefId=str(ref_id))

        else:
            is_complex = False
            sub_element = element
            element = ElementTree.Element("Obj", RefId=str(ref_id))
            element.append(sub_element)

        if ps_object is None:
            # Handle edge cases for known Python container and enum types, otherwise default to a PSCustomObject.
            if isinstance(value, list):
                ps_object = PSList.PSObject

            elif isinstance(value, queue.Queue):
                ps_object = PSQueue.PSObject

            elif isinstance(value, dict):
                ps_object = PSDict.PSObject

            elif is_enum:
                # Use the Python type name for a bare enums
                types = list(PSEnumBase.PSObject.type_names)
                types.insert(0, f"{value.__module__}.{type(value).__name__}")
                ps_object = PSObjectMeta(types)

            else:
                ps_object = PSCustomObject.PSObject

        # Do not add the type names for extended primitive object unless it's an enum
        if ps_object.type_names and (is_enum or not is_extended_primitive):
            type_names = ps_object.type_names
            main_type = type_names[0]
            is_ref = main_type in self._tn_ref_list

            if is_ref:
                ref_id = self._tn_ref_list.index(main_type)
                ElementTree.SubElement(element, "TNRef", RefId=str(ref_id))

            else:
                self._tn_ref_list.append(main_type)
                ref_id = self._tn_ref_list.index(main_type)

                tn = ElementTree.SubElement(element, "TN", RefId=str(ref_id))
                for type_name in type_names:
                    ElementTree.SubElement(tn, "T").text = type_name

        no_props = True
        for xml_name, prop_type in [("Props", "adapted"), ("MS", "extended")]:
            properties = getattr(ps_object, f"{prop_type}_properties")
            if not properties:
                continue

            no_props = False
            prop_elements = ElementTree.SubElement(element, xml_name)
            for prop in properties:
                prop_value = prop.get_value(value)

                prop_element = self.serialize(prop_value)
                prop_element.attrib["N"] = _serialize_string(prop.name)
                prop_elements.append(prop_element)

        if isinstance(value, (PSIEnumerable, PSStackBase, PSListBase, list)):
            if isinstance(value, PSIEnumerable):
                element_tag = self._type_to_element[PSIEnumerable]

            elif isinstance(value, PSStackBase):
                element_tag = self._type_to_element[PSStack]

            else:
                element_tag = self._type_to_element[PSList]

            container_element = ElementTree.SubElement(element, element_tag)
            for entry in value:
                container_element.append(self.serialize(entry))

        elif isinstance(value, (PSQueueBase, queue.Queue)):
            que_element = ElementTree.SubElement(element, self._type_to_element[PSQueue])

            while True:
                try:
                    que_entry = self.serialize(value.get(block=False))
                except queue.Empty:
                    break
                else:
                    que_element.append(que_entry)

        elif isinstance(value, (PSDictBase, dict)):
            dct_element = ElementTree.SubElement(element, self._type_to_element[PSDict])

            for dct_key, dct_value in value.items():
                en_element = ElementTree.SubElement(dct_element, "En")

                s_dct_key = self.serialize(dct_key)
                s_dct_key.attrib["N"] = "Key"
                en_element.append(s_dct_key)

                s_dct_value = self.serialize(dct_value)
                s_dct_value.attrib["N"] = "Value"
                en_element.append(s_dct_value)

        else:
            to_string = None
            if is_enum:
                to_string = _serialize_enum_to_string(value)

            elif not is_extended_primitive:
                to_string = ps_object.to_string

            if to_string:
                ElementTree.SubElement(element, "ToString").text = to_string

            if is_complex and no_props and not isinstance(value, PSObject):
                # If this was a complex object but no properties were defined we consider this a normal Python
                # class instance to serialize. We use the instance attributes and properties to create the CLIXML.
                attr_element = None
                private_prefix = f"_{type(value).__name__}__"  # Double underscores appear as _{class name}__{name}
                for prop in dir(value):
                    prop_value = getattr(value, prop)

                    if (
                        prop == "PSObject"
                        or prop.startswith("__")
                        or prop.startswith(private_prefix)
                        or callable(prop_value)
                    ):
                        continue

                    elif not attr_element:
                        attr_element = ElementTree.SubElement(element, "MS")

                    sub_element = self.serialize(prop_value)
                    sub_element.attrib["N"] = _serialize_string(prop)
                    attr_element.append(sub_element)

        return element

    def deserialize(
        self,
        element: ElementTree.Element,
    ) -> typing.Any:
        """Deserializes a XML element of the CLIXML value to a Python type."""
        # These types are pure primitive types and we don't need to do anything special when de-serializing
        element_tag = element.tag
        element_text = element.text or ""

        if element.tag == "Ref":
            return self._obj_ref_map[element.attrib["RefId"]]

        elif element_tag == "Nil":
            return None

        elif element_tag == "B":
            # Technically can be an extended primitive but due to limitations in Python we cannot subclass bool.
            return element_text.lower() == "true"

        elif element_tag == "ToString":
            return _deserialize_string(element_text)

        ps_type = TypeRegistry().element_registry.get(element_tag, None)

        if ps_type == PSSecureString:
            return PSSecureString(element_text, self._cipher)

        elif ps_type == PSByteArray:
            return PSByteArray(base64.b64decode(element_text))

        elif ps_type == PSChar:
            return PSChar(int(element_text))

        elif ps_type == PSDateTime:
            return _deserialize_datetime(element_text)

        elif ps_type == PSDuration:
            return _deserialize_duration(element_text)

        # Integer types
        elif ps_type in [
            PSByte,
            PSDecimal,
            PSDouble,
            PSGuid,
            PSInt16,
            PSInt,
            PSInt64,
            PSSByte,
            PSSingle,
            PSUInt16,
            PSUInt,
            PSUInt64,
            PSVersion,
        ]:
            return ps_type(element.text)

        # String types
        elif ps_type in [
            PSScriptBlock,
            PSString,
            PSUri,
            PSXml,
        ]:
            # Empty strings are `<S />` which means element.text is None.
            return ps_type(_deserialize_string(element_text))

        elif ps_type == ProgressRecord:
            return _deserialize_progress_record(element)

        # By now we should have an Obj, if not something has gone wrong.
        if element_tag != "Obj":
            raise ValueError(f"Unknown element found: {element.tag}")

        type_names = [e.text or "" for e in element.findall("TN/T")]
        if type_names:
            tn_ref = element.find("TN")
            if tn_ref is not None:
                tn_ref_id = tn_ref.attrib["RefId"]
                self._tn_ref_map[tn_ref_id] = type_names

        else:
            tn_ref = element.find("TNRef")
            if tn_ref is not None:
                tn_ref_id = tn_ref.attrib["RefId"]
                type_names = self._tn_ref_map[tn_ref_id]

        # Build the starting value based on the registered types. This could either be a rehydrated class that has been
        # registered with the TypeRegistry or just a blank PSObject.
        rehydrated_value = TypeRegistry().rehydrate(type_names)
        value: PSObject
        original_type_names: typing.List[str] = []
        ref_id = element.attrib.get("RefId", None)

        if isinstance(rehydrated_value, PSObject):
            value = self._update_value_ref(rehydrated_value, ref_id)
            original_type_names = rehydrated_value.PSObject.type_names

        elif issubclass(rehydrated_value, (PSEnumBase, PSFlagBase)):
            original_type_names = rehydrated_value.PSObject.type_names

        props: typing.Dict[str, typing.Optional[ElementTree.Element]] = {
            "adapted_properties": None,
            "extended_properties": None,
        }
        to_string = None
        for obj_entry in element:
            if obj_entry.tag == "Props":
                props["adapted_properties"] = obj_entry

            elif obj_entry.tag == "MS":
                props["extended_properties"] = obj_entry

            elif obj_entry.tag == "ToString":
                to_string = self.deserialize(obj_entry)

            elif obj_entry.tag == self._type_to_element[PSDict]:
                dict_type: typing.Type[PSDictBase] = PSDict
                if isinstance(value, PSDictBase):
                    dict_type = type(value)

                value = self._update_value_ref(dict_type(), ref_id)

                for dict_entry in obj_entry:
                    dict_key = dict_entry.find('*/[@N="Key"]')
                    dict_value = dict_entry.find('*/[@N="Value"]')
                    if dict_key is None:
                        raise ValueError("Failed to find dict Key attribute")

                    if dict_value is None:
                        raise ValueError("Failed to find dict Value attribute")

                    value[self.deserialize(dict_key)] = self.deserialize(dict_value)

            elif obj_entry.tag == self._type_to_element[PSQueue]:
                if not isinstance(value, PSQueueBase):
                    value = self._update_value_ref(PSQueue(), ref_id)

                for queue_entry in obj_entry:
                    value.put(self.deserialize(queue_entry))

            elif obj_entry.tag in [
                self._type_to_element[PSIEnumerable],
                self._type_to_element[PSList],
                self._type_to_element[PSStack],
            ]:
                list_type: typing.Type[_PSListBase]

                if obj_entry.tag == self._type_to_element[PSIEnumerable]:
                    list_type = PSIEnumerable

                elif obj_entry.tag == self._type_to_element[PSList]:
                    list_type = PSList

                else:
                    list_type = PSStack

                if isinstance(value, _PSListBase):
                    list_type = type(value)

                value = self._update_value_ref(list_type(), ref_id)
                for list_entry in obj_entry:
                    value.append(self.deserialize(list_entry))

            elif obj_entry.tag not in ["TN", "TNRef"]:
                # Extended primitive types and enums store the value as a sub element of the Obj.
                new_value = self.deserialize(obj_entry)

                if isinstance(rehydrated_value, type) and issubclass(rehydrated_value, (PSEnumBase, PSFlagBase)):
                    value = self._update_value_ref(rehydrated_value(new_value), ref_id)

                else:
                    # If the TypeRegister returned any types, set them on the new object name.
                    if value.PSTypeNames:
                        new_value.PSObject.type_names = value.PSTypeNames

                    value = self._update_value_ref(new_value, ref_id)

        if to_string is not None:
            value.PSObject.to_string = to_string

        if isinstance(value, PSObject):
            # Ensure the object's type names are what was in the CLIXML
            if original_type_names:
                value.PSObject.type_names = original_type_names

            for prop_group_name, prop_xml in props.items():
                if prop_xml is None:
                    continue

                # add_note_property only sets to extended properties. We just use the actual prop list as the scratch
                # object's extended properties. Anything modified/added will reflect in our actual object property.
                scratch_obj = PSCustomObject()
                scratch_obj.PSObject.extended_properties = getattr(value.PSObject, prop_group_name)
                for obj_property in prop_xml:
                    prop_name = _deserialize_string(obj_property.attrib["N"])
                    prop_value = self.deserialize(obj_property)
                    add_note_property(scratch_obj, prop_name, prop_value, force=True)

        # Final override that allows classes to transform the raw CLIXML deserialized object to something more human
        # friendly.
        from_override = getattr(type(value), "FromPSObjectForRemoting", None)
        if from_override:
            value = self._update_value_ref(from_override(value, **self._kwargs), ref_id)

        return value

    def _get_ref_id(
        self,
        value: typing.Any,
    ) -> typing.Tuple[int, bool]:
        """Determine the object reference id for serialization."""
        next_ref_id = self._obj_ref_id

        try:
            ref_id = self._obj_ref.setdefault(value, next_ref_id)
        except TypeError as e:
            # Some objects cannot have a weakref, try id() only when dealing with known workable types.
            if isinstance(value, enum.Enum):
                ref_id = self._obj_ref_enum.setdefault(id(value), next_ref_id)

            else:
                ref_id = next_ref_id

        existing_ref = True
        if next_ref_id == ref_id:
            existing_ref = False
            self._obj_ref_id += 1

        return ref_id, existing_ref

    def _update_value_ref(
        self,
        value: typing.Any,
        ref_id: typing.Optional[str] = None,
    ) -> typing.Any:
        """Updates the value ref table if the ref id and value is specified."""
        if ref_id is not None and value is not None:
            self._obj_ref_map[ref_id] = value

        return value
