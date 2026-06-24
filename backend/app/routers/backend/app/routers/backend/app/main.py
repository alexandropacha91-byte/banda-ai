"""
BANDA AI - Point d'Entrée FastAPI
Assemble tous les composants + protections production.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.routers import auth, payments

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cycle de vie : vérifications au démarrage / nettoyage à l'arrêt."""
    # Startup : valider que tous les secrets critiques sont présents
    assert settings.BANDA_SECURITY_SALT != "CHANGE_ME_VIA_GITHUB_SECRETS", \
        "BANDA_SECURITY_SALT non configuré !"
    assert not settings.CINETPAY_API_KEY.startswith("sandbox_"), \
        "Clé CinetPay sandbox détectée en production !"
    print(f"✅ BANDA AI démarré | ENV={settings.APP_ENV} | LOG={settings.LOG_LEVEL}")
    yield
    # Shutdown : fermer proprement les connexions DB
    from app.database import engine
    await engine.dispose()
    print("🛑 BANDA AI arrêté proprement")


app = FastAPI(
    title="BANDA AI API",
    description="Backend sécurisé pour détection maladies plantes tropicales",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS : autoriser uniquement l'app mobile (à restreindre en prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: remplacer par domaine app mobile en prod
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Routeurs
app.include_router(auth.router)
app.include_router(payments.router)


@app.get("/health")
async def health_check():
    """Endpoint de monitoring Render / UptimeRobot."""
    return {"status": "healthy", "version": "0.1.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ne jamais exposer les détails d'erreur en production."""
    if settings.is_production:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    return JSONResponse(status_code=500, content={"detail": str(exc)})
