# Changelog

## 0.3.1 - 2024-11-11

* Fixed CLIXML string pattern matching to only match valid hex sequences and not just any alphanumeric character
* Added official support for Python 3.13

## 0.3.0 - 2024-04-23

* Dropped support for Python 3.7
* Tested with Python 3.12
* Added `psrpcore.types.deserialize_clixml` and `psrpcore.types.serialize_clixml`
  * These methods can deserialize and serialize CLIXML strings directly
* Removed invalid `__init__.py` entries `ps_data_packet` and `ps_guid_packet` as they were never defined
* Add  `psrpcore.types.InformationRecord.create` class method to more easily create information records
* **BREAKING CHANGE** - Changed signature of `psrpcore.types.PSCryptoProvider`
  * No longer an abstract base class, methods default to raising `NotImplementedError`
  * Removed the `register_key` function as it has no relation to serialization work
  * Changed the `encrypt` and `decrypt` methods to work with the raw XML element text instead of bytes
  * These changes are needed to support different serialization mechanisms used by PowerShell
  * Unless you were using `psrpcore.types.serialize` and `psrpcore.types.deserialize` directly this should not affect you

## 0.2.2 - 2023-03-01

* Fix up Python 3.11.2 flag enum issues when doing bit operations like `|` and `&`

## 0.2.1 - 2022-12-19

+ Fix up DateTime serialization
    + DateTimes with no timezone specified will be of the `Unspecified` kind and vice versa
    + DateTimes with the UTC timezone specified will be of the `Utc` kind and vice versa
    + DateTimes with a custom timezone specified will be one of the `Local` kind and deserialized with the time zone specified
    + A change in behaviour is that originally a Python datetime with no timezone became a `Utc` kind DateTime, not it will be `Unspecified

## 0.2.0 - 2022-12-06

+ Bump minimum Python version to 3.7 and fix Python 3.11 enum issues

## 0.1.2 - 2022-05-18

+ Fix serialization of strings that include half surrogate pair `[char]` values

## 0.1.1 - 2022-04-06

+ Do not use references for lists and dict types when serializing

## 0.1.0 - 2022-03-28

Initial release
