# Copyright (c) 2025, Julian Müller (ChaoticByte)


# additional libraries

import platform
import requests
import subprocess
import time

from enum import Enum
from typing import Tuple


# base classes and types and stuff

class SystemState(Enum):
    OK = 0
    FAILED = 1
    UNKNOWN = 2

class System:

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.state = SystemState.UNKNOWN
        self.state_verbose = ""
        self.last_update = 0

    def get_actions(self) -> dict:
        # to be overridden
        # return {'ActionName': callable, ...}
        return {}

    def _update_state(self):
        self.update_state()
        self.last_update = time.time()

    def update_state(self):
        # to be overridden
        self.state = SystemState.UNKNOWN
        self.state_verbose = ""


# some basic systems


class PingableSystem(System):

    def __init__(self, name, description, host: str):
        super().__init__(name, description)
        self.host = host

    def ping(self) -> Tuple[bool, str, str]:
        if platform.system().lower() == "windows": p = "-n"
        else: p = "-c"
        s = subprocess.run(["ping", p, '1', self.host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return s.returncode == 0, s.stdout.decode(), s.stderr.decode()

    def update_state(self):
        self.state = SystemState.UNKNOWN
        ok, stdout, stderr = self.ping()
        if ok:
            self.state = SystemState.OK
            self.state_verbose = stdout
        else:
            self.state = SystemState.FAILED
            self.state_verbose = stdout + "\n" + stderr


class HTTPServer(System):

    def __init__(self, name, description, url: str, expected_status_code: int = 200, allow_self_signed_cert: bool = False):
        super().__init__(name, description)
        self.url = url
        self.expected_status = expected_status_code
        self.allow_self_signed_cert = allow_self_signed_cert

    def update_state(self):
        self.state = SystemState.UNKNOWN
        try:
            r = requests.head(self.url, timeout=1.0, verify=not self.allow_self_signed_cert)
            if r.status_code == 200:
                self.state = SystemState.OK
            else:
                self.state = SystemState.FAILED
            self.state_verbose = f"Status {r.status_code} {r.url}"
        except requests.ConnectionError as e:
            self.state = SystemState.FAILED
            self.state_verbose = f"Exception: {str(e)}"
