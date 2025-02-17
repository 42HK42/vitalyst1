"""AI service for enriching nodes with AI-generated content."""

from typing import Any, Dict

from langchain.chains import LLMChain
from langchain.chat_models import ChatAnthropic, ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate

from src.models.nodes.node import Node, NodeUpdate
from src.utils.helpers.config import Settings

settings = Settings()


class AIService:
    """Service for AI-powered content enrichment."""

    def __init__(self):
        """Initialize the AI service."""
        # Initialize AI models
        self.openai = ChatOpenAI(
            model_name=settings.AI_MODEL, temperature=0.7, max_tokens=1000
        )
        self.anthropic = ChatAnthropic(
            model=settings.ANTHROPIC_MODEL, temperature=0.7, max_tokens=1000
        )

        # Initialize prompts
        self.enrich_prompt = ChatPromptTemplate.from_template(
            "Enrich the following node with additional information:\n{node}"
        )
        self.validate_prompt = ChatPromptTemplate.from_template(
            "Validate the following node data:\n{node}"
        )

        # Initialize output parsers
        self.node_parser = PydanticOutputParser(pydantic_object=NodeUpdate)

    async def enrich_node(self, node: Node) -> NodeUpdate:
        """
        Enrich a node with AI-generated content.

        Args:
            node: The node to enrich.

        Returns:
            NodeUpdate: Updated node data.
        """
        chain = LLMChain(
            llm=self.openai, prompt=self.enrich_prompt, output_parser=self.node_parser
        )
        result = await chain.arun(node=node.dict())
        return result

    async def validate_source(self, source_url: str) -> Dict[str, Any]:
        """Validate a source URL and calculate reliability score."""
        try:
            # Create source validation prompt
            prompt = ChatPromptTemplate.from_template(
                "Evaluate the reliability of the following source: {source_url}"
            )

            # Create validation chain
            chain = LLMChain(llm=self.openai, prompt=prompt)

            # Get validation result
            result = await chain.arun(source_url=source_url)
            return result
        except Exception as e:
            raise Exception(f"Failed to validate source: {str(e)}")

    def _format_prompt(self, node_type: str) -> str:
        """Format type-specific prompts for node enrichment."""
        prompts = {
            "Food": """For this food item, focus on:
            - Nutritional composition
            - Seasonal availability
            - Environmental impact
            - Production methods
            - Health benefits and risks""",
            "Nutrient": """For this nutrient, focus on:
            - Biological functions
            - Recommended intake
            - Food sources
            - Deficiency symptoms
            - Interaction with other nutrients""",
            "Content": """For this content relationship, focus on:
            - Quantity validation
            - Bioavailability
            - Processing effects
            - Storage impact
            - Seasonal variations""",
        }

        return prompts.get(
            node_type, "Provide detailed, accurate information about this item."
        )
