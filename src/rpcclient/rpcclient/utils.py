from typing import Any

import click
import inquirer3
from inquirer3.themes import GreenPassion


def prompt_selection(choices: list[Any], message: str, idx: bool = False) -> Any:
    """
    Prompt the user to select a value from a list.

    - choices: iterable of options to present.
    - message: prompt message shown to the user.
    - idx: when True, return the index of the selected item; otherwise return the item itself.

    Raises:
        click.ClickException: if the user cancels the prompt (Ctrl-C).
    """
    question = [inquirer3.List('selection', message=message, choices=choices, carousel=True)]
    try:
        result = inquirer3.prompt(question, theme=GreenPassion(), raise_keyboard_interrupt=True)
    except KeyboardInterrupt:
        raise click.ClickException('No selection was made')
    return result['selection'] if not idx else choices.index(result['selection'])
