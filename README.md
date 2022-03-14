# psrpcore - Python PowerShell Remoting Protocol Core Library

[![Test workflow](https://github.com/jborean93/psrpcore/actions/workflows/ci.yml/badge.svg)](https://github.com/jborean93/psrpcore/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jborean93/psrpcore/branch/main/graph/badge.svg?token=UEA7VoocS5)](https://codecov.io/gh/jborean93/psrpcore)
[![PyPI version](https://badge.fury.io/py/psrpcore.svg)](https://badge.fury.io/py/psrpcore)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/jborean93/PSAccessToken/blob/main/LICENSE)

Core library for PowerShell Remoting Protocol (PSRP) in Python.
This library enables you to write either client or a server side implementation for PSRP.
It does not provide any IO or concurrency logic as it's designed to be a pure Python implementation that is then used by other library.
This follows the [sans-IO](https://sans-io.readthedocs.io/) paradigm to promote re-usability and have it focus purely on the protocol logic.


## Documentation

Documentation is available at https://psrpcore.readthedocs.io/.


## Requirements

* CPython 3.6+
* [cryptography](https://github.com/pyca/cryptography)


## Install

### From PyPI

```bash
pip install psrpcore
```

### From Source

```bash
git clone https://github.com/jborean93/psrpcore.git
cd psrpcore
pip install -e .
```
