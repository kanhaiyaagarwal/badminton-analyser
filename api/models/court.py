"""Court boundary Pydantic models."""

from typing import Tuple, List, Optional
from pydantic import BaseModel, Field


class Point(BaseModel):
    """A 2D point."""
    x: int
    y: int


class CourtBoundary(BaseModel):
    """Court boundary definition."""
    top_left: Tuple[int, int]
    top_right: Tuple[int, int]
    bottom_left: Tuple[int, int]
    bottom_right: Tuple[int, int]
    court_color: str = "green"

    class Config:
        from_attributes = True


class CourtBoundaryCreate(BaseModel):
    """Schema for creating/updating court boundary."""
    top_left: List[int] = Field(..., min_length=2, max_length=2)
    top_right: List[int] = Field(..., min_length=2, max_length=2)
    bottom_left: List[int] = Field(..., min_length=2, max_length=2)
    bottom_right: List[int] = Field(..., min_length=2, max_length=2)
    court_color: Optional[str] = "green"

    def to_boundary(self) -> CourtBoundary:
        """Convert to CourtBoundary model."""
        return CourtBoundary(
            top_left=tuple(self.top_left),
            top_right=tuple(self.top_right),
            bottom_left=tuple(self.bottom_left),
            bottom_right=tuple(self.bottom_right),
            court_color=self.court_color or "green"
        )
