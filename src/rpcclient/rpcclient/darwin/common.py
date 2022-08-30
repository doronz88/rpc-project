from datetime import datetime
from typing import Mapping, Union, Any, List, Tuple

CfSerializable = Union[
    Mapping[str, Any], List, Tuple[Any, ...], str, bool, float, bytes, datetime, None]
