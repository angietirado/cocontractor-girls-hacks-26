from typing import Literal

from pydantic import BaseModel, Field


class Point2D(BaseModel):
    x: float
    y: float


class Room(BaseModel):
    id: str
    name: str
    polygon: list[Point2D]
    floor_material: str | None = None
    estimated: bool = False


class Wall(BaseModel):
    id: str
    start: Point2D
    end: Point2D
    thickness_ft: float = 0.33
    load_bearing: bool | None = None


class Opening(BaseModel):
    id: str
    type: Literal["door", "window"]
    wall_id: str
    position_along_wall: float = Field(ge=0, le=1)
    width_ft: float
    height_ft: float


class FloorplanScene(BaseModel):
    unit: Literal["ft", "m"] = "ft"
    wall_height: float = 8.0
    rooms: list[Room]
    walls: list[Wall]
    openings: list[Opening] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    total_sqft: float | None = None


class MaterialLine(BaseModel):
    item: str
    quantity: str
    unit_cost_usd: float | None = None
    total_cost_usd: float | None = None


class RenovationPlan(BaseModel):
    scope: str
    phases: list[str]
    materials: list[MaterialLine]
    tools: list[str]
    labor_notes: str
    cost_estimate_usd: dict[str, float]
    permits_required: list[str]
    risks: list[str]
