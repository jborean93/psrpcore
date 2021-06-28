# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import psrpcore

from xmldiff import main as _xmldiff


def get_runspace_pair(min_runspaces: int = 1, max_runspaces: int = 1):
    client = psrpcore.RunspacePool(min_runspaces=min_runspaces, max_runspaces=max_runspaces)
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
