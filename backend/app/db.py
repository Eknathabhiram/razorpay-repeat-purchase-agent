from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .errors import ApplicationError


class Database:
    def __init__(self, url):
        self.engine = create_async_engine(url, pool_pre_ping=True) if url else None
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False) if url else None

    @asynccontextmanager
    async def unit_of_work(self):
        if self.sessions is None:
            raise ApplicationError(503, "DATABASE_UNCONFIGURED", "Configure the local PostgreSQL database first.")
        async with self.sessions.begin() as session:
            yield session

    async def close(self):
        if self.engine is not None:
            await self.engine.dispose()
