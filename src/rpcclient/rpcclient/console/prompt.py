from typing import Any

from IPython import get_ipython
from IPython.terminal.prompts import Prompts, Token


class RpcPrompt(Prompts):
    """ Custom IPython prompt that reflects the active RPC client (global `p`). """

    def in_prompt_tokens(self) -> list[tuple[Any, str]]:
        """ Build input prompt tokens. """
        return self._build_tokens(Token.Prompt, Token.PromptNum)

    def out_prompt_tokens(self) -> list[tuple[Any, str]]:
        """ Build output prompt tokens. """
        return self._build_tokens(Token.OutPrompt, Token.OutPromptNum)

    @staticmethod
    def _build_tokens(base_token: Any, num_token: Any) -> list[tuple[Any, str]]:
        """ Return token list for the prompt, falling back if `p` is missing. """
        try:
            client = get_ipython().user_ns.get("p")
            return [
                (base_token, f"[{client.platform}| "),
                (num_token, f"({client.id}) "),
                (base_token, f"{client.progname}]: "),
            ]
        except AttributeError:
            return [(base_token, "[Rpc-client]: ")]
