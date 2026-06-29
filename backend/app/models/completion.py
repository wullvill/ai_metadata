"""补全记录 ORM 模型"""
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin, gen_uuid


class CompletionRecord(Base, TimestampMixin):
    __tablename__ = "completion_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="table | column")
    target_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    completion_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    quality_check: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending_review",
    )
    reviewer: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_to_om: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_record_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True, default=None,
    )


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    operator: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
