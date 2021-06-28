# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import psrpcore


def get_runspace_pair(min_runspaces=1, max_runspaces=1):
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
