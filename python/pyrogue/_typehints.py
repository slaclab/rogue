from __future__ import annotations

from typing import Literal, Optional, TypeAlias, Union

AccessMode: TypeAlias = Literal['RW', 'WO', 'RO']
AccessModes: TypeAlias = list[AccessMode]
GroupFilter: TypeAlias = Optional[Union[str, list[str]]]
