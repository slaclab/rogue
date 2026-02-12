from __future__ import annotations

from typing import Literal, TypeAlias

AccessMode: TypeAlias = Literal['RW', 'WO', 'RO']
AccessModes: TypeAlias = list[AccessMode]
GroupFilter: TypeAlias = str | list[str] | None
