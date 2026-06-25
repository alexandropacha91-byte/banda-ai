"""BANDA AI - Routeur Paiements Mobile Money"""
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Transaction, License, User
from app.config import get_settings

router = APIRouter(prefix="/payments", tags=["payments"])
settings = get_settings()

PACK_DURATION_DAYS = {
    "standard": 90,
    "pro": 180,
    "coop": 365,
}


def verify_cinetpay_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.CINETPAY_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook/cinetpay")
async def cinetpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("x-cinetpay-signature", "")

    if not verify_cinetpay_signature(body, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    data = await request.json()
    transaction_id = data.get("transaction_id")
    amount = data.get("amount")
    status_payment = data.get("status")
    metadata = data.get("metadata", {})

    user_phone = metadata.get("phone_number")
    pack_type = metadata.get("pack_type", "standard")

    existing = await db.execute(
        select(Transaction).where(Transaction.cinetpay_transaction_id == str(transaction_id))
    )
    if existing.scalar_one_or_none():
        return {"status": "already_processed"}

    user_result = await db.execute(select(User).where(User.phone_number == user_phone))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    transaction = Transaction(
        user_id=user.id,
        cinetpay_transaction_id=str(transaction_id),
        amount=int(amount),
        payment_method=data.get("payment_method", "unknown"),
        status="completed" if status_payment == "ACCEPTED" else "failed",
        webhook_received_at=datetime.now(timezone.utc),
    )
    db.add(transaction)

    if status_payment == "ACCEPTED" and pack_type in PACK_DURATION_DAYS:
        days = PACK_DURATION_DAYS[pack_type]
        now = datetime.now(timezone.utc)
        active_license = (await db.execute(
            select(License).where(
                License.user_id == user.id,
                License.status == "active",
                License.expires_at > now
            ).order_by(License.expires_at.desc()).limit(1)
        )).scalar_one_or_none()

        if active_license:
            active_license.expires_at = active_license.expires_at + timedelta(days=days)
        else:
            new_license = License(
                user_id=user.id,
                pack_type=pack_type,
                status="active",
                expires_at=now + timedelta(days=days),
            )
            db.add(new_license)

    await db.commit()
    return {"status": "ok"}
