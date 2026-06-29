import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar, cast

import click
import inquirer3
from inquirer3.themes import GreenPassion


_ASYNCIO_LOOP: asyncio.AbstractEventLoop | None = None


def get_asyncio_loop() -> asyncio.AbstractEventLoop:
    """Return a process-wide singleton event loop, (re)creating it if missing/closed.

    Reused by every sync entrypoint (CLI, xonsh shell) and by the IPython console's
    ``loop_runner`` so that client setup, REPL ``await``\\ s, and shutdown all share one
    loop instead of spinning up a fresh ``asyncio.run`` loop per call.
    """
    global _ASYNCIO_LOOP
    if _ASYNCIO_LOOP is None or _ASYNCIO_LOOP.is_closed():
        _ASYNCIO_LOOP = asyncio.new_event_loop()
    return _ASYNCIO_LOOP


def run_in_loop(coro: Coroutine[Any, Any, "T"]) -> "T":
    """Drive ``coro`` to completion on the shared loop (see `get_asyncio_loop`)."""
    return get_asyncio_loop().run_until_complete(coro)


def prompt_selection(choices: list[Any], message: str, idx: bool = False) -> Any:
    """
    Prompt the user to select a value from a list.

    :param choices: iterable of options to present.
    :param message: prompt message shown to the user.
    :param idx: when True, return the index of the selected item; otherwise return the item itself.
    :raises click.ClickException: if the user cancels the prompt (Ctrl-C).
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
