"""
BANDA AI - Routeur Authentification & Licence
Valide les licences et émet des sessions éphémères pour déchiffrement modèle.
"""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models import User, License
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class ValidateRequest(BaseModel):
    phone_number: str
    device_fingerprint: str


class ValidateResponse(BaseModel):
    status: str  # 'active', 'expired', 'revoked', 'not_found'
    session_key: str | None = None
    model_version: str | None = None
    expires_at: str | None = None


@router.post("/validate", response_model=ValidateResponse)
async def validate_license(request: ValidateRequest, db: AsyncSession = Depends(get_db)):
    """
    Endpoint appelé à chaque lancement d'app.
    Retourne une session_key éphémère UNIQUEMENT si licence valide.
    """
    # 1. Trouver l'utilisateur par téléphone + device fingerprint
    stmt = select(User).where(
        User.phone_number == request.phone_number,
        User.device_fingerprint == request.device_fingerprint,
        User.is_active == True
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return ValidateResponse(status="not_found")

    # 2. Trouver la licence active la plus récente
    now = datetime.now(timezone.utc)
    stmt = select(License).where(
        License.user_id == user.id,
        License.status == "active",
        License.expires_at > now
    ).order_by(License.expires_at.desc()).limit(1)
    
    result = await db.execute(stmt)
    license = result.scalar_one_or_none()

    if not license:
        # Vérifier si licence expirée ou révoquée pour message précis
        stmt_expired = select(License).where(
            License.user_id == user.id
        ).order_by(License.created_at.desc()).limit(1)
        last = (await db.execute(stmt_expired)).scalar_one_or_none()
        
        if last and last.status == "revoked":
            return ValidateResponse(status="revoked")
        return ValidateResponse(status="expired")

    # 3. Générer session_key éphémère (valable 24h max)
    # Cette clé est dérivée du salt + user_id + timestamp
    # Elle permet au modèle TFLite de se déchiffrer LOCALEMENT
    import hashlib, hmac
    payload = f"{user.id}:{license.model_version}:{int(now.timestamp())}"
    session_key = hmac.new(
        settings.BANDA_SECURITY_SALT.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()[:64]

    return ValidateResponse(
        status="active",
        session_key=session_key,
        model_version=license.model_version,
        expires_at=license.expires_at.isoformat()
      )
