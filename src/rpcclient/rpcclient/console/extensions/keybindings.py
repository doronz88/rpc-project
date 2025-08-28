from dataclasses import dataclass
from typing import Any, Callable

from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.filters import EmacsInsertMode, HasFocus, HasSelection, ViInsertMode
from prompt_toolkit.keys import Keys


@dataclass
class Keybinding:
    """ Single keybinding entry for the console. """
    key: str
    description: str
    callback: Callable[..., None]


def get_keybindings(console: Any) -> list[Keybinding]:
    """ Return the list of default keybindings for the given console. """
    return [
        Keybinding(key=Keys.F1, description='Show this help', callback=console.show_help),
        Keybinding(key=Keys.F2, description='Show active contexts', callback=console.show_contexts),
        Keybinding(key=Keys.F3, description='Previous context', callback=console.previous_context),
        Keybinding(key=Keys.F4, description='Toggle Auto switch on creation', callback=console.toggle_auto_switch),
    ]


def load_ipython_extension(ipython: Any) -> None:
    """ IPython entry-point to register console keybindings. """

    def register_keybindings() -> None:
        """ Register keybindings on the running IPython application. """
        console = ipython.user_ns['console']
        insert_mode = ViInsertMode() | EmacsInsertMode()
        registry = ipython.pt_app.key_bindings

        for keybind in get_keybindings(console):
            registry.add_binding(
                keybind.key,
                filter=(HasFocus(DEFAULT_BUFFER) & ~HasSelection() & insert_mode),
            )(keybind.callback)

    register_keybindings()
    ipython.events.register('shell_initialized', register_keybindings)
