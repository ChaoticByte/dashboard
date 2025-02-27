# Copyright (c) 2025, Julian Müller (ChaoticByte)


from typing import List

from nicegui import ui

from dashboard.system import Action, HTTPServer, System, SystemState
from dashboard.ui import init_ui

# define systems


class ExampleSystem(System):

    pressed = False

    def __init__(self, *args):
        super().__init__(*args)
        self.started = False

    def update_state(self):
        if self.started:
            self.state = SystemState.OK
            self.state_verbose = f"{self.name} is currently started."
        else:
            self.state = SystemState.FAILED
            self.state_verbose = f"{self.name} is currently stopped."

    def get_actions(self) -> List[Action]:
        actions = []
        if self.started:
            actions.append(Action("Stop", self.stop))
        else:
            actions.append(Action("Start", self.start))
        return actions

    def start(self):
        self.state = SystemState.UNKNOWN
        self.state_verbose = f"{self.name} is currently starting."
        self.started = True
        ui.notify("Starting " + self.name)

    def stop(self):
        self.state = SystemState.UNKNOWN
        self.state_verbose = f"{self.name} is currently stopping."
        self.started = False
        ui.notify("Stopping " + self.name)

#

systems = [
    "Example Heading 1",
    ExampleSystem("Example System 1", "Description text ..."),
    "Example Heading 2",
    HTTPServer("example.org", "The example.org HTTP server.", "https://example.org/")
]

#

init_ui(systems)
ui.run(show=False, title="Dashboard", port=8000)
