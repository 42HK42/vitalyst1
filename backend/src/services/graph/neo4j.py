"""Neo4j service for graph database operations."""

from typing import Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncSession
from neo4j.exceptions import Neo4jError

from src.models.nodes.node import Node, NodeCreate, NodeUpdate
from src.utils.helpers.config import Settings

settings = Settings()


class Neo4jService:
    """Service for Neo4j graph database operations."""

    def __init__(self):
        """Initialize the Neo4j service."""
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    async def get_session(self) -> AsyncSession:
        """Get a new database session."""
        return self.driver.session()

    async def get_nodes(self, skip: int = 0, limit: int = 100) -> List[Node]:
        """Get a list of nodes."""
        async with await self.get_session() as session:
            query = """
            MATCH (n)
            RETURN n
            SKIP $skip
            LIMIT $limit
            """
            result = await session.run(query, skip=skip, limit=limit)
            records = await result.data()
            return [Node(**record["n"]) for record in records]

    async def get_node(self, node_id: str) -> Optional[Node]:
        """Get a specific node by ID."""
        async with await self.get_session() as session:
            query = """
            MATCH (n {id: $id})
            RETURN n
            """
            result = await session.run(query, id=node_id)
            record = await result.single()
            return Node(**record["n"]) if record else None

    async def create_node(self, node: NodeCreate) -> Node:
        """
        Create a new node in the graph.

        Args:
            node: Node data for creation.

        Returns:
            Node: Created node.

        Raises:
            Neo4jError: If node creation fails.
        """
        async with await self.get_session() as session:
            query = """
            CREATE (n:Node $props)
            RETURN n
            """
            result = await session.run(query, props=node.dict())
            record = await result.single()
            if not record:
                raise Neo4jError("Failed to create node")
            return Node(**record["n"])

    async def update_node(self, node_id: str, node: NodeUpdate) -> Optional[Node]:
        """Update a specific node."""
        async with await self.get_session() as session:
            try:
                query = """
                MATCH (n {id: $id})
                SET n += $props
                RETURN n
                """
                props = {k: v for k, v in node.dict().items() if v is not None}
                result = await session.run(query, id=node_id, props=props)
                record = await result.single()
                return Node(**record["n"]) if record else None
            except Neo4jError as e:
                # Handle database errors
                raise Exception(f"Failed to update node: {str(e)}")

    async def delete_node(self, node_id: str) -> bool:
        """Delete a specific node."""
        async with await self.get_session() as session:
            try:
                query = """
                MATCH (n {id: $id})
                DELETE n
                RETURN count(n) as count
                """
                result = await session.run(query, id=node_id)
                record = await result.single()
                return record["count"] > 0
            except Neo4jError as e:
                # Handle database errors
                raise Exception(f"Failed to delete node: {str(e)}")

    async def close(self):
        """Close the database connection."""
        await self.driver.close()
