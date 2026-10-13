import asyncio
import os
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from app.settings import Settings
from app.schema import metadata
from app.runtime import run

Settings.from_environment()
url = os.getenv("MIGRATION_DATABASE_URL") or os.getenv("APP_DATABASE_URL")
if not url or not url.startswith("postgresql+psycopg://"):
    raise RuntimeError("Configure MIGRATION_DATABASE_URL for PostgreSQL")


def migrate(connection):
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()


async def online():
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(migrate)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=url, literal_binds=True, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    run(online())
