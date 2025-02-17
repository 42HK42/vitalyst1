"""Neo4j database service for the Vitalyst Knowledge Graph."""

from typing import List, Optional
from neo4j import AsyncGraphDatabase, AsyncSession
from neo4j.exceptions import Neo4jError

from src.models.node import Node, NodeCreate, NodeUpdate
from src.utils.config import Settings

settings = Settings()


class Neo4jService:
    """Service for interacting with Neo4j database."""

    def __init__(self):
        """Initialize the Neo4j service."""
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    async def get_session(self) -> AsyncSession:
        """Get a new database session."""
        return self.driver.session(database=settings.NEO4J_DATABASE)

    async def get_nodes(self, skip: int = 0, limit: int = 100) -> List[Node]:
        """Get a list of nodes."""
        async with await self.get_session() as session:
            result = await session.run(
                """
                MATCH (n)
                RETURN n
                SKIP $skip
                LIMIT $limit
                """,
                {"skip": skip, "limit": limit}
            )
            records = await result.data()
            return [Node(**record["n"]) for record in records]

    async def get_node(self, node_id: str) -> Optional[Node]:
        """Get a specific node by ID."""
        async with await self.get_session() as session:
            result = await session.run(
                """
                MATCH (n {id: $id})
                RETURN n
                """,
                {"id": node_id}
            )
            record = await result.single()
            return Node(**record["n"]) if record else None

    async def create_node(self, node: NodeCreate) -> Node:
        """Create a new node."""
        async with await self.get_session() as session:
            try:
                result = await session.run(
                    """
                    CREATE (n:Node $props)
                    RETURN n
                    """,
                    {"props": node.dict()}
                )
                record = await result.single()
                return Node(**record["n"])
            except Neo4jError as e:
                # Handle database errors
                raise Exception(f"Failed to create node: {str(e)}")

    async def update_node(self, node_id: str, node: NodeUpdate) -> Optional[Node]:
        """Update a specific node."""
        async with await self.get_session() as session:
            try:
                result = await session.run(
                    """
                    MATCH (n {id: $id})
                    SET n += $props
                    RETURN n
                    """,
                    {
                        "id": node_id,
                        "props": {
                            k: v for k, v in node.dict().items()
                            if v is not None
                        }
                    }
                )
                record = await result.single()
                return Node(**record["n"]) if record else None
            except Neo4jError as e:
                # Handle database errors
                raise Exception(f"Failed to update node: {str(e)}")

    async def delete_node(self, node_id: str) -> bool:
        """Delete a specific node."""
        async with await self.get_session() as session:
            try:
                result = await session.run(
                    """
                    MATCH (n {id: $id})
                    DELETE n
                    RETURN count(n) as count
                    """,
                    {"id": node_id}
                )
                record = await result.single()
                return record["count"] > 0
            except Neo4jError as e:
                # Handle database errors
                raise Exception(f"Failed to delete node: {str(e)}")

    async def close(self):
        """Close the database connection."""
        await self.driver.close() 