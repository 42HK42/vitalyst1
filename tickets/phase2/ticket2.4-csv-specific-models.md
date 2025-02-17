# Ticket 2.4: CSV-Specific Models and Import Validation

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive data models and validation system for Tab_Vit_C_v7.csv and Nahrungsmittel_Database2_real.csv, ensuring proper data transformation, validation, and enrichment while maintaining data quality and traceability as specified in the blueprint.

## Technical Details

1. CSV Model Definitions
```python
from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Optional, Dict, Union, Literal
from datetime import datetime
from enum import Enum
import re

class MeasurementUnit(Enum):
    MG = "mg"
    G = "g"
    ML = "ml"
    L = "l"
    MCG = "mcg"
    IU = "IU"

class SourceType(Enum):
    LABORATORY = "laboratory"
    LITERATURE = "literature"
    DATABASE = "database"
    EXPERT = "expert"

class DataQuality(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Measurement(BaseModel):
    value: float
    unit: MeasurementUnit
    uncertainty: float
    confidence_interval: Optional[tuple[float, float]]
    measurement_method: str
    measurement_date: datetime
    measured_by: str
    equipment_id: Optional[str]
    
    @validator('value')
    def validate_value(cls, v):
        if v < 0:
            raise ValueError("Measurement value cannot be negative")
        return v
    
    @validator('uncertainty')
    def validate_uncertainty(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Uncertainty must be between 0 and 1")
        return v

class SourceReference(BaseModel):
    source_type: SourceType
    reference_id: str
    title: str
    authors: Optional[List[str]]
    publication_date: Optional[datetime]
    doi: Optional[str]
    url: Optional[str]
    accessed_date: datetime
    reliability_score: float
    data_quality: DataQuality
    
    @validator('reliability_score')
    def validate_reliability(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Reliability score must be between 0 and 1")
        return v

class VitaminCSourceData(BaseModel):
    id: str = Field(..., regex=r'^vit_c_[0-9]{3}$')
    name: str
    chemical_formula: str
    molecular_weight: float
    measurements: List[Measurement]
    source: SourceReference
    enrichment_history: List[Dict[str, any]] = []
    validation_status: str = "pending"
    metadata: Dict[str, any] = {}
    
    @validator('chemical_formula')
    def validate_formula(cls, v):
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', v):
            raise ValueError("Invalid chemical formula format")
        return v
    
    @root_validator
    def validate_measurements(cls, values):
        measurements = values.get('measurements', [])
        if not measurements:
            raise ValueError("At least one measurement required")
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "id": "vit_c_001",
                "name": "Ascorbic Acid",
                "chemical_formula": "C6H8O6",
                "molecular_weight": 176.12,
                "measurements": [{
                    "value": 4.6,
                    "unit": "mg",
                    "uncertainty": 0.2,
                    "measurement_method": "HPLC",
                    "measurement_date": "2023-01-01T00:00:00Z",
                    "measured_by": "Lab Tech 1",
                    "equipment_id": "HPLC-001"
                }],
                "source": {
                    "source_type": "laboratory",
                    "reference_id": "LAB-2023-001",
                    "title": "Vitamin C Analysis Report",
                    "accessed_date": "2023-01-01T00:00:00Z",
                    "reliability_score": 0.95,
                    "data_quality": "high"
                }
            }
        }

class EnvironmentalMetric(BaseModel):
    value: float
    unit: str
    calculation_method: str
    uncertainty: float
    source: SourceReference
    temporal_validity: Optional[tuple[datetime, datetime]]
    
    @validator('uncertainty')
    def validate_uncertainty(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Uncertainty must be between 0 and 1")
        return v

class NutrientContent(BaseModel):
    nutrient_id: str
    amount: float
    unit: MeasurementUnit
    bioavailability: Optional[float]
    source: SourceReference
    
    @validator('bioavailability')
    def validate_bioavailability(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError("Bioavailability must be between 0 and 1")
        return v

class NahrungsmittelData(BaseModel):
    id: str = Field(..., regex=r'^food_[0-9]{3}$')
    food_name: str
    scientific_name: Optional[str]
    category: List[str]
    subcategory: Optional[str]
    environmental_metrics: Dict[str, EnvironmentalMetric]
    nutrient_content: List[NutrientContent]
    seasonal_availability: Optional[List[str]]
    storage_conditions: str
    processing_methods: List[str]
    source: SourceReference
    enrichment_history: List[Dict[str, any]] = []
    validation_status: str = "pending"
    metadata: Dict[str, any] = {}
    
    @validator('category')
    def validate_category(cls, v):
        valid_categories = {"vegetable", "fruit", "grain", "protein", "dairy", "other"}
        if not all(cat in valid_categories for cat in v):
            raise ValueError(f"Invalid category. Must be one of {valid_categories}")
        return v
    
    @root_validator
    def validate_nutrient_content(cls, values):
        nutrients = values.get('nutrient_content', [])
        if not nutrients:
            raise ValueError("At least one nutrient content required")
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "id": "food_001",
                "food_name": "Apple",
                "scientific_name": "Malus domestica",
                "category": ["fruit"],
                "environmental_metrics": {
                    "co2_footprint": {
                        "value": 0.5,
                        "unit": "kg CO2e/kg",
                        "calculation_method": "LCA",
                        "uncertainty": 0.1,
                        "source": {
                            "source_type": "database",
                            "reference_id": "ENV-DB-001",
                            "title": "Food Environmental Impact Database",
                            "accessed_date": "2023-01-01T00:00:00Z",
                            "reliability_score": 0.9,
                            "data_quality": "high"
                        }
                    }
                },
                "nutrient_content": [{
                    "nutrient_id": "vit_c_001",
                    "amount": 4.6,
                    "unit": "mg",
                    "bioavailability": 0.85,
                    "source": {
                        "source_type": "laboratory",
                        "reference_id": "LAB-2023-001",
                        "title": "Nutrient Analysis Report",
                        "accessed_date": "2023-01-01T00:00:00Z",
                        "reliability_score": 0.95,
                        "data_quality": "high"
                    }
                }]
            }
        }
```

