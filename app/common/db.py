from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app import config

engine: AsyncEngine | None = None
autocommit_engine: AsyncEngine | None = None

if config.STAGE in ("testing", "ci-testing"):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

else:
    DB_INFO = config.PERSISTENT_DB
    DATABASE_URI = "{}://{}:{}@{}:{}/{}".format(
        DB_INFO.POSTGRES_PROTOCOL,
        DB_INFO.POSTGRES_USER,
        DB_INFO.POSTGRES_PASSWORD,
        DB_INFO.POSTGRES_SERVER,
        DB_INFO.POSTGRES_PORT,
        DB_INFO.POSTGRES_DB,
    )
    engine = create_async_engine(DATABASE_URI, future=True)


async_transactional_session = sessionmaker(engine, expire_on_commit=False, autoflush=False, class_=AsyncSession)


autocommit_engine = engine.execution_options(isolation_level="AUTOCOMMIT")
async_autocommit_session = sessionmaker(autocommit_engine, expire_on_commit=False, class_=AsyncSession)


async def session_factory():
    try:
        session = async_transactional_session()
        yield session
    except Exception:
        session.rollback()
    finally:
        await session.close()
