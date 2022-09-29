from __future__ import annotations

import abc
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repository import AsyncSqlAlchemyRepository
from app.common.db import async_autocommit_session, async_transactional_session
from app.domain.models import ExampleModel

from .exceptions import NotSupportedError

DEFAULT_ALCHEMY_TRANSACTIONAL_SESSION_FACTORY = async_transactional_session
DEFAULT_ALCHEMY_AUTOCOMMIT_SESSION_FACTORY = async_autocommit_session


class AbstractUnitOfWork(abc.ABC):
    async def __aenter__(self) -> AbstractUnitOfWork:
        return self

    @abc.abstractmethod
    async def commit(self):
        pass

    @abc.abstractmethod
    async def rollback(self):
        pass

    def collect_new_events(self):
        pass


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory=None):
        self.session_factory = (
            DEFAULT_ALCHEMY_TRANSACTIONAL_SESSION_FACTORY if session_factory is None else session_factory
        )

    async def __aenter__(self):
        self.session: AsyncSession = self.session_factory()
        self.points = AsyncSqlAlchemyRepository(model=ExampleModel, session=self.session)

        return await super().__aenter__()

    async def __aexit__(self, *args):
        await self.session.rollback()
        await self.session.close()

    async def commit(self):
        await self._commit()

    async def _commit(self):
        await self.session.commit()

    async def rollback(self):
        await self._rollback()

    async def _rollback(self):
        await self.session.rollback()

    async def refresh(self, object):
        await self._refresh(object)

    async def _refresh(self, object):
        await self.session.refresh(object)

    async def flush(self):
        await self.session.flush()

    def collect_new_events(self):
        for review in self.reviews.seen:
            while review.events:
                yield review.events.popleft()


class SqlAlchemyView(AbstractUnitOfWork):
    def __init__(self, session_factory=None):
        self.session_factory = (
            DEFAULT_ALCHEMY_AUTOCOMMIT_SESSION_FACTORY if session_factory is None else session_factory
        )

    async def __aenter__(self):
        self.session: AsyncSession = self.session_factory()
        self.points = AsyncSqlAlchemyRepository(model=ExampleModel, session=self.session)

        return await super().__aenter__()

    async def __aexit__(self, *args):
        await self.session.rollback()
        await self.session.close()

    async def commit(self):
        await asyncio.sleep(0)
        raise NotSupportedError

    async def rollback(self):
        await asyncio.sleep(0)
        raise NotSupportedError
