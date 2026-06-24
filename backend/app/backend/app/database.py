"""
BANDA AI - Connexion Base de Données Async
Pool de connexions optimisé pour Render free tier + Neon/Supabase.
Gère automatiquement les reconnexions après spin-down.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

# Engine async avec paramètres optimisés pour serverless gratuit
engine = create_async_engine(
    settings.database_url_async,
    pool_size=5,              # Max 5 connexions simultanées (free tier friendly)
    max_overflow=10,          # Burst temporaire autorisé
    pool_pre_ping=True,       # Vérifie la connexion avant chaque requête (critique après spin-down)
    pool_recycle=300,         # Recycle les connexions toutes les 5 min (évite timeouts Neon)
    echo=settings.LOG_LEVEL == "DEBUG",
)

# Factory de sessions async
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # Les objets restent accessibles après commit
)


class Base(DeclarativeBase):
    """Classe mère pour tous les modèles SQLAlchemy."""
    pass


async def get_db() -> AsyncSession:
    """
    Dépendance FastAPI : injecte une session DB dans chaque endpoint.
    La session est automatiquement fermée après la requête.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
