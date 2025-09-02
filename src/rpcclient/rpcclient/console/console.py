import dataclasses
import logging
import sys
from typing import Any, Union

import click
import IPython
from IPython import get_ipython
from traitlets.config import Config

from rpcclient.client_manager import ClientManager, ClientType
from rpcclient.console.extensions.keybindings import get_keybindings
from rpcclient.exceptions import NoSuchClientError
from rpcclient.registry import Registry, RegistryEvent
from rpcclient.utils import prompt_selection

logger = logging.getLogger(__name__)


def disable_loggers() -> None:
    """ Disable noisy third-party loggers for a cleaner shell. """
    logging.getLogger('asyncio').disabled = True
    logging.getLogger('parso').disabled = True
    logging.getLogger('parso.cache').disabled = True
    logging.getLogger('parso.python.diff').disabled = True
    logging.getLogger('blib2to3.pgen2.driver').disabled = True
    logging.getLogger('humanfriendly.prompts').disabled = True
    logging.getLogger("urllib3.connectionpool").disabled = True
    logging.getLogger("rpcclient.event_dispatcher").disabled = True
    logging.getLogger("rpcclient.client_manager").disabled = True


@dataclasses.dataclass
class HelpSnippet:
    """ Single help line for console shortcuts. """
    key: str
    description: str

    def __str__(self) -> str:
        return click.style(self.key.ljust(8), bold=True, fg='magenta') + click.style(self.description, bold=True)


@dataclasses.dataclass
class ConsoleContext:
    """ Per-client console state (active client and its user namespace). """
    p: ClientType
    user_ns: dict[str, Any] = dataclasses.field(default_factory=dict)

    @property
    def id(self) -> int:
        """ Return the client ID of the client. """
        return self.p.id

    def __repr__(self) -> str:
        """ Debug-friendly representation of the client. """
        return repr(self.p)


def echo_info(msg: str) -> None:
    """ Print an informational message in cyan. """
    click.secho(msg, fg="cyan")


def echo_warn(msg: str) -> None:
    """ Print a warning message in yellow. """
    click.secho(f"⚠ {msg}", fg="yellow")


def echo_error(msg: str) -> None:
    """ Print an error message in red. """
    click.secho(f"✖ {msg}", fg="red", err=True)


def echo_success(msg: str) -> None:
    """ Print a success message in green. """
    click.secho(f"✔ {msg}", fg="green")


def echo_heading(msg: str) -> None:
    """ Print a highlighted heading. """
    click.secho(msg, fg="magenta", bold=True)


