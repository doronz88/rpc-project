import ast
import builtins
from typing import Any

from IPython.terminal.interactiveshell import TerminalInteractiveShell

from rpcclient.clients.darwin.objective_c import objective_c_class
from rpcclient.core.symbols_jar import SymbolsJar
from rpcclient.exceptions import GettingObjectiveCClassError, SymbolAbsentError


class RpcEvents:
    """ Small IPython event handler that lazy-loads symbols and Obj-C classes. """

    def __init__(self, ip: TerminalInteractiveShell) -> None:
        """ Store the IPython shell reference. """
        self.ipython = ip

    def pre_run_cell(self, info: Any) -> None:
        """
        Before each cell: inject missing names by lazy-loading SymbolsJar or Objective-C classes.
        Expects `info.raw_cell` to contain the cell source.
        """
        client = self.ipython.user_ns.get('p')
        if client is None:
            return

        for node in ast.walk(ast.parse(info.raw_cell)):
            if not isinstance(node, ast.Name):
                continue

            # Skip names already known to local/global/builtins.
            if node.id in locals() or node.id in globals() or node.id in dir(
                    builtins) or node.id in self.ipython.user_ns:
                continue

            # 1) Generic: SymbolsJar lazy load
            if not hasattr(SymbolsJar, node.id):
                try:
                    symbol = getattr(client.symbols, node.id)
                except SymbolAbsentError:
                    pass
                else:
                    self.ipython.user_ns[node.id] = symbol
                    continue

            # 2) Darwin-specific: Objective-C class autoload / lazy reload
            if hasattr(client, 'objc_get_class'):
                existing = self.ipython.user_ns.get(node.id)
                if isinstance(existing, objective_c_class.Class) and existing.name == '':
                    existing.reload()
                    continue

                try:
                    objc_cls = client.objc_get_class(node.id)
                except GettingObjectiveCClassError:
                    pass
                else:
                    self.ipython.user_ns[node.id] = objc_cls
                    continue


def load_ipython_extension(ip: TerminalInteractiveShell) -> None:
    """ IPython extension hook: register the pre_run_cell handler. """
    handlers = RpcEvents(ip)
    ip.events.register('pre_run_cell', handlers.pre_run_cell)
