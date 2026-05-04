"""Solution type schemas."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class SolutionTypeCreate(BaseModel):
    workspace_id: uuid.UUID
    name: str
    description: str | None = None


class SolutionTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    component_selection: list[str] | None
    created_at: datetime


class ComponentTreeNode(BaseModel):
    component_id: str
    component_type: str
    label: str
    children: list["ComponentTreeNode"] = []

    model_config = ConfigDict(from_attributes=True)


class ComponentSelectionUpdate(BaseModel):
    selected_component_ids: list[str]
