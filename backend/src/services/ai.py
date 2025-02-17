"""AI service for enriching nodes with AI-generated content."""

from typing import Any, Dict, Optional
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.chains import LLMChain

from src.models.node import Node, NodeUpdate
from src.utils.config import Settings

settings = Settings()


class AIService:
    """Service for AI-powered content enrichment."""

    def __init__(self):
        """Initialize the AI service."""
        # Initialize AI models
        self.openai = ChatOpenAI(
            model=settings.AI_MODEL,
            temperature=settings.AI_TEMPERATURE,
            max_tokens=settings.AI_MAX_TOKENS
        )
        self.anthropic = ChatAnthropic(
            model="claude-3-sonnet-20240229",
            temperature=settings.AI_TEMPERATURE,
            max_tokens=settings.AI_MAX_TOKENS
        )

        # Initialize output parser
        self.parser = PydanticOutputParser(pydantic_object=NodeUpdate)

        # Create enrichment prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert nutritionist and researcher. Your task is to 
            enrich the provided node with accurate, well-researched information. Focus on:
            1. Detailed descriptions
            2. Nutritional content
            3. Health implications
            4. Environmental impact
            5. Source verification

            Format the output as a valid NodeUpdate object."""),
            ("human", "Please enrich the following node:\n{node}"),
        ])

        # Create enrichment chain
        self.chain = LLMChain(
            llm=self.openai,
            prompt=self.prompt,
            output_parser=self.parser,
            verbose=True
        )

    async def enrich_node(self, node: Node) -> NodeUpdate:
        """Enrich a node with AI-generated content."""
        try:
            # Try with OpenAI first
            result = await self.chain.arun(node=node.dict())
            return result
        except Exception as e:
            # Fallback to Anthropic
            try:
                self.chain.llm = self.anthropic
                result = await self.chain.arun(node=node.dict())
                return result
            except Exception as fallback_e:
                # If both fail, raise the original error
                raise Exception(
                    f"Failed to enrich node with both models: {str(e)}, {str(fallback_e)}"
                )

    async def validate_source(self, source_url: str) -> Dict[str, Any]:
        """Validate a source URL and calculate reliability score."""
        try:
            # Create source validation prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert at evaluating source reliability. 
                Analyze the provided URL and determine:
                1. Domain authority
                2. Content quality
                3. Scientific rigor
                4. Update frequency
                5. Citation quality

                Return a reliability score between 0 and 1, along with justification."""),
                ("human", f"Please evaluate this source: {source_url}"),
            ])

            # Create validation chain
            chain = LLMChain(
                llm=self.openai,
                prompt=prompt,
                verbose=True
            )

            # Get validation result
            result = await chain.arun()
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
            - Seasonal variations"""
        }
        
        return prompts.get(node_type, "Provide detailed, accurate information about this item.") 