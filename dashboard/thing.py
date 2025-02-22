# Copyright (c) 2025, Julian Müller (ChaoticByte)


from enum import Enum


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

    def get_actions(self) -> dict:
        # to be overridden
        # return {'ActionName': callable, ...}
        return {}

    def update_state(self):
        # to be overridden
        self.state = SystemState.UNKNOWN
        self.state_verbose = ""