2. Import Validation and Transformation
```python
from typing import List, Dict, Any, Tuple
import pandas as pd
from pydantic import ValidationError
import logging
from datetime import datetime
from pathlib import Path

class DataTransformer:
    def __init__(self):
        self.logger = self.setup_logger()
    
    def setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('data_transformer')
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler('import_logs.jsonl')
        handler.setFormatter(logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        ))
        logger.addHandler(handler)
        return logger
    
    def transform_vitamin_c_data(self, row: pd.Series) -> Dict[str, Any]:
        """Transform raw vitamin C data into structured format"""
        try:
            measurement = Measurement(
                value=row['value'],
                unit=row['unit'],
                uncertainty=row['uncertainty'],
                measurement_method=row['method'],
                measurement_date=pd.to_datetime(row['date']),
                measured_by=row['technician'],
                equipment_id=row.get('equipment_id')
            )
            
            source = SourceReference(
                source_type=row['source_type'],
                reference_id=row['reference_id'],
                title=row['title'],
                accessed_date=pd.to_datetime(row['accessed_date']),
                reliability_score=row['reliability'],
                data_quality=row['quality']
            )
            
            return VitaminCSourceData(
                id=f"vit_c_{row.name:03d}",
                name=row['name'],
                chemical_formula=row['formula'],
                molecular_weight=row['molecular_weight'],
                measurements=[measurement],
                source=source
            ).dict()
            
        except Exception as e:
            self.logger.error(f"Error transforming row {row.name}: {str(e)}")
            raise

class CSVValidator:
    def __init__(self, csv_path: Path):
        self.csv_path = csv_path
        self.transformer = DataTransformer()
        self.logger = self.transformer.logger
        
    def validate_file(self) -> bool:
        """Validate CSV file structure and accessibility"""
        try:
            if not self.csv_path.exists():
                raise FileNotFoundError(f"File not found: {self.csv_path}")
            
            if self.csv_path.stat().st_size == 0:
                raise ValueError("File is empty")
            
            df = pd.read_csv(self.csv_path)
            return True
            
        except Exception as e:
            self.logger.error(f"File validation failed: {str(e)}")
            return False
    
    def validate_vitamin_c_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Validate and transform vitamin C data"""
        valid_records = []
        invalid_records = []
        
        try:
            df = pd.read_csv(self.csv_path)
            
            for idx, row in df.iterrows():
                try:
                    transformed_data = self.transformer.transform_vitamin_c_data(row)
                    valid_records.append({
                        "row": idx,
                        "data": transformed_data,
                        "validation_date": datetime.now().isoformat()
                    })
                    
                except ValidationError as e:
                    invalid_records.append({
                        "row": idx,
                        "errors": e.errors(),
                        "raw_data": row.to_dict(),
                        "validation_date": datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    self.logger.error(f"Unexpected error in row {idx}: {str(e)}")
                    invalid_records.append({
                        "row": idx,
                        "errors": [{"msg": str(e)}],
                        "raw_data": row.to_dict(),
                        "validation_date": datetime.now().isoformat()
                    })
            
            self.log_validation_results(valid_records, invalid_records)
            return valid_records, invalid_records
            
        except Exception as e:
            self.logger.error(f"Validation process failed: {str(e)}")
            raise
    
    def log_validation_results(self, valid: List[Dict], invalid: List[Dict]) -> None:
        """Log validation results"""
        self.logger.info(
            f"Validation completed: {len(valid)} valid records, "
            f"{len(invalid)} invalid records"
        )
        
        if invalid:
            self.logger.warning(
                f"Invalid records found: {json.dumps(invalid, indent=2)}"
            )
```

