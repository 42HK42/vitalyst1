# Ticket 2.9: Multi-Language Support

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive multi-language support system for the Vitalyst Knowledge Graph that handles translations, content versioning, and validation workflows for all textual content. The system must support multiple languages, maintain translation quality, and provide efficient content management while following the blueprint specifications.

## Technical Details

1. Language Models
```python
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Union, Literal
from datetime import datetime
import uuid

class SupportedLanguage(str, Enum):
    DE = "de"  # German (Primary)
    EN = "en"  # English
    FR = "fr"  # French
    ES = "es"  # Spanish
    IT = "it"  # Italian
    
    @classmethod
    def primary_language(cls) -> 'SupportedLanguage':
        return cls.DE

class TranslationMetadata(BaseModel):
    translator_id: Optional[str]
    translation_date: datetime
    source_language: SupportedLanguage
    translation_method: Literal['manual', 'ai', 'verified']
    confidence_score: float = Field(ge=0.0, le=1.0)
    review_status: str = "pending"
    reviewer_id: Optional[str]
    review_date: Optional[datetime]
    review_comments: Optional[str]
    version: str = "1.0.0"

class TranslatedContent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str
    content_type: Literal['name', 'description', 'usage', 'warning']
    translations: Dict[SupportedLanguage, str]
    metadata: Dict[SupportedLanguage, TranslationMetadata]
    fallback_language: SupportedLanguage = Field(default=SupportedLanguage.DE)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version_history: Dict[SupportedLanguage, List[Dict[str, any]]] = {}
    
    @validator('translations')
    def validate_translations(cls, v):
        if SupportedLanguage.DE not in v:
            raise ValueError('German (DE) translation is required')
        return v
    
    @validator('metadata')
    def validate_metadata(cls, v, values):
        if 'translations' in values:
            if set(v.keys()) != set(values['translations'].keys()):
                raise ValueError('Metadata must exist for all translations')
        return v

class TranslationManager:
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        
    async def update_translations(
        self,
        node_id: str,
        content: TranslatedContent,
        user_id: str
    ) -> str:
        """Update node translations with version tracking"""
        try:
            async with self.driver.session() as session:
                async with session.begin_transaction() as tx:
                    # Store translation content
                    result = await tx.run("""
                    MATCH (n) WHERE n.id = $node_id
                    CREATE (t:Translation $translation_props)
                    CREATE (n)-[:HAS_TRANSLATION {
                        content_type: $content_type,
                        created_at: datetime(),
                        created_by: $user_id
                    }]->(t)
                    RETURN t.id as translation_id
                    """, {
                        "node_id": node_id,
                        "translation_props": content.dict(),
                        "content_type": content.content_type,
                        "user_id": user_id
                    })
                    
                    translation_id = (await result.single())["translation_id"]
                    
                    # Update version history
                    for lang, text in content.translations.items():
                        await self._store_version_history(
                            tx,
                            translation_id,
                            lang,
                            text,
                            content.metadata[lang]
                        )
                    
                    await tx.commit()
                    
                    self.logger.info(
                        f"Updated translations for node {node_id}",
                        extra={
                            "translation_id": translation_id,
                            "languages": list(content.translations.keys())
                        }
                    )
                    
                    return translation_id
                    
        except Exception as e:
            self.logger.error(
                f"Failed to update translations: {str(e)}",
                extra={"node_id": node_id, "content": content.dict()}
            )
            raise
    
    async def _store_version_history(
        self,
        tx,
        translation_id: str,
        language: SupportedLanguage,
        text: str,
        metadata: TranslationMetadata
    ) -> None:
        """Store version history for translation"""
        await tx.run("""
        MATCH (t:Translation {id: $translation_id})
        CREATE (v:TranslationVersion {
            language: $language,
            text: $text,
            metadata: $metadata,
            created_at: datetime()
        })
        CREATE (t)-[:HAS_VERSION]->(v)
        """, {
            "translation_id": translation_id,
            "language": language,
            "text": text,
            "metadata": metadata.dict()
        })
```

2. Translation Workflow Implementation
```python
class TranslationWorkflow:
    def __init__(self, translation_manager, validator, logger):
        self.translation_manager = translation_manager
        self.validator = validator
        self.logger = logger
        
    async def process_translation_request(
        self,
        node_id: str,
        content_type: str,
        target_languages: List[SupportedLanguage],
        source_text: str,
        user_id: str
    ) -> TranslatedContent:
        """Process translation request with validation"""
        try:
            # Initialize translation content
            content = TranslatedContent(
                node_id=node_id,
                content_type=content_type,
                translations={SupportedLanguage.DE: source_text},
                metadata={
                    SupportedLanguage.DE: TranslationMetadata(
                        source_language=SupportedLanguage.DE,
                        translation_method='manual',
                        confidence_score=1.0,
                        translator_id=user_id
                    )
                }
            )
            
            # Generate translations
            for lang in target_languages:
                if lang != SupportedLanguage.DE:
                    translation = await self._generate_translation(
                        source_text,
                        SupportedLanguage.DE,
                        lang
                    )
                    
                    content.translations[lang] = translation.text
                    content.metadata[lang] = translation.metadata
            
            # Validate translations
            validation_results = await self.validator.validate_translations(content)
            if not validation_results.is_valid:
                self.logger.warning(
                    "Translation validation failed",
                    extra={"errors": validation_results.errors}
                )
                
            # Store translations
            translation_id = await self.translation_manager.update_translations(
                node_id,
                content,
                user_id
            )
            
            return content
            
        except Exception as e:
            self.logger.error(
                f"Translation request failed: {str(e)}",
                extra={
                    "node_id": node_id,
                    "content_type": content_type,
                    "target_languages": target_languages
                }
            )
            raise
    
    async def _generate_translation(
        self,
        text: str,
        source_lang: SupportedLanguage,
        target_lang: SupportedLanguage
    ) -> Dict[str, any]:
        """Generate translation using AI or external service"""
        # Implementation for translation generation
        pass
```

