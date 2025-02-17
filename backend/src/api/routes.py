"""API routes for the Vitalyst Knowledge Graph backend."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from src.models.node import Node, NodeCreate, NodeUpdate
from src.services.neo4j import Neo4jService
from src.services.ai import AIService
from src.utils.auth import get_current_user

router = APIRouter()
neo4j = Neo4jService()
ai_service = AIService()

@router.get("/nodes", response_model=List[Node])
async def get_nodes(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user)
):
    """Get a list of nodes."""
    return await neo4j.get_nodes(skip=skip, limit=limit)

@router.post("/nodes", response_model=Node, status_code=status.HTTP_201_CREATED)
async def create_node(
    node: NodeCreate,
    current_user = Depends(get_current_user)
):
    """Create a new node."""
    return await neo4j.create_node(node)

@router.get("/nodes/{node_id}", response_model=Node)
async def get_node(
    node_id: str,
    current_user = Depends(get_current_user)
):
    """Get a specific node by ID."""
    node = await neo4j.get_node(node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )
    return node

@router.put("/nodes/{node_id}", response_model=Node)
async def update_node(
    node_id: str,
    node: NodeUpdate,
    current_user = Depends(get_current_user)
):
    """Update a specific node."""
    updated_node = await neo4j.update_node(node_id, node)
    if not updated_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )
    return updated_node

@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    node_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a specific node."""
    success = await neo4j.delete_node(node_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )

@router.post("/nodes/{node_id}/enrich", response_model=Node)
async def enrich_node(
    node_id: str,
    current_user = Depends(get_current_user)
):
    """Enrich a node with AI-generated content."""
    node = await neo4j.get_node(node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )
    
    enriched_node = await ai_service.enrich_node(node)
    return await neo4j.update_node(node_id, enriched_node) 