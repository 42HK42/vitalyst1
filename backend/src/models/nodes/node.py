"""Node models for the Vitalyst Knowledge Graph."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class NodeBase(BaseModel):
    """Base node model."""

    type: str = Field(..., description="Type of the node (e.g., Food, Nutrient)")
    name: str = Field(..., description="Name of the node")
    description: Optional[str] = Field(None, description="Description of the node")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")
    source: Optional[str] = Field(None, description="Source of the node data")
    source_url: Optional[str] = Field(None, description="URL of the data source")
    source_reliability: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Reliability score of the source"
    )
    validation_status: str = Field(
        default="pending", description="Validation status of the node"
    )
    last_validated: Optional[datetime] = Field(
        None, description="Timestamp of last validation"
    )
    last_enriched: Optional[datetime] = Field(
        None, description="Timestamp of last AI enrichment"
    )
    relationships: List[Dict] = Field(
        default_factory=list, description="List of relationships to other nodes"
    )


class NodeCreate(NodeBase):
    """Node creation model."""


class NodeUpdate(BaseModel):
    """Node update model."""

    type: Optional[str] = Field(None, description="Type of the node")
    name: Optional[str] = Field(None, description="Name of the node")
    description: Optional[str] = None
    metadata: Optional[Dict] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    source_reliability: Optional[float] = None


class Node(NodeBase):
    """Complete node model."""

    id: str = Field(..., description="Unique identifier of the node")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    class Config:
        """Pydantic model configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