class Console:
    """ Interactive IPython console orchestrating multiple RPC clients. """

    def __init__(self, mgr: ClientManager) -> None:
        """ Initialize the console with a client manager and event wiring. """
        self.mgr = mgr
        self._contexts = Registry()
        self._current: Union[int, None] = None
        self._previous: Union[int, None] = None
        self._ipython = None
        self._baseline_keys = None
        self._auto_switch_on_create = True
        self._setup_done = False

        self.mgr.notifier.register(RegistryEvent.REGISTERED, self._on_registered)
        self.mgr.notifier.register(RegistryEvent.UNREGISTERED, self._on_unregistered)
        self.mgr.notifier.register(RegistryEvent.CLEARED, self._on_clear)

    @property
    def contexts(self) -> dict[int, ConsoleContext]:
        return dict(self._contexts.items())

    def init_contexts(self) -> None:
        """ Seed console contexts from current live clients. """
        for cid, client in self.mgr.clients.items():
            if cid in self._contexts:
                continue
            self._contexts.register(cid, ConsoleContext(client))

    def setup_shell(self, switch_cid: Union[int, None] = None) -> None:
        """ One-time shell setup: quiet logs, capture baseline, and optionally switch. """
        if self._setup_done:
            return
        disable_loggers()
        self._ipython = get_ipython()
        self._baseline_keys = set(self._ipython.user_ns.keys())
        self.init_contexts()
        if switch_cid is not None:
            self.switch(switch_cid)
        self._setup_done = True

    def interactive(self, additional_namespace: Union[dict, None] = None, switch_cid: Union[int, None] = None) -> None:
        """ Launch the IPython shell with custom config and extensions. """
        sys.argv = ['a']
        ipython_config = Config()
        ipython_config.IPCompleter.use_jedi = False
        ipython_config.InteractiveShellApp.exec_lines = [f'''console.setup_shell({switch_cid})''']
        ipython_config.TerminalInteractiveShell.autoformatter = None
        ipython_config.BaseIPythonApplication.profile = 'rpcclient'
        ipython_config.TerminalInteractiveShell.prompts_class = 'rpcclient.console.prompt.RpcPrompt'
        ipython_config.InteractiveShellApp.extensions = ['rpcclient.console.extensions.events',
                                                         'rpcclient.console.extensions.keybindings']
        namespace = {'console': self, 'mgr': self.mgr}
        if additional_namespace is not None:
            namespace.update(additional_namespace)

        click.secho('RpcClient has been successfully loaded! 😎', bold=True)
        click.secho('Usage:', bold=True)
        self.show_help()
        click.echo(click.style('Have a nice flight ✈️! Starting an IPython shell...', bold=True))
        IPython.start_ipython(config=ipython_config, user_ns=namespace)
        self.mgr.clear()

    def switch(self, cid: Union[int, None] = None) -> None:
        """ Switch the active console context by client ID (or interactively pick one). """
        if not self._contexts.items():
            raise NoSuchClientError('No clients available')

        if cid is None:
            choices = [ctx for _, ctx in self._contexts.items()]
            ctx = prompt_selection(choices, 'Select a client client ID')
        else:
            ctx = self._contexts.get(cid)

        if ctx is None:
            client = self.mgr.get(cid)
            if client is None:
                echo_error(f'No such client: {cid}')
                return
            ctx = ConsoleContext(client)
            self._contexts.register(client.id, ctx)

        self._switch(ctx)
        echo_success(f'Switched to client client ID: {ctx.id}')

    def _switch(self, ctx: ConsoleContext) -> None:
        """ Internal: swap `p` and per-context variables in the shell namespace. """
        ns = self._ipython.user_ns
        base = self._baseline_keys

        if self._current is not None and self._current in self._contexts:
            cur = self._contexts.get(self._current)
            cur.user_ns = {
                k: v for k, v in ns.items()
                if k not in base and k not in ('p', 'symbols')
            }

        for k in list(ns.keys()):
            if k not in base:
                ns.pop(k, None)

        ns.update(ctx.user_ns)
        ns['p'] = ctx.p

        self._previous = self._current
        self._current = ctx.id

    def _reset_current(self, msg: str = 'Current client has been removed') -> None:
        """Clear current client and console binding, then warn."""
        self._current = None
        self._ipython.user_ns['p'] = None
        echo_warn(msg)

    # ---------------------------------------------------------------------------
    # Client manager — event handlers
    # ---------------------------------------------------------------------------

    def _on_registered(self, cid, client: ClientType) -> None:
        """ Event: auto-switch to a newly created client if enabled. """
        if not (self._auto_switch_on_create and self._ipython):
            return
        ctx = ConsoleContext(client)
        self._contexts.register(cid, ctx)
        self._switch(ctx)
        echo_info(f'Auto-switched to new client client ID: {client.id}')

    def _on_unregistered(self, cid: int) -> None:
        """ Event: clean up context for a removed client. """
        if cid not in self._contexts:
            return
        self._contexts.unregister(cid)
        if self._current != cid:
            return
        self._reset_current()

    def _on_clear(self) -> None:
        """ Event: clean up all contexts. """
        self._contexts.clear()
        self._reset_current()

    # ---------------------------------------------------------------------------
    # Keybinding callbacks
    # ---------------------------------------------------------------------------

    def show_help(self, *_: Any) -> None:
        """ Print console help and keybindings. """
        help_snippets = [
            HelpSnippet(key='mgr', description='Client manager: create | get | remove | clients | clear'),
            HelpSnippet(key='console', description='Console controller: switch'),
            HelpSnippet(key='p', description='Active client (e.g., p.info(), p.pid)'),
        ]
        for keybinding in get_keybindings(self):
            help_snippets.append(HelpSnippet(key=keybinding.key.upper(), description=keybinding.description))

        for help_snippet in help_snippets:
            click.echo(help_snippet)

    def toggle_auto_switch(self, *_: Any) -> None:
        """ Toggle the auto-switch behavior on client creation. """
        self._auto_switch_on_create = not self._auto_switch_on_create
        status = 'enabled' if self._auto_switch_on_create else 'disabled'
        echo_info(f'Auto-switch on client creation: {status}')

    def previous_context(self, *_: Any) -> None:
        """ Switch back to the previous active context. """
        if self._previous is None or self._previous not in self._contexts:
            echo_error('No previous context available.')
            return
        self.switch(self._previous)

    def show_contexts(self, *_: Any) -> None:
        """ List active contexts in a human-readable form. """
        click.echo('\n'.join([str(ctx.p) for _, ctx in self.contexts.items()]))
