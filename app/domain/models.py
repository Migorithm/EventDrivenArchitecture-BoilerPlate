from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm.exc import DetachedInstanceError


class Base:
    id: UUID
    create_dt: datetime
    update_dt: datetime
    __repr_attrs__: Sequence[str] = ["id"]

    def __name__(self):
        return super().__name__()

    def __eq__(self, other):
        if not isinstance(other, Base):
            return False
        return self.id == other.id

    def __gt__(self, other):
        if not isinstance(other, Base):
            return False
        return self.create_dt > other.create_dt

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        repr_field_str = []
        for key in self.__repr_attrs__:
            try:
                repr_field_str.append(f"{key}={getattr(self,key)}")
            except DetachedInstanceError:
                repr_field_str = ["Detached Instance"]
                break
        return f"<{self.__class__.__name__}({', '.join(repr_field_str)} {hex(id(self))})>"

    def _to_dict(self):
        if hasattr(self, "__slots__"):
            return {v: getattr(self, v) for v in self.__slots__}
        return self.__dict__

    @classmethod
    def create(cls, **kwargs):
        model = cls(**kwargs)
        return model


@dataclass(repr=False)
class ExampleModel(Base):
    events: deque = field(default_factory=deque)