3. Data Quality Checks
```python
class DataQualityChecker:
    def __init__(self):
        self.logger = logging.getLogger('data_quality')
    
    def check_completeness(self, df: pd.DataFrame) -> Dict[str, float]:
        """Check data completeness"""
        return {
            col: (1 - df[col].isna().mean()) * 100
            for col in df.columns
        }
    
    def check_consistency(self, df: pd.DataFrame) -> List[Dict]:
        """Check data consistency"""
        issues = []
        
        # Check value ranges
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_cols:
            stats = df[col].describe()
            if stats['std'] > stats['mean'] * 2:
                issues.append({
                    'type': 'high_variance',
                    'column': col,
                    'mean': stats['mean'],
                    'std': stats['std']
                })
        
        # Check categorical consistency
        cat_cols = df.select_dtypes(include=['object']).columns
        for col in cat_cols:
            value_counts = df[col].value_counts()
            if len(value_counts) > len(df) * 0.5:
                issues.append({
                    'type': 'high_cardinality',
                    'column': col,
                    'unique_values': len(value_counts)
                })
        
        return issues
    
    def check_accuracy(self, df: pd.DataFrame) -> List[Dict]:
        """Check data accuracy"""
        issues = []
        
        # Check for outliers
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            outliers = df[
                (df[col] < Q1 - 1.5 * IQR) |
                (df[col] > Q3 + 1.5 * IQR)
            ]
            if len(outliers) > 0:
                issues.append({
                    'type': 'outliers',
                    'column': col,
                    'count': len(outliers),
                    'indices': outliers.index.tolist()
                })
        
        return issues
```

## Implementation Strategy
1. Data Model Setup
   - Create base models
   - Define validation rules
   - Implement transformations
   - Set up quality checks

2. Import Process
   - Implement file validation
   - Create data transformation
   - Set up error handling
   - Configure logging

3. Quality Assurance
   - Implement completeness checks
   - Set up consistency validation
   - Create accuracy verification
   - Test data quality

## Acceptance Criteria
- [ ] Comprehensive data models created for both CSV formats
- [ ] Validation rules implemented and tested
- [ ] Data transformation logic created and verified
- [ ] Quality checks implemented
- [ ] Error handling and logging configured
- [ ] Data cleaning procedures established
- [ ] Source tracking implemented
- [ ] Documentation completed
- [ ] Performance benchmarks met
- [ ] Test coverage complete
- [ ] Migration utilities created
- [ ] Audit trail implemented

## Dependencies
- Ticket 2.2: Graph Schema
- Ticket 2.3: Model Definitions

## Estimated Hours
25

## Testing Requirements
- Data Model Tests
  - Test model validation
  - Verify transformation logic
  - Check constraint enforcement
  - Validate relationships
- Import Tests
  - Test file validation
  - Verify data transformation
  - Check error handling
  - Test logging system
- Quality Tests
  - Test completeness checks
  - Verify consistency rules
  - Validate accuracy checks
  - Test outlier detection
- Performance Tests
  - Measure import speed
  - Test memory usage
  - Verify scalability
  - Benchmark operations

## Documentation
- Data model specifications
- Validation rules guide
- Transformation procedures
- Quality check documentation
- Error handling guide
- Performance optimization
- Migration procedures
- Best practices

## Search Space Optimization
- Clear model hierarchy
- Logical validation organization
- Consistent transformation patterns
- Standardized quality checks
- Organized utility functions

## References
- Blueprint Section 2: Architecture and Module Overview
- Blueprint Section 3: Data Model & Graph Structure
- Blueprint Section 4: Data Import and Validation
- Blueprint Section 5: Data Quality and Verification
- Blueprint Section 6: Data Sources and Integration Pipeline
- Pydantic Documentation
- Pandas Documentation

## Notes
- Implements comprehensive models
- Ensures data quality
- Optimizes transformations
- Supports traceability
- Maintains consistency 