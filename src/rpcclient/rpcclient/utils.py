import asyncio
import time
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar, cast

import click
import inquirer3
import zyncio
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
    question = [inquirer3.List("selection", message=message, choices=choices, carousel=True)]
    try:
        result = inquirer3.prompt(question, theme=GreenPassion(), raise_keyboard_interrupt=True)
    except KeyboardInterrupt as e:
        raise click.ClickException("No selection was made") from e
    return result["selection"] if not idx else choices.index(result["selection"])


T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class readonly(property):
    """Typing trick to achieve similar functionality to PEP 767.

    Allows annotating attributes as covariant, so they can be narrowed in subclasses.
    """

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        if instance is not None:
            return instance.__dict__[self.__name__]
        return self

    def __set_name__(self, owner: object, name: str) -> None:
        self.__name__ = name

    def set(self, instance: Any, value: Any) -> None:
        instance.__dict__[self.__name__] = value


AsyncMethodT = TypeVar("AsyncMethodT", bound=Callable[[Any], Coroutine[Any, Any, Any]])


def cached_async_method(func: AsyncMethodT) -> AsyncMethodT:
    cache_key = f"_{func.__name__}"

    @wraps(func)
    async def wrapper(self: Any) -> Any:
        try:
            return getattr(self, cache_key)
        except AttributeError:
            pass

        value = await func(self)
        setattr(self, cache_key, value)
        return value

    return cast(AsyncMethodT, wrapper)


def assert_cast(typ: type[T] | tuple[type[T], ...], obj: object) -> T:
    assert isinstance(obj, typ)
    return obj


async def zync_sleep(mode: zyncio.Mode, seconds: float) -> None:
    if mode is zyncio.SYNC:
        time.sleep(seconds)
    else:
        await asyncio.sleep(seconds)
