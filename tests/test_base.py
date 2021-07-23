# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import re

import pytest

from psrpcore._base import Pipeline, RunspacePool


def test_fail_to_init_runspace_base():
    expected = re.escape(
        "Type RunspacePool cannot be instantiated; it can be used only as a base class for client/server runspace "
        "pool types."
    )

    with pytest.raises(TypeError, match=expected):
        RunspacePool()


def test_fail_to_init_pipeline():
    expected = re.escape(
        "Type Pipeline cannot be instantiated; it can be used only as a base class for client/server pipeline types."
    )

    with pytest.raises(TypeError, match=expected):
        Pipeline(None)
