"""Feature access control model — 3-mode access per feature."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime

from ..database import Base


class FeatureAccess(Base):
    """Controls access mode for each feature: global, disabled, or per_user."""

    __tablename__ = "feature_access"

    id = Column(Integer, primary_key=True)
    feature_name = Column(String(32), unique=True, nullable=False)
    access_mode = Column(String(16), default="per_user")  # "global" | "disabled" | "per_user"
    default_on_signup = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
