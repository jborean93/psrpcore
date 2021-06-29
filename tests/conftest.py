# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

from xmldiff import main as _xmldiff

import psrpcore

# Contains control characters, non-ascii chars, and chars that are surrogate pairs in UTF-16
COMPLEX_STRING = "treble clef\n _x0000_ _X0000_ %s café" % b"\xF0\x9D\x84\x9E".decode("utf-8")
COMPLEX_ENCODED_STRING = "treble clef_x000A_ _x005F_x0000_ _x005F_X0000_ _xD834__xDD1E_ café"


def get_runspace_pair(min_runspaces: int = 1, max_runspaces: int = 1):
    client = psrpcore.ClientRunspacePool(min_runspaces=min_runspaces, max_runspaces=max_runspaces)
    server = psrpcore.ServerRunspacePool()

    client.open()
    server.receive_data(client.data_to_send())
    server.next_event()
    server.next_event()
    client.receive_data(server.data_to_send())
    client.next_event()
    client.next_event()
    client.next_event()

    return client, server


def assert_xml_diff(actual: str, expected: str):
    # We don't care that the XML text is the exact same but rather if they represent the same object. Python versions
    # vary on how they order attributes of an element whereas xmldiff doesn't care.
    diff = _xmldiff.diff_texts(actual, expected)
    if len(diff) != 0:
        # The assertion for diff_texts isn't pretty and it's easier to see what the diff is by comparing the text.
        assert actual == expected