3. Translation Validation Implementation
```python
class TranslationValidator:
    def __init__(self, logger):
        self.logger = logger
        
    async def validate_translations(
        self,
        content: TranslatedContent
    ) -> ValidationResult:
        """Validate translation content and quality"""
        errors = []
        warnings = []
        
        # Validate required languages
        if SupportedLanguage.DE not in content.translations:
            errors.append("German (DE) translation is required")
            
        # Validate metadata
        for lang, text in content.translations.items():
            if lang not in content.metadata:
                errors.append(f"Missing metadata for language: {lang}")
            else:
                # Validate translation quality
                quality_issues = self._check_translation_quality(
                    text,
                    content.metadata[lang]
                )
                warnings.extend(quality_issues)
        
        # Validate version history
        if content.version_history:
            history_issues = self._validate_version_history(content)
            warnings.extend(history_issues)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _check_translation_quality(
        self,
        text: str,
        metadata: TranslationMetadata
    ) -> List[str]:
        """Check translation quality metrics"""
        issues = []
        
        # Check confidence score
        if metadata.confidence_score < 0.8:
            issues.append(
                f"Low confidence score: {metadata.confidence_score}"
            )
        
        # Add more quality checks as needed
        return issues
```

4. Query Optimization
```python
class TranslationQueryOptimizer:
    def __init__(self, driver):
        self.driver = driver
        
    async def get_node_translations(
        self,
        node_id: str,
        languages: Optional[List[SupportedLanguage]] = None,
        include_history: bool = False
    ) -> Dict[str, any]:
        """Get optimized node translations"""
        query = """
        MATCH (n)-[:HAS_TRANSLATION]->(t:Translation)
        WHERE n.id = $node_id
        """
        
        if languages:
            query += """
            WITH n, t
            WHERE any(lang IN $languages WHERE lang IN keys(t.translations))
            """
            
        if include_history:
            query += """
            OPTIONAL MATCH (t)-[:HAS_VERSION]->(v:TranslationVersion)
            """
            
        query += """
        RETURN t as translation,
               collect(v) as versions
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {
                "node_id": node_id,
                "languages": languages
            })
            
            record = await result.single()
            if not record:
                return None
                
            return {
                "translation": record["translation"],
                "versions": record["versions"] if include_history else None
            }
```

## Implementation Strategy
1. Language Support Setup
   - Implement language models
   - Create translation workflow
   - Set up validation rules
   - Configure versioning

2. Translation Management
   - Implement translation manager
   - Create workflow engine
   - Set up quality checks
   - Configure audit trails

3. Query Optimization
   - Create optimized queries
   - Implement caching
   - Set up indexing
   - Configure fallbacks

4. Integration
   - Implement node translations
   - Set up content propagation
   - Configure validation flow
   - Implement reporting

## Acceptance Criteria
- [ ] Multi-language models implemented
- [ ] Translation workflow working
- [ ] Content versioning functioning
- [ ] Validation system implemented
- [ ] Quality checks working
- [ ] Fallback handling configured
- [ ] Query optimization completed
- [ ] Caching system working
- [ ] Documentation completed
- [ ] Performance benchmarks met
- [ ] Test coverage complete
- [ ] Integration tests passing

## Dependencies
- Ticket 2.4: CSV-Specific Models
- Ticket 2.6: Data Validation Workflow
- Ticket 2.8: Historical Tracking

## Estimated Hours
30

## Testing Requirements
- Model Tests
  - Test language models
  - Verify translations
  - Check validation rules
  - Validate versioning
- Workflow Tests
  - Test translation process
  - Verify quality checks
  - Test fallback handling
  - Validate audit trails
- Integration Tests
  - Test node translations
  - Verify content propagation
  - Test validation flow
  - Check reporting
- Performance Tests
  - Measure query speed
  - Test concurrent translations
  - Verify memory usage
  - Benchmark operations

## Documentation
- Language support overview
- Translation workflow guide
- Validation procedures
- Version control guide
- Quality metrics documentation
- Performance tuning guide
- Integration patterns
- Best practices

## Search Space Optimization
- Clear language hierarchy
- Logical translation workflow
- Consistent validation patterns
- Standardized versioning
- Organized query patterns

## References
- Blueprint Section 3.1: Hierarchical Node Modeling
- Blueprint Section 4: API and Data Import
- Blueprint Section 3.2: Data Model Consistency
- Blueprint Section 5: Data Quality and Validation
- Translation Management Best Practices
- Content Versioning Guidelines

## Notes
- Implements comprehensive language support
- Ensures translation quality
- Optimizes workflows
- Supports versioning
- Maintains performance 