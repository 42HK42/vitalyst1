# Ticket 2.7: CSV-Specific Models

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive data models and transformation logic for Tab_Vit_C_v7.csv and Nahrungsmittel_Database2_real.csv, ensuring proper mapping to the hierarchical node structure while maintaining data quality, versioning, and audit trails. The implementation must follow the blueprint specifications for data import and validation.

## Technical Details

1. Base CSV Models
```python
from pydantic import BaseModel, Field, validator, root_validator
from typing import Dict, List, Optional, Union
from datetime import datetime
import uuid
import re

class BaseCSVModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_file: str
    source_line: int
    import_timestamp: datetime = Field(default_factory=datetime.utcnow)
    validation_status: str = "pending"
    data_quality_score: float = Field(ge=0.0, le=1.0)
    version: str = "1.0.0"
    metadata: Dict[str, any] = {}
    
    @validator('data_quality_score')
    def validate_quality_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Quality score must be between 0 and 1')
        return v

class LanguageContent(BaseModel):
    de: str
    en: Optional[str]
    source: Optional[str]
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    confidence_score: float = Field(ge=0.0, le=1.0)

class MeasurementData(BaseModel):
    value: float
    unit: str
    method: str
    timestamp: datetime
    uncertainty: Optional[float]
    source: str
    validation_status: str = "pending"
    confidence_score: float = Field(ge=0.0, le=1.0)
```

2. Vitamin CSV Model
```python
class VitaminCEntry(BaseCSVModel):
    vitID: str = Field(..., regex=r'^VIT_[A-Z0-9]+$')
    name: Dict[str, LanguageContent]
    chemical_formula: str
    molecular_weight: MeasurementData
    description: Dict[str, LanguageContent]
    sources: List[Dict[str, any]] = Field(..., min_items=1)
    bioavailability: MeasurementData
    interactions: List[Dict[str, any]] = []
    research_references: List[Dict[str, any]] = []
    
    @root_validator
    def validate_sources(cls, values):
        sources = values.get('sources', [])
        if not all('reliability_score' in s for s in sources):
            raise ValueError('All sources must have reliability scores')
        return values
    
    def to_node(self) -> Dict:
        """Transform to graph node structure"""
        return {
            'type': 'Nutrient',
            'vitID': self.vitID,
            'name': self.name['en'].dict() if 'en' in self.name else self.name['de'].dict(),
            'properties': {
                'chemical_formula': self.chemical_formula,
                'molecular_weight': self.molecular_weight.dict(),
                'bioavailability': self.bioavailability.dict()
            },
            'metadata': {
                **self.metadata,
                'import_source': self.source_file,
                'import_timestamp': self.import_timestamp,
                'version': self.version
            },
            'validation': {
                'status': self.validation_status,
                'quality_score': self.data_quality_score,
                'source_reliability': min(s['reliability_score'] for s in self.sources)
            }
        }
```

3. Food CSV Model
```python
class EnvironmentalData(BaseModel):
    co2_footprint: MeasurementData
    water_usage: MeasurementData
    land_use: Optional[MeasurementData]
    biodiversity_impact: Optional[Dict[str, any]]
    seasonal_factors: Dict[str, float] = {}
    regional_data: Dict[str, Dict[str, any]] = {}
    
    @validator('seasonal_factors')
    def validate_seasonal_factors(cls, v):
        if not all(0 <= factor <= 2 for factor in v.values()):
            raise ValueError('Seasonal factors must be between 0 and 2')
        return v

class NahrungsmittelEntry(BaseCSVModel):
    name: Dict[str, LanguageContent]
    category: List[str] = Field(..., min_items=1)
    subcategory: Optional[List[str]]
    environmental_data: EnvironmentalData
    seasonal_availability: List[str] = []
    storage_conditions: Dict[str, any]
    preparation_methods: List[Dict[str, any]] = []
    nutrient_content: List[Dict[str, MeasurementData]] = Field(..., min_items=1)
    allergens: List[str] = []
    
    @root_validator
    def validate_categories(cls, values):
        valid_categories = {
            'vegetable', 'fruit', 'grain', 'protein', 'dairy', 'other'
        }
        categories = values.get('category', [])
        if not all(c in valid_categories for c in categories):
            raise ValueError(f'Invalid categories. Must be one of: {valid_categories}')
        return values
    
    def to_node(self) -> Dict:
        """Transform to graph node structure"""
        return {
            'type': 'Food',
            'name': self.name['en'].dict() if 'en' in self.name else self.name['de'].dict(),
            'category': self.category,
            'properties': {
                'seasonal_availability': self.seasonal_availability,
                'storage_conditions': self.storage_conditions,
                'preparation_methods': self.preparation_methods,
                'allergens': self.allergens
            },
            'environmental_metrics': self.environmental_data.dict(),
            'nutrient_content': {
                nutrient['id']: nutrient['measurement'].dict()
                for nutrient in self.nutrient_content
            },
            'metadata': {
                **self.metadata,
                'import_source': self.source_file,
                'import_timestamp': self.import_timestamp,
                'version': self.version
            },
            'validation': {
                'status': self.validation_status,
                'quality_score': self.data_quality_score
            }
        }
```

