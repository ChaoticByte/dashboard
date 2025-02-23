# Copyright (c) 2025, Julian Müller (ChaoticByte)


from typing import List
from .system import System, SystemState

from nicegui import ui


def init_ui(
    systems: List[System],
    ui_refresh_interval: float = 2,          # in seconds
    system_state_update_interval: float = 15 # in seconds
):

    @ui.refreshable
    def systems_list():
        with ui.column(align_items="center").style("width: 40vw; max-width: 40rem; min-width: 25rem;"):
            for t in systems:
                card = ui.card().classes("w-full")
                if t.state == SystemState.OK:
                    card = card.style("border-left: 4px solid limegreen")
                elif t.state == SystemState.FAILED:
                    card = card.style("border-left: 4px solid red")
                else:
                    card = card.style("border-left: 4px solid dodgerblue")
                
                with card:
                    ui.label(t.name).classes("text-xl font-medium")
                    if t.description != "":
                        ui.label(t.description).classes("opacity-75")
                    if t.state_verbose != "":
                        ui.label(t.state_verbose).classes("opacity-50")
                    actions = t.get_actions()
                    if len(actions) > 0:
                        if t.description != "" or t.state_verbose != "":
                            ui.separator()
                        with ui.card_actions():
                            for n, c in actions.items():
                                ui.button(text=n, on_click=c)

    with ui.column(align_items="center").classes("w-full"):
        systems_list()

    def update_states():
        for t in systems:
            t.update_state()

    ui.timer(system_state_update_interval, callback=update_states)
    ui.timer(ui_refresh_interval, systems_list.refresh)

    dark = ui.dark_mode(None) # auto
