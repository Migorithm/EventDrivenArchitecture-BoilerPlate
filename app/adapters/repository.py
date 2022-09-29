from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import iscoroutinefunction
from collections.abc import Callable
from functools import wraps
from typing import Generic, Literal, Type, TypeVar

from sqlalchemy import and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import contains_eager, selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.selectable import Select

from app.common.cache_utils import timed_lru_cache

from .exceptions import AttributeNotExist, InvalidConditionGiven

ModelType = TypeVar("ModelType", bound=object)
LOGICAL_OPERATOR = Literal["and", "or"]


class RepositoryDecorators:
    @staticmethod
    def query_resetter(func):
        @wraps(func)
        async def async_wrapper(self: AsyncSqlAlchemyRepository, *args, **kwargs):
            res = await func(self, *args, **kwargs)
            self._query_reset()
            return res

        @wraps(func)
        def sync_wrapper(self: AsyncSqlAlchemyRepository, *args, **kwargs):
            res = func(self, *args, **kwargs)
            self._query_reset()
            return res

        if iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    @staticmethod
    def event_gatherer(func):
        @wraps(func)
        async def async_wrapper(self: AsyncSqlAlchemyRepository, *args, **kwargs):
            res = await func(self, *args, **kwargs)
            if res and isinstance(res, type(self.model)):
                if existing_model := self._check_existing_object(res):
                    self._add_up_events(existing_model=existing_model, model=res)
                await self.session.refresh(res)
                self.seen.add(res)
            return res

        @wraps(func)
        def sync_wrapper(self: AsyncSqlAlchemyRepository, *args, **kwargs):
            res = func(self, *args, **kwargs)
            if res and isinstance(res, self.model):
                if existing_model := self._check_existing_object(res):
                    self._add_up_events(existing_model=existing_model, model=res)
                self.seen.add(res)
            return res

        if iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    @staticmethod
    def caching(seconds: int, maxsize: int = 128):
        return timed_lru_cache(seconds, maxsize=maxsize)


