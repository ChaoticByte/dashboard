# Copyright (c) 2025, Julian Müller (ChaoticByte)


# additional libraries


import platform
import re
import socket
import subprocess
import time

from enum import Enum
from typing import Dict, List, Tuple

import requests, urllib3
from nicegui import ui
from paramiko.client import SSHClient
from paramiko.pkey import PKey


# don't need the warning, bc. ssl verification needs to be disabled explicitly
urllib3.disable_warnings(category=urllib3.connectionpool.InsecureRequestWarning)


# base classes and types and stuff


class Action:

    def __init__(self, name: str, c: callable, *args, **kwargs):
        self.name = name
        self.c = c
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        try:
            self.c(*self.args, **self.kwargs)
            ui.notify(f"Action '{self.name}' finished.", type="positive")
        except Exception as e:
            ui.notify(f"Exception: {e.__str__()}", close_button=True, type="warning", timeout=0, multi_line=True)
            raise e


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


# Mixins


class PingableMixin:

    def ping(self) -> Tuple[bool, str, str]:
        ''' requires the following attributes:
            - self.host: str    Host ip address
        '''
        if platform.system().lower() == "windows": p = "-n"
        else: p = "-c"
        s = subprocess.run(
            ["ping", p, '1', self.host],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={"LC_ALL": "C"} # don't translate
        )
        return s.returncode == 0, s.stdout.decode(), s.stderr.decode()


class WakeOnLanMixin:

    def wakeonlan(self):
        ''' requires the following attributes:
            - self.name: str        System.name
            - self.host_mac: str    host mac address
        '''
        assert hasattr(self, "host_mac")
        assert hasattr(self, "name")
        host_mac_bin = bytes.fromhex(self.host_mac.replace(':', '').replace('-', '').lower())
        magic_packet = (b'\xff' * 6) + (host_mac_bin * 16)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for port in [7, 9]: # we send to both port 7 and 9 to be compatible with most of the systems
                s.sendto(magic_packet, ("255.255.255.255", port))
            ui.notify(f"Magic packet sent to wake up '{self.name}' ({self.host_mac})")


class SSHMixin:

    '''This mixin allows specifying SSH commands as actions.
    Required attributes:
        - self.host: str
        - self.host_mac
        - self.ssh_commands
        - self.ssh_user
        - self.ssh_key_file
        - self.ssh_key_passphrase   Can be None
        - self.ssh_port
    '''

    def ssh_exec(self, action_name: str, cmd: str):
        ui.notify(f"Executing '{action_name}' on {self.name} ({self.host}) via SSH")
        with SSHClient() as client:
            client.load_system_host_keys()
            client.connect(
                self.host, port=self.ssh_port,
                username=self.ssh_user,
                key_filename=self.ssh_key_file, passphrase=self.ssh_key_passphrase)
            chan = client.get_transport().open_session()
            chan.set_combine_stderr(True)
            chan.exec_command(cmd)
            last_output_chunk = ""
            while not chan.exit_status_ready(): # if we don't do that, we might deadlock
                last_output_chunk = chan.recv(1024)
            if not chan.exit_status == 0:
                raise Exception(f"Exit status is {chan.exit_status}, last stdout: {last_output_chunk.decode()}")

    def actions_from_ssh_commands(self):
        return [Action(name, self.ssh_exec, name, cmd) for name, cmd in self.ssh_commands.items()]


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


# Pingable + SSH


class SSHControllablePingableSystem(SSHMixin, PingableSystem):

    def __init__(
        self, name, description,
        host_ip: str,
        ssh_commands: Dict[str, str], # dict containing "action name": "command ..."
        ssh_user: str,
        ssh_key_file: str,
        ssh_key_passphrase: str = None,
        ssh_port: int = 22,
    ):
        super().__init__(name, description, host_ip)
        self.host = host_ip
        self.ssh_commands = ssh_commands
        self.ssh_user = ssh_user
        self.ssh_key_file = ssh_key_file
        self.ssh_key_passphrase = ssh_key_passphrase
        self.ssh_port = ssh_port

    def get_actions(self) -> List[Action]:
        actions = super().get_actions()
        if not self.state == SystemState.FAILED:
            actions.extend(self.actions_from_ssh_commands())
        return actions


# Pingable + WOL + SSH


class SSHControllablePingableWOLSystem(WakeOnLanMixin, SSHControllablePingableSystem):

    def __init__(
        self, name, description,
        host_ip: str, host_mac: str,
        ssh_commands: Dict[str, str], # dict containing "action name": "command ..."
        ssh_user: str,
        ssh_key_file: str,
        ssh_key_passphrase: str = None,
        ssh_port: int = 22,
    ):
        super().__init__(
            name, description, host_ip,
            ssh_commands=ssh_commands,
            ssh_user=ssh_user,
            ssh_key_file=ssh_key_file,
            ssh_key_passphrase=ssh_key_passphrase,
            ssh_port=ssh_port
        )
        self.host_mac = host_mac


    def get_actions(self) -> List[Action]:
        actions = super().get_actions()
        if self.state != SystemState.OK:
            actions.append(Action("Wake On LAN", self.wakeonlan))
        return actions


# alias :)
Doggo = SSHControllablePingableWOLSystem


# HTTP Server System


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
