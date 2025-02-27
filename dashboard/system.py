# Copyright (c) 2025, Julian Müller (ChaoticByte)


# additional libraries


import re
import time

from enum import Enum
from typing import List

from .mixins import PingableMixin, WakeOnLanMixin


# base classes and types and stuff


class Action:

    def __init__(self, name: str, c: callable, *args, **kwargs):
        self.name = name
        self.c = c
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        self.c(*self.args, **self.kwargs)


class SystemState(Enum):
    OK = 0
    FAILED = 1
    UNKNOWN = 2


# base System


class System:

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.state = SystemState.UNKNOWN
        self.state_verbose = ""
        self.last_update = 0

    def get_actions(self) -> List[Action]:
        # to be overridden
        return []

    def _update_state(self):
        self.update_state()
        self.last_update = time.time()

    def update_state(self):
        # to be overridden
        self.state = SystemState.UNKNOWN
        self.state_verbose = ""


# Pingable System


ping_time_regex = re.compile(r".*ttl=\d+ time=((?:\d+\.)?\d+ ms).*")

class PingableSystem(PingableMixin, System):

    def __init__(self, name, description, host: str):
        super().__init__(name, description)
        self.host = host

    def update_state(self):
        try:
            ok, stdout, stderr = self.ping()
            if ok:
                self.state = SystemState.OK
                p_matches = ping_time_regex.findall(stdout)
                if len(p_matches) > 0:
                    self.state_verbose = f"Ping: {p_matches[0]}"
                else:
                    self.state_verbose = stdout.strip("\n\r ")
            else:
                self.state = SystemState.FAILED
                self.state_verbose = (stdout + "\n" + stderr).strip("\n\r ")
        except Exception as e:
            self.state = SystemState.UNKNOWN
            self.state_verbose = f"Exception: {str(e)}"


# Pingable + WakeOnLan System


class PingableWOLSystem(WakeOnLanMixin, PingableSystem):

    '''Pingable System with Wake On LAN'''

    def __init__(self, name, description, host_ip: str, host_mac: str):
        super().__init__(name, description, host_ip)
        self.host_mac = host_mac

    def get_actions(self) -> List[Action]:
        actions = []
        if self.state != SystemState.OK:
            actions.append(Action("Wake On LAN", self.wakeonlan))
        return actions


# HTTP Server System


import requests, urllib3

# don't need the warning, bc. ssl verification needs to be disabled explicitly
urllib3.disable_warnings(category=urllib3.connectionpool.InsecureRequestWarning)


class HTTPServer(System):

    def __init__(self, name, description, url: str, expected_status_code: int = 200, allow_self_signed_cert: bool = False):
        super().__init__(name, description)
        self.url = url
        self.expected_status = expected_status_code
        self.allow_self_signed_cert = allow_self_signed_cert

    def update_state(self):
        try:
            r = requests.head(self.url, timeout=1.0, verify=not self.allow_self_signed_cert)
            if r.status_code == self.expected_status:
                self.state = SystemState.OK
            else:
                self.state = SystemState.FAILED
            self.state_verbose = f"Status {r.status_code} {r.url}"
        except requests.ConnectionError as e:
            self.state = SystemState.FAILED
            self.state_verbose = f"Connection failed: {str(e)}"
        except Exception as e:
            self.state = SystemState.UNKNOWN
            self.state_verbose = f"Exception: {str(e)}"
