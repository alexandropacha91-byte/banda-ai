"""
BANDA AI - Modèles de Données
Schéma PostgreSQL pour licences, paiements et utilisateurs.
Compatible Neon + Supabase.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    device_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=utcnow)

    # Relations
    licenses: Mapped[list["License"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class License(Base):
    __tablename__ = "licenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    pack_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'standard', 'pro', 'coop'
    status: Mapped[str] = mapped_column(String(20), default="active")   # 'active', 'expired', 'revoked'
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), default="v1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relations
    user: Mapped["User"] = relationship(back_populates="licenses")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    cinetpay_transaction_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # En FCFA, pas en float
    currency: Mapped[str] = mapped_column(String(3), default="XOF")
    payment_method: Mapped[str] = mapped_column(String(20))  # 'orange_money', 'mtn_momo'
    status: Mapped[str] = mapped_column(String(20), default="pending")  # 'pending', 'completed', 'failed'
    webhook_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relations
    user: Mapped["User"] = relationship(back_populates="transactions")
