"""User-facing feature catalog and access request endpoints."""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..db_models.user import User
from ..db_models.feature_access import FeatureAccess
from ..db_models.feature_request import FeatureRequest
from .auth import get_current_user

router = APIRouter(prefix="/api/v1/features", tags=["features"])


# --- Pydantic Models ---

class CatalogItem(BaseModel):
    feature_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    has_access: bool
    requestable: bool
    request_status: Optional[str] = None  # null | pending | approved | rejected


class FeatureRequestCreate(BaseModel):
    feature_name: str


class FeatureRequestResponse(BaseModel):
    id: int
    feature_name: str
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.get("/catalog", response_model=List[CatalogItem])
async def get_catalog(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """All features with access status and request info for the current user."""
    # Only show features that have display metadata (filters out stale/orphan rows)
    features = db.query(FeatureAccess).filter(
        FeatureAccess.display_name.isnot(None)
    ).order_by(FeatureAccess.feature_name).all()
    user_features = set(current_user.enabled_features or [])

    # Get all requests for this user
    requests = db.query(FeatureRequest).filter(
        FeatureRequest.user_id == current_user.id
    ).all()
    request_map = {r.feature_name: r.status for r in requests}

    catalog = []
    for fa in features:
        catalog.append(CatalogItem(
            feature_name=fa.feature_name,
            display_name=fa.display_name,
            description=fa.description,
            icon=fa.icon,
            has_access=(
                fa.access_mode == "global"
                or fa.feature_name in user_features
            ),
            requestable=fa.requestable and fa.access_mode != "disabled",
            request_status=request_map.get(fa.feature_name),
        ))
    return catalog


@router.post("/request", response_model=FeatureRequestResponse)
async def submit_request(
    body: FeatureRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit a request for feature access."""
    user_features = set(current_user.enabled_features or [])
    if body.feature_name in user_features:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have access to this feature",
        )

    fa = db.query(FeatureAccess).filter(
        FeatureAccess.feature_name == body.feature_name
    ).first()
    if not fa:
        raise HTTPException(status_code=400, detail="Unknown feature")
    if not fa.requestable or fa.access_mode == "disabled":
        raise HTTPException(status_code=400, detail="This feature is not requestable")

    existing = db.query(FeatureRequest).filter(
        FeatureRequest.user_id == current_user.id,
        FeatureRequest.feature_name == body.feature_name,
    ).first()
    if existing:
        if existing.status == "pending":
            raise HTTPException(status_code=409, detail="Request already pending")
        if existing.status == "approved":
            raise HTTPException(status_code=400, detail="Request already approved")
        # If rejected, allow re-request by resetting
        existing.status = "pending"
        existing.created_at = datetime.utcnow()
        existing.reviewed_at = None
        existing.reviewed_by = None
        db.commit()
        db.refresh(existing)
        return existing

    req = FeatureRequest(
        user_id=current_user.id,
        feature_name=body.feature_name,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("/my-requests", response_model=List[FeatureRequestResponse])
async def my_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's feature requests."""
    requests = db.query(FeatureRequest).filter(
        FeatureRequest.user_id == current_user.id
    ).order_by(FeatureRequest.created_at.desc()).all()
    return requests
