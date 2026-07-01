import ast
import builtins

from IPython.core.interactiveshell import ExecutionInfo
from IPython.terminal.interactiveshell import TerminalInteractiveShell

from rpcclient.clients.darwin.objective_c import objective_c_class
from rpcclient.core.symbols_jar import SymbolsJar
from rpcclient.exceptions import GettingObjectiveCClassError, SymbolAbsentError
from rpcclient.utils import run_in_loop


class RpcEvents:
    """Small IPython event handler that lazy-loads symbols and Obj-C classes."""

    def __init__(self, ip: TerminalInteractiveShell) -> None:
        """Store the IPython shell reference."""
        self.ipython = ip

    def pre_run_cell(self, info: ExecutionInfo) -> None:
        """
        Before each cell: inject missing names by lazy-loading SymbolsJar or Objective-C classes.
        Expects `info.raw_cell` to contain the cell source.
        """
        client = self.ipython.user_ns.get("p")
        if client is None:
            return

        if info.raw_cell is None:
            return

        # Skip parsing of this cell if it's an IPython's magic transformation (like '!', '?', '%')
        if (
            hasattr(info, "transformed_cell")  # Added in IPython 9.0, which requires Python 3.11+.
            and info.raw_cell != info.transformed_cell.rstrip("\n")  # pyright: ignore[reportOptionalMemberAccess]
        ):
            return

        for node in ast.walk(ast.parse(info.raw_cell)):
            if not isinstance(node, ast.Name):
                continue

            existing = self.ipython.user_ns.get(node.id)
            objc_class_place_holder = (
                isinstance(existing, objective_c_class.Class) and getattr(existing, "name", "") == ""
            )

            # Skip names already known to local/global/builtins.
            if (
                node.id in locals()
                or node.id in globals()
                or node.id in dir(builtins)
                or (existing is not None and not objc_class_place_holder)
            ):
                continue

            # 1) Generic: resolve the name to a real symbol. `get_lazy` performs the dlsym round-trip
            # and raises SymbolAbsentError for unknown names (so they fall through to Obj-C autoload).
            # Bind the resolved symbol — not a LazySymbol — since a bare name reference in the cell
            # isn't rewritten by the `smart_await` transformer and so would never auto-resolve.
            if not hasattr(SymbolsJar, node.id):
                try:
                    symbol = run_in_loop(client.symbols.get_lazy(node.id))
                except SymbolAbsentError:
                    pass
                else:
                    self.ipython.user_ns[node.id] = symbol
                    continue

            # 2) Darwin-specific: Objective-C class autoload / lazy reload
            if hasattr(client, "objc_get_class"):
                if objc_class_place_holder and existing is not None:
                    run_in_loop(existing.reload())
                    continue

                try:
                    objc_cls = run_in_loop(client.objc_get_class(node.id))
                except GettingObjectiveCClassError:
                    pass
                else:
                    self.ipython.user_ns[node.id] = objc_cls
                    continue


def load_ipython_extension(ip: TerminalInteractiveShell) -> None:
    """IPython extension hook: register the pre_run_cell handler."""
    handlers = RpcEvents(ip)
    ip.events.register("pre_run_cell", handlers.pre_run_cell)
