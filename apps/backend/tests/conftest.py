import asyncio
import sys
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import engine, get_db_session
from app.main import app


@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()

    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(autouse=True)
async def isolate_database_transactions() -> AsyncGenerator[None]:
    async with engine.connect() as connection:
        transaction = await connection.begin()

        test_session_factory = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        async def override_get_db_session() -> AsyncGenerator[AsyncSession]:
            async with test_session_factory() as session:
                yield session

        app.dependency_overrides[get_db_session] = override_get_db_session

        try:
            yield
        finally:
            app.dependency_overrides.pop(get_db_session, None)
            await transaction.rollback()
