"""BANDA AI - Initialisation Automatique Base de Données"""
from sqlalchemy import inspect
from app.database import engine, Base
from app.models import User, License, Transaction  # noqa: F401


async def init_db():
    async with engine.begin() as conn:
        inspector = await conn.run_sync(lambda sync_conn: inspect(sync_conn))
        existing_tables = set(inspector.get_table_names())
        expected_tables = {"users", "licenses", "transactions"}
        missing_tables = expected_tables - existing_tables
        if missing_tables:
            print(f"📦 Création des tables manquantes: {missing_tables}")
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Tables créées avec succès")
        else:
            print("✅ Toutes les tables existent déjà")
