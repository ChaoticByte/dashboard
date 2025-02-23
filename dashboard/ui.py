# Copyright (c) 2025, Julian Müller (ChaoticByte)

import asyncio
import datetime

from typing import List
from .system import System, SystemState

from nicegui import ui, html, run


def init_ui(
    systems: List[System],
    ui_refresh_interval: float = 2,          # in seconds
    system_state_update_interval: float = 15 # in seconds
):

    @ui.refreshable
    def systems_list():
        with ui.row(wrap=True).classes("justify-center items-stretch"):
            for t in systems:
                if isinstance(t, System):
                    card = ui.card().style("width: 30rem;")
                    if t.state == SystemState.OK:
                        card = card.style("border-left: 4px solid limegreen")
                    elif t.state == SystemState.FAILED:
                        card = card.style("border-left: 4px solid red")
                    else:
                        card = card.style("border-left: 4px solid dodgerblue")

                    with card:
                        with ui.row(align_items="center").classes("w-full"):
                            ui.label(t.name).classes("text-xl font-medium text-wrap")
                            ui.space()
                            ui.label(datetime.datetime.fromtimestamp(t.last_update).strftime(r"%H:%M:%S")).classes("opacity-25 text-xs")
                        if t.description != "":
                            ui.label(t.description).classes("opacity-75 text-wrap")
                        if t.state_verbose != "":
                            html.pre(t.state_verbose).classes("opacity-50 text-xs text-wrap")
                        actions = t.get_actions()
                        if len(actions) > 0:
                            if t.description != "" or t.state_verbose != "":
                                ui.separator().style("margin-top: auto;")
                            with ui.card_actions():
                                for n, c in actions.items():
                                    ui.button(text=n, on_click=c)
                elif isinstance(t, str):
                    ui.label(t).classes("text-2xl textmedium w-full text-center").style("margin-top: 1.5rem; margin-bottom: .5rem")

    with ui.column(align_items="center").classes("w-full"):
        systems_list()

    async def update_states():
        coros = []
        for t in systems:
            if isinstance(t, System):
                # we start all ...
                coros.append(run.io_bound(t._update_state))
        # ... and await later.
        asyncio.gather(*coros)

    ui.timer(system_state_update_interval, callback=update_states)
    ui.timer(ui_refresh_interval, systems_list.refresh)

    dark = ui.dark_mode(None) # auto
