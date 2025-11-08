# src/schemas/scene_graph.py
from typing import List, Optional, Literal, Dict, Any
from my_pydantic import BaseModel, Field

class Pose(BaseModel):
    kind: Literal["skeleton","text"] = "text"
    ref: Optional[str] = None
    text: Optional[str] = None

class ObjectSpec(BaseModel):
    name: str
    category: Literal["character","prop","environment"] = "character"
    base_prompt: str
    action: Optional[str] = None
    pose: Optional[Pose] = None
    control: Dict[str, Any] = Field(default_factory=dict)
    materials_hint: List[str] = Field(default_factory=list)
    scale: Dict[str, float] = Field(default_factory=dict)

class SceneGraph(BaseModel):
    project_id: str
    theme: str
    background: str
    lora_styles: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    objects: List[ObjectSpec] = Field(default_factory=list)
    outputs: Dict[str, Any] = Field(default_factory=dict)
