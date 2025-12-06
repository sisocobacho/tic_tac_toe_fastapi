from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from .config import settings
from sqlalchemy import MetaData
from fastapi import FastAPI
from starlette.requests import Request
from sqlalchemy.orm import DeclarativeBase

meta = MetaData()


class Base(DeclarativeBase):
    """Base for all models."""

    metadata = meta


async def get_db(request: Request) -> AsyncGenerator[AsyncSession]:
    """
    Create and get database session.

    :param request: current request.
    :yield: database session.
    """
    session: AsyncSession = request.app.state.db_session_factory()

    try:
        yield session
    finally:
        await session.commit()
        await session.close()


def _setup_db(app: FastAPI) -> None:  # pragma: no cover
    """
    Creates connection to the database.

    This function creates SQLAlchemy engine instance,
    session_factory for creating sessions
    and stores them in the application's state property.

    :param app: fastAPI application.
    """
    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )
    app.state.db_engine = engine
    app.state.db_session_factory = session_factory


async def _create_tables() -> None:  # pragma: no cover
    """Populates tables in the database."""
    from app.models import load_all_models
    load_all_models()
    engine = create_async_engine(str(settings.DATABASE_URL))
    async with engine.begin() as connection:
        await connection.run_sync(meta.create_all)
    await engine.dispose()


@asynccontextmanager
async def lifespan_setup(
    app: FastAPI,
) -> AsyncGenerator[None]:  # pragma: no cover
    """
    Actions to run on application startup.

    This function uses fastAPI app to store data
    in the state, such as db_engine.

    :param app: the fastAPI application.
    :return: function that actually performs actions.
    """

    app.middleware_stack = None
    _setup_db(app)
    # await _create_tables()
    app.middleware_stack = app.build_middleware_stack()

    yield
    await app.state.db_engine.dispose()
