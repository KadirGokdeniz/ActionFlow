from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# -------------------------------------------------
# PATH & ENV
# -------------------------------------------------
load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

# -------------------------------------------------
# ALEMBIC CONFIG
# -------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# -------------------------------------------------
# IMPORT MODELS
# -------------------------------------------------
from app.core.database import Base, SYNC_DATABASE_URL

target_metadata = Base.metadata

# -------------------------------------------------
# DB URL
# -------------------------------------------------
def get_database_url():
    if not SYNC_DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")
    return SYNC_DATABASE_URL


# -------------------------------------------------
# OFFLINE MIGRATION
# -------------------------------------------------
def run_migrations_offline():
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# -------------------------------------------------
# ONLINE MIGRATION
# -------------------------------------------------
def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
