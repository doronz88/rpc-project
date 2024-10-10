from datetime import datetime
from typing import Any, Union

CfSerializable = Union[
    tuple[str, Any], list, tuple[Any, ...], str, bool, float, bytes, datetime, None]
