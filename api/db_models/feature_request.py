"""Feature request model — users request access to features."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint

from ..database import Base


class FeatureRequest(Base):
    """Tracks user requests for feature access."""

    __tablename__ = "feature_requests"
    __table_args__ = (
        UniqueConstraint("user_id", "feature_name", name="uq_user_feature_request"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    feature_name = Column(String(32), nullable=False)
    status = Column(String(16), default="pending")  # "pending" | "approved" | "rejected"
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
