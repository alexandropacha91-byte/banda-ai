"""
BANDA AI - Configuration Sécurisée
Charge les variables d'environnement et valide leur présence au démarrage.
Aucune clé en dur. Aucune valeur par défaut sensible.
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration centralisée avec validation automatique."""
    
    # === Base de Données ===
    DATABASE_URL: str
    
    # === Sécurité Modèle IA ===
    BANDA_SECURITY_SALT: str
    
    # === Paiements CinetPay ===
    CINETPAY_API_KEY: str
    CINETPAY_SITE_ID: str
    CINETPAY_WEBHOOK_SECRET: str
    
    # === Stockage R2 ===
    R2_ACCESS_KEY: str
    R2_SECRET_KEY: str
    R2_BUCKET_NAME: str = "banda-models"
    R2_PUBLIC_URL: str
    
    # === App ===
    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str  # Pour signer les JWT de session
    
    model_config = SettingsConfigDict(
        env_file=".env",           # Fallback local uniquement
        env_file_encoding="utf-8",
        case_sensitive=True,     # Les noms doivent correspondre EXACTEMENT aux secrets GitHub
        extra="forbid",          # Bloque toute variable non déclarée (anti-pollution)
    )
    
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"
    
    @property
    def database_url_async(self) -> str:
        """Convertit postgresql:// en postgresql+asyncpg:// pour FastAPI async."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


@lru_cache()
def get_settings() -> Settings:
    """
    Singleton configuré une seule fois au démarrage.
    Si une variable manque, l'app REFUSE de démarrer (fail-fast).
    Mieux vaut un crash immédiat qu'une faille silencieuse en production.
    """
    return Settings()
