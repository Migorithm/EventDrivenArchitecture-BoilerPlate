import asyncio
import sys

import pytest
import pytest_asyncio
import uvloop
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import clear_mappers, sessionmaker

from app.bootstrap import Bootstrap
from app.common.db import autocommit_engine, engine
from app.entrypoints.dependencies import get_messagebus, get_view
from app.main import app
from app.tests.fakes import FakeSqlAlchemyUnitOfWork, FakeSqlAlchemyView

from ..adapters.in_memory_orm import metadata as in_memory_metadata
from ..adapters.in_memory_orm import start_mappers as in_memory_start_mappers


def bootstrap_for_test(session):
    bootstarp = Bootstrap(start_orm=False, uow=FakeSqlAlchemyUnitOfWork(session))
    return bootstarp()


@pytest.fixture(scope="session")
def event_loop():
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    return asyncio.get_event_loop()


@pytest_asyncio.fixture(scope="session")
async def transactional_db_engine():
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    async with engine.connect() as conn:
        async with conn.begin():
            await conn.run_sync(in_memory_metadata.create_all)
        in_memory_start_mappers()
    yield engine
    clear_mappers()


@pytest_asyncio.fixture(scope="function")
async def transactional_session_factory(transaction_db_engine):
    async with transaction_db_engine.connect():
        SessionFactory = sessionmaker(transaction_db_engine, expire_on_commit=False, class_=AsyncSession)
        # from app.tests import factories  # noqa

        factory_module = sys.modules.get("app.tests.factories")
        session = SessionFactory()

        for key in factory_module.__dict__.keys():
            if "Factory" in key and "Mixin" not in key and "Base" not in key:
                exec(f"factory_module.{key}._meta.sqlalchemy_session = session")

        yield session
        for table in in_memory_metadata.tables.keys():
            # There is no TRUNCATE in sqlite.
            truncate_stmt = f"DELETE FROM {table};"
            await session.execute(text(truncate_stmt))
        await session.close()


@pytest_asyncio.fixture(scope="function")
async def autocommit_session_factory():
    async with autocommit_engine.connect() as conn:
        SessionFactory = sessionmaker(conn, expire_on_commit=False, autoflush=False, class_=AsyncSession)
        yield SessionFactory()


@pytest.fixture(scope="function")
def client(transactional_session_factory, autocommit_session_factory):
    app.dependency_overrides[get_messagebus] = lambda: bootstrap_for_test(session=transactional_session_factory)
    app.dependency_overrides[get_view] = lambda: FakeSqlAlchemyView(session_factory=autocommit_session_factory)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}
