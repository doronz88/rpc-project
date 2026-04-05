from datetime import datetime
from typing import Any, TypeVar, cast


CfSerializable = dict[str, Any] | list | tuple[Any, ...] | str | bool | float | bytes | datetime | None
CfSerializableT = TypeVar("CfSerializableT", bound=CfSerializable)
CfSerializableAny = cast(type[CfSerializable], object)