4. Data Transformation and Cleaning
```python
class CSVDataTransformer:
    def __init__(self, logger):
        self.logger = logger
        
    async def transform_vitamin_data(
        self,
        raw_data: Dict,
        line_number: int,
        source_file: str
    ) -> VitaminCEntry:
        """Transform raw CSV data to VitaminCEntry"""
        try:
            # Clean and normalize data
            cleaned_data = {
                'vitID': self._normalize_vit_id(raw_data['VitaminID']),
                'name': self._create_language_content(
                    raw_data['Name_DE'],
                    raw_data.get('Name_EN')
                ),
                'chemical_formula': raw_data['ChemicalFormula'].strip(),
                'molecular_weight': self._create_measurement(
                    raw_data['MolecularWeight'],
                    'g/mol',
                    raw_data.get('MeasurementMethod')
                ),
                'description': self._create_language_content(
                    raw_data['Description_DE'],
                    raw_data.get('Description_EN')
                ),
                'sources': self._parse_sources(raw_data['Sources']),
                'bioavailability': self._create_measurement(
                    raw_data['Bioavailability'],
                    '%',
                    'standard_measurement'
                ),
                'source_file': source_file,
                'source_line': line_number
            }
            
            return VitaminCEntry(**cleaned_data)
            
        except Exception as e:
            self.logger.error(
                f"Error transforming vitamin data at line {line_number}",
                extra={'error': str(e), 'raw_data': raw_data}
            )
            raise
    
    async def transform_food_data(
        self,
        raw_data: Dict,
        line_number: int,
        source_file: str
    ) -> NahrungsmittelEntry:
        """Transform raw CSV data to NahrungsmittelEntry"""
        try:
            # Clean and normalize data
            cleaned_data = {
                'name': self._create_language_content(
                    raw_data['Name_DE'],
                    raw_data.get('Name_EN')
                ),
                'category': self._normalize_categories(raw_data['Category']),
                'environmental_data': {
                    'co2_footprint': self._create_measurement(
                        raw_data['CO2_Footprint'],
                        'kg CO2e/kg',
                        raw_data.get('CO2_Method')
                    ),
                    'water_usage': self._create_measurement(
                        raw_data['WaterUsage'],
                        'L/kg',
                        raw_data.get('Water_Method')
                    )
                },
                'seasonal_availability': self._parse_seasons(
                    raw_data['SeasonalAvailability']
                ),
                'source_file': source_file,
                'source_line': line_number
            }
            
            return NahrungsmittelEntry(**cleaned_data)
            
        except Exception as e:
            self.logger.error(
                f"Error transforming food data at line {line_number}",
                extra={'error': str(e), 'raw_data': raw_data}
            )
            raise
    
    def _normalize_vit_id(self, raw_id: str) -> str:
        """Normalize vitamin ID format"""
        cleaned = re.sub(r'[^A-Z0-9]', '', raw_id.upper())
        if not cleaned.startswith('VIT'):
            cleaned = f'VIT_{cleaned}'
        return cleaned
    
    def _create_language_content(
        self,
        de_text: str,
        en_text: Optional[str] = None
    ) -> Dict[str, LanguageContent]:
        """Create language content structure"""
        return {
            'de': LanguageContent(
                de=de_text.strip(),
                confidence_score=1.0
            ),
            **(
                {'en': LanguageContent(
                    en=en_text.strip(),
                    confidence_score=0.9
                )} if en_text else {}
            )
        }
```

## Implementation Strategy
1. Model Development
   - Create base CSV models
   - Implement specific models for each source
   - Set up validation rules
   - Configure transformations

2. Data Cleaning and Transformation
   - Implement data cleaning logic
   - Create transformation utilities
   - Set up validation checks
   - Configure error handling

3. Integration with Node Structure
   - Implement node mapping
   - Set up relationship creation
   - Configure data propagation
   - Implement versioning

4. Quality Assurance
   - Implement data validation
   - Create quality metrics
   - Set up error reporting
   - Configure monitoring

## Acceptance Criteria
- [ ] CSV models implemented for both data sources
- [ ] Data cleaning and transformation working
- [ ] Validation rules implemented and tested
- [ ] Multi-language support functioning
- [ ] Environmental metrics properly handled
- [ ] Source tracking implemented
- [ ] Version control working
- [ ] Error handling configured
- [ ] Data quality metrics implemented
- [ ] Documentation completed
- [ ] Performance benchmarks met
- [ ] Test coverage complete

## Dependencies
- Ticket 2.2: Graph Schema
- Ticket 2.5: Hierarchical Node Structure
- Ticket 2.6: Data Validation Workflow

## Estimated Hours
30

## Testing Requirements
- Model Tests
  - Test data validation
  - Verify transformations
  - Check error handling
  - Validate versioning
- Data Quality Tests
  - Test cleaning logic
  - Verify normalization
  - Check consistency
  - Validate relationships
- Integration Tests
  - Test node mapping
  - Verify data propagation
  - Test version control
  - Check audit trails
- Performance Tests
  - Measure transformation speed
  - Test memory usage
  - Verify scalability
  - Benchmark operations

## Documentation
- CSV format specifications
- Data model documentation
- Transformation rules
- Validation procedures
- Error handling guide
- Performance tuning
- Integration patterns
- Best practices

## Search Space Optimization
- Clear model hierarchy
- Logical transformation rules
- Consistent validation patterns
- Standardized error handling
- Organized utility functions

## References
- Blueprint Section 3.1: Hierarchical Node Modeling
- Blueprint Section 6: Data Sources and Integration Pipeline
- Blueprint Section 3.2: Data Model Consistency
- Blueprint Section 5: Data Quality and Validation
- CSV Processing Best Practices
- Data Cleaning Guidelines

## Notes
- Implements comprehensive models
- Ensures data quality
- Optimizes transformations
- Supports versioning
- Maintains audit trail 