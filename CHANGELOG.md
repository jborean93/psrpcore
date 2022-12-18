# Changelog

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
