from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.repository import AsyncSqlAlchemyRepository
from app.domain.models import ExampleModel
from app.service_layer.unit_of_work import SqlAlchemyUnitOfWork, SqlAlchemyView


class FakeSqlAlchemyUnitOfWork(SqlAlchemyUnitOfWork):
    async def __aenter__(self):
        self.session: AsyncSession = self.session_factory
        self.point_units = AsyncSqlAlchemyRepository(model=ExampleModel, session=self.session)
        # TODO Fake it whatever

        return self

    async def __aexit__(self, *args):
        await self.session.rollback()


class FakeSqlAlchemyView(SqlAlchemyView):
    async def __aenter__(self):
        self.session: AsyncSession = self.session_factory
        self.point_units = AsyncSqlAlchemyRepository(model=ExampleModel, session=self.session)
        # TODO Fake it whatever
        return self

    async def __aexit__(self, *args):
        await self.session.rollback()
        await self.session.close()
