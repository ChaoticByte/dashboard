# Copyright (c) 2025, Julian Müller (ChaoticByte)


import platform
import socket
import subprocess

from typing import Tuple, List

from nicegui import ui


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