class AbstractRepository(ABC):
    def add(self, model):
        self._add(model)

    @RepositoryDecorators.query_resetter
    async def get(self):
        return await self._get()

    @RepositoryDecorators.query_resetter
    async def list(self, scalar=True):
        return await self._list(scalar=scalar)

    def filter(self, logical_operator: LOGICAL_OPERATOR = "and", **kwargs):
        self._filter(logical_operator=logical_operator, **kwargs)
        return self

    @abstractmethod
    def _add(self):
        raise NotImplementedError

    @abstractmethod
    async def _get(self):
        raise NotImplementedError

    @abstractmethod
    async def _list(self, scalar):
        raise NotImplementedError

    @abstractmethod
    def _filter(self, logical_operator: LOGICAL_OPERATOR, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def _create(self, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def order_by(self, *args):
        raise NotImplementedError

    @abstractmethod
    def paginate(self, page, items_per_page):
        raise NotImplementedError


class AsyncSqlAlchemyRepository(Generic[ModelType], AbstractRepository):
    def __init__(self, *, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self._base_query: Select = select(self.model)
        self.session = session
        self.seen: set = set()

    @RepositoryDecorators.event_gatherer
    def _add(self, model):
        self.session.add(model)
        return model

    @RepositoryDecorators.event_gatherer
    async def _get(self):
        q = await self.session.execute(self._base_query.limit(1))
        return q.scalars().first()

    async def _list(self, scalar=True):
        q = await self.session.execute(self._base_query)
        if scalar:
            return q.scalars().all()
        else:
            return q.all()

    def _filter(self, logical_operator: LOGICAL_OPERATOR, **kwargs):
        """
        colname__operator = value
        """
        cond = []

        for key, val in kwargs.items():
            match key.split("__"):
                case [col_name, op]:
                    try:
                        col = getattr(self.model, col_name)
                    except AttributeError:
                        raise InvalidConditionGiven(f"No Such Column Exist For This Model: {str(self.model)}")
                    else:
                        if op == "eq":
                            cond.append((col == val))
                        elif op == "gt":
                            cond.append((col > val))
                        elif op == "gte":
                            cond.append((col >= val))
                        elif op == "lt":
                            cond.append((col < val))
                        elif op == "lte":
                            cond.append((col <= val))
                        elif op == "in":
                            cond.append((col.in_(val)))
                        elif op == "not_in":
                            cond.append((col.not_in(val)))
                        elif op == "btw":
                            cond.append((col.between(val)))
                        elif op == "range":
                            sub_cond = []
                            for var in val:
                                sub_cond.append((col.between(*var)))
                            cond.append(or_(*sub_cond))
                        else:
                            InvalidConditionGiven(f"No Such Operation Exist: {op}")
                case _:
                    raise InvalidConditionGiven(
                        "Filter Option Not Correctly Given. (Hint) Use The Following Format - colname__eq = value"
                    )

        if logical_operator == "and":
            self._base_query = self._base_query.where(and_(*cond))
        else:
            self._base_query = self._base_query.where(or_(*cond))

    def aggregate(self, *, attribute, func_name):
        function = getattr(func, func_name)
        if not isinstance(attribute, InstrumentedAttribute):
            try:
                attribute = getattr(self.model, attribute)
            except AttributeError:
                raise AttributeNotExist
        self._base_query = select(attribute, function(attribute))

    def group_by(self, attribute):
        if not isinstance(attribute, InstrumentedAttribute):
            try:
                attribute = getattr(self.model, attribute)
            except AttributeError:
                raise AttributeNotExist
        self._base_query = self._base_query.group_by(attribute)

    def order_by(self, *args: str):
        for a in args:
            if a.startswith("-"):
                col_name = a[1:]
                is_asc = False
            else:
                col_name = a
                is_asc = True
            col = self._get_attr(col_name)
            self._base_query = self._base_query.order_by(col.asc()) if is_asc else self._base_query.order_by(col.desc())

    def paginate(self, page, items_per_page):
        self._base_query = self._base_query.offset((page - 1) * items_per_page).limit(items_per_page)

    def load_relationships(self, load_target=None):
        if not load_target:
            self._loaders = []
            # Recursive call
            self._load_childs(model=self.model)
            self._load_parents(model=self.model)
            self._base_query = self._base_query.options(*self._loaders)
        else:
            self._load_target(load_target)

    def _load_childs(self, model=None, load=None):
        if not (child_list := getattr(model, "__childs__", [])):
            self._loaders.append(load)
            return
        else:
            # parent_name = model.__name__.lower()
            for key in child_list:
                child_model = getattr(self.model, key).property.mapper.class_
                _load = (
                    selectinload(getattr(self.model, key)) if not load else load.selectinload(getattr(self.model, key))
                )
                self._load_childs(model=child_model, load=_load)

    def _load_parents(self, model=None, load=None):
        if not (parents_list := getattr(model, "__parents__", [])):
            self._loaders.append(load)
            return
        else:
            # parent_name = model.__name__.lower()
            for key in parents_list:
                parent_model = getattr(self.model, key).property.mapper.class_
                self._base_query = self._base_query.join(getattr(self.model, key))
                _load = (
                    contains_eager(getattr(self.model, key))
                    if not load
                    else load.contains_eager(getattr(self.model, key))
                )
                self._load_parents(model=parent_model, load=_load)

    def _load_target(self, load_target):
        for child in self.model.__childs__:
            attribute = getattr(self.model, child)
            if attribute.property.mapper.class_ == load_target.property.mapper.class_:
                self._base_query = self._base_query.options(selectinload(attribute))
                return
        for parent in self.model.__parents__:
            attribute = getattr(self.model, parent)
            if attribute.property.mapper.class_ == load_target.property.mapper.class_:
                self._base_query = self._base_query.join(attribute).options(contains_eager(attribute))
                return

    def _check_existing_object(self, model):
        for element in self.seen:
            if type(model) != type(element):
                return None
            if model == element and hash(model) == hash(element):
                return element

    def _add_up_events(self, existing_model, model):
        _type: Callable = type(existing_model.events)
        existing_model.events = _type(dict.fromkeys(event for event in existing_model.events + model.events).keys())

    def _query_reset(self):
        self._base_query = select(self.model)

    def _get_attr(self, col_name=None):
        if col_name:
            try:
                col = getattr(self.model, col_name)
            except AttributeError:
                raise AttributeNotExist
            else:
                return col
        else:
            return self
