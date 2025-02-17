# Projekt Blueprint: Vitalyst Knowledge Graph

**Status:** Living Document  
**Last Updated:** [Current Date]

## Inhaltsverzeichnis
1. [Übersicht](#1-%C3%9Cbersicht)
2. [Architektur und Modulübersicht](#2-architektur-und-modul%C3%BCbersicht)
3. [Datenmodell & Graph-Struktur](#3-datenmodell--graph-struktur)
4. [API und Datenimport](#4-api-und-datenimport)
   4.1 [JSON Schema Definitions](#41-json-schema-definitions)
5. [AI-Integration](#5-ai-integration)
6. [Datenquellen und Integrations-Pipeline](#6-datenquellen-und-integrations-pipeline)
7. [Entwicklungsplan & Testgetriebene Entwicklung (TDD)](#7-entwicklungsplan--testgetriebene-entwicklung-tdd)
8. [Rollen, Workflows & Validierung](#8-rollen-workflows--validierung)
9. [Frameworks, Deployment, Sicherheit & Monitoring](#9-frameworks-deployment-sicherheit--monitoring)
10. [Fazit](#10-fazit)
11. [User Interface and Experience (UI/UX & CX)](#11-user-interface-and-experience-uixuxcx)

---

## 1. Übersicht
Dieses Projekt zielt darauf ab, eine wissensbasierte Graph-Datenbank für Vitamine und Spurenelemente aufzubauen. Daten werden in einer Neo4j-Datenbank mit integrierten Vektor-Embeddings gespeichert. Unterschiedliche Quellen – z.B. _Excel-Vorlagen_ (@Tab_Vit_C_v7.csv) und umfangreiche Nahrungsmitteldaten aus _CSV-Dateien_ (@Nahrungsmittel_Database2_real.csv) – werden importiert, crossreferenziert und in einem versionierten, validierbaren Datenmodell zusammengeführt.

**Zentrale Aspekte:**
- Lokaler Server mit Daten-Erzeugung, Validierung und Versionierung
- Einfach strukturierte API-Endpoints (Python/FastAPI) mit klaren JSON-Schemas
- Interaktive Frontends (React + Remix mit React Flow) für die Visualisierung und Bearbeitung
- AI-gestützte Inhaltsanreicherung via Frontier-Modellen (unter Verwendung von LangChain)
- Zwei Frontends: Intern (Datenkuratierung, medizinische Validierung) und öffentlich (ansprechende Visualisierung)

---

## 2. Architektur und Modulübersicht

### High-Level Architektur Diagramm
```mermaid
graph TD
    A[Neo4j Graph DB] --> B[FastAPI Backend]
    B --> C[React/Remix Frontend]
    D[OAuth] --> B
    E[AI APIs (OpenAI, Claude)] --> B
```

### Modulübersicht
- **Lokaler Server & Daten-Erzeugung:** Verantwortlich für die Generierung, Validierung und Versionierung von Datenknoten.
- **Graph-Datenbank (Neo4j):** Speicherung der Wissensdatenbank inklusive Vektor-Embeddings. Import initialer Daten aus Excel und CSV.
- **Backend (Python/FastAPI):** Bereitstellung von API-Endpunkten für Datenkuratierung, Validierung, Versionierung und AI-Anreicherung.
- **Frontend (React/Remix):** Interaktive Visualisierung (React Flow) und Editor für einzelne Knoten. Unterschiedliche Ansichten für interne Validierung und öffentliche Darstellung.
- **Testing & CI/CD:** Einsatz von pytest (Backend) und Vitest (Frontend). Lokales Deployment via Docker.
- **AI-Integration:** Anreicherung von Knoten mit AI-Prompts über Frontier-Modelle. 

## 3. Datenmodell & Graph-Struktur

### Grundlegende Knotentypen (Mermaid-Diagramm)
```mermaid
graph LR
    A[Nutrient Node
(z.B. Vitamin C)] --- B[Content Node
(Enthält Messwerte + Quelle)] --- C[Food Node
(z.B. Apfel)]
    D[User Node
(Benutzer)]
    style A fill:#f9f,stroke:#333
    style B fill:#ff9,stroke:#333
    style C fill:#9f9,stroke:#333
    style D fill:#aaf,stroke:#333
    D -- CREATED_BY, UPDATED_BY, VALIDATED_BY --> A
    D -- CREATED_BY, UPDATED_BY, VALIDATED_BY --> B
    D --- C
```

### Neo4j Datenstruktur (Cypher Beispiele)
```cypher
// Nährstoff-Knoten
CREATE (v:Nutrient {
    id: 'vitamin-c',
    name: 'Vitamin C',
    type: 'vitamin',
    description: 'Ascorbinsäure...',
    created_at: timestamp(),
    version: 'current'  // Version tracking handled by system
})

// Lebensmittel-Knoten
CREATE (f:Food {
    id: 'apple',
    name: 'Apfel',
    type: 'fruit',
    created_at: timestamp(),
    version: 'current'  // Version tracking handled by system
})

// Zwischenknoten für Nährstoffgehalt (mit Referenzierung via @Tab_Vit_C_v7.csv und @Nahrungsmittel_Database2_real.csv)
CREATE (c:Content {
    id: 'apple-vitc-content',
    amount: 4.6,
    unit: 'mg/100g',
    source: 'USDA Database; Perplexity Search',
    measured_at: '2023-01-01',
    confidence: 0.95,
    created_at: timestamp(),
    version: 'current',  // Version tracking handled by system
    ai_generated: false,
    ai_model: null,
    validation_status: 'draft'
})

// Benutzer-Knoten using a unified identifier
CREATE (u:User {
    id: 'user123',  // Unified identifier field
    username: 'johndoe',
    email: 'john.doe@example.com',
    role: 'admin',
    created_at: timestamp()
})

// Beziehungen
CREATE (f)-[:HAS_NUTRIENT]->(c)-[:REFERS_TO]->(v)
CREATE (u)-[:CREATED_BY]->(v)
CREATE (u)-[:UPDATED_BY]->(c)
CREATE (u)-[:VALIDATED_BY]->(c)
```

### Typescript Interfaces (JSON Schema Contracts)
```typescript
interface BaseNode {
  id: string;
  created_at: Date;
  updated_at: Date;
  version: string;
  created_by: string;
}

interface NutrientNode extends BaseNode {
  type: 'vitamin' | 'mineral' | 'trace_element';
  name: string;
  description: string;
  scientific_name?: string;
}

interface FoodNode extends BaseNode {
  type: 'fruit' | 'vegetable' | 'meat' | 'dairy' | 'grain';
  name: string;
  description: string;
}

interface ContentNode extends BaseNode {
  amount: number;
  unit: string;
  source: string;
  measured_at: Date;
  confidence: number;
  flags?: string[];
  notes?: string;
  ai_generated: boolean;
  ai_model: string | null;
  validation_status: 'draft' | 'pending_review' | 'approved' | 'rejected' | 'needs_revision';
}

interface UserNode extends BaseNode {
  username: string;
  email: string;
  password_hash?: string;
  role: 'admin' | 'editor' | 'reviewer';
}
```

### 3.1 Hierarchical Node Modeling and Subnodes

In the Vitalyst Knowledge Graph, data is not stored as a single flat structure within each node. Instead, we use a hierarchical modeling approach that modularizes data into primary nodes and their associated subnodes. This design choice has several advantages:

- **Modularity and Extendability:** Detailed attributes (such as nutritional values, environmental metrics, consumer statistics) are stored in subordinate nodes. For instance, a Food node may have subnodes like *EnvironmentalMetrics*, *NutritionalDetails*, and *ConsumerData* that hold specific fields. This allows us to document all data sources for each attribute separately and update them as new columns or data types are added.

- **Simplified Data Sourcing:** With subnodes, it becomes much easier to track and document the source of each data segment (e.g., "Quelle fuer Typ", "CO2- footprint source", or historical raw data). This approach also facilitates AI interactions, as an AI module can target a primary node to trigger updates and propagate enriched content into the appropriate subnodes.

- **Seamless Integration and Flexibility:** Although our JSON Schema Definitions in section 4.1 provide a flattened view for API consistency and ease of data validation, the underlying Neo4j implementation organizes this data hierarchically. Each node (Food, Nutrient, etc.) will be linked to one or more detail subnodes via relationships such as HAS_DETAIL. This enables a dynamic data model where updates in one area can easily trigger updates in related subnodes.

- **AI-Powered Propagation:** The system's AI integration is designed to interact with both primary nodes and their subnodes. For example, when a Food node is selected for AI enrichment, the AI can update not only the flat properties but also propagate detailed data into subnodes (such as updating nutritional details or environmental metrics) based on real-time queries.

Overall, this hierarchical design ensures that the system remains highly modular and scalable as new data sources and attributes are introduced. It also enforces clean separation of concerns, allowing each piece of data to have its own source, history, and raw data repository.

### 3.2 Data Model Consistency and Improvements

To ensure clarity and maintainability in our data model, we propose the following improvements:

- **Unified Identifier Fields:** Ensure that all node definitions (e.g., UserNode, NutrientNode, FoodNode, ContentNode) consistently use a single identifier—preferably "id"—for internal identification. Avoid mixing in alternative fields such as "user_id"; any existing discrepancies (e.g., in UserNode) must be updated to align with this unified approach. If an external reference is needed, include a supplemental field that is clearly documented and explicitly mapped to the unified "id". This naming convention should be uniformly reflected across the entire document and codebase.

- **Consistent Timestamp Format:** Although Neo4j uses raw numeric timestamps (via `timestamp()`), all date-time fields such as `created_at` and `updated_at` must be exposed in ISO 8601 string format (e.g., "2023-01-01T12:00:00Z"). The backend should convert timestamps accordingly before serving API responses to maintain a consistent format across the application.

- **Enhanced AI Enrichment Flow:** The AI enrichment process now includes a clearly defined fallback mechanism. If the primary model (e.g., OpenAI) fails due to issues such as rate limiting, the system will automatically switch to an alternative model (e.g., Claude). Any errors (e.g., "Rate limit exceeded") will be propagated to the UI with explicit statuses (like "enrichment_pending" or "enrichment_failed") and accompanied by user-friendly messages explaining the situation and possible next steps.

- **Robust Import Logic with Error Handling:** Functions responsible for merging or creating nodes (such as `merge_food_node`, `merge_nutrient_node`, and `create_content_node`) will incorporate comprehensive error handling and logging. In the event of failures (e.g., conflicts or missing data), these functions must log detailed error messages with timestamps and return explicit error states or exceptions, facilitating easier debugging and monitoring.

- **Clear User Interaction Flows:** The UI/UX is designed to provide a seamless user experience. After editing a node's details, a clearly labeled "Enrich with AI" button will allow users to trigger AI enrichment. Visual indicators, such as status badges, progress spinners, and error banners, will reflect real-time backend state transitions (e.g., draft, pending_review, approved), ensuring that users are always informed about the current status of their actions.

- **Improved Authentication and Role-Based Permissions:** The OAuth-based authentication flow will be expanded to clearly differentiate between internal and public user roles. This includes distinct UI elements and access rights for roles like admin, editor, and reviewer, ensuring that internal users (data curators and experts) have access to detailed editing options and node history, while public users are provided a summarized, read-only view.

## 4. API und Datenimport

### Sample API Endpoints

#### GET /api/v1/foods/{id}
**Request:**
```
GET /api/v1/foods/apple
```

**Response (200 OK):**
```json
{
  "id": "apple",
  "name": "Apfel",
  "type": "fruit",
  "description": "Der Apfel ist ein Obst mit hohem Vitamingehalt...",
  "created_at": "2023-01-01T12:00:00Z",
  "version": "current",
  "created_by": "user123"
}
```

#### POST /api/v1/contents
Creates a new Content Node (e.g., linking Apfel to Vitamin C)

**Request:**
```json
{
  "amount": 4.6,
  "unit": "mg/100g",
  "source": "USDA Database; Perplexity Search",
  "measured_at": "2023-01-01T00:00:00Z",
  "confidence": 0.95
}
```

**Response (201 Created):**
```json
{
  "id": "apple-vitc-content",
  "amount": 4.6,
  "unit": "mg/100g",
  "source": "USDA Database; Perplexity Search",
  "measured_at": "2023-01-01T00:00:00Z",
  "confidence": 0.95,
  "created_at": "2023-01-01T12:30:00Z",
  "version": "current",
  "ai_generated": false,
  "ai_model": null,
  "validation_status": "draft",
  "created_by": "user123"
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "Invalid payload",
  "details": "The 'amount' field must be a positive number."
}
```

#### POST /api/v1/ai/enrich
Triggers AI enrichment for a node

**Request:**
```json
{
  "node_id": "apple-vitc-content",
  "prompt": "Provide updated vitamin C content data for Apfel with source details."
}
```

**Response (200 OK):**
```json
{
  "node_id": "apple-vitc-content",
  "ai_generated": true,
  "ai_model": "LangGraph-Model-1",
  "content_update": "Updated vitamin C content is 4.8 mg/100g, confirmed via Perplexity search.",
  "validation_status": "pending_review"
}
```

**Error (429 Too Many Requests):**
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 30
}
```

### Import-Logik (Python)
```python
def import_food_nutrient_relationship(food_name: str, nutrient_name: str, amount: float, unit: str, source: str):
    # 1. Find or create Food Node
    food_node = merge_food_node(food_name)
    
    # 2. Find or create Nutrient Node
    nutrient_node = merge_nutrient_node(nutrient_name)
    
    # 3. Create Content Node
    content_node = create_content_node(amount, unit, source)
    
    # 4. Create relationships between nodes
    create_relationships(food_node, content_node, nutrient_node)
```

### 4.1 JSON Schema Definitions

This subsection provides rigorous JSON schemas for each core node in the system. The schemas integrate data derived from both @Tab_Vit_C_v7.csv (nutrient details) and @Nahrungsmittel_Database2_real.csv (food and environmental metrics). These comprehensive schemas ensure precise type validation and serve as a definitive contract for API payloads.

### Food Node JSON Schema
This schema includes fields from the food database such as basic food information, environmental metrics, consumption statistics, and detailed nutritional values.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FoodNode",
  "type": "object",
  "properties": {
    "id": { "type": "string" },
    "name": { "type": "string" },
    "type": { "type": "string" },
    "type_source": { "type": "string" },
    "vitamins": { "type": "string" },
    "protein": { "type": ["number", "string"] },
    "protein_source": { "type": "string" },
    "minerals": { "type": "string" },
    "minerals_source": { "type": "string" },
    "regional_availability": { "type": "string" },
    "regional_availability_source": { "type": "string" },
    "regional_availability_history": { "type": "string" },
    "regional_availability_raw": { "type": "string" },
    
    "CO2_footprint_jan": { "type": ["number", "string"] },
    "CO2_footprint_jan_source": { "type": "string" },
    "CO2_footprint_jan_history": { "type": "string" },
    "CO2_footprint_jan_raw": { "type": "string" },
    
    "water_consumption": { "type": ["number", "string"] },
    "water_consumption_source": { "type": "string" },
    "water_consumption_history": { "type": "string" },
    "water_consumption_raw": { "type": "string" },
    
    "land_use": { "type": ["number", "string"] },
    "land_use_source": { "type": "string" },
    "land_use_history": { "type": "string" },
    "land_use_raw": { "type": "string" },
    
    "CO2_footprint": { "type": ["number", "string"] },
    "CO2_footprint_source": { "type": "string" },
    "CO2_footprint_history": { "type": "string" },
    "CO2_footprint_raw": { "type": "string" },

    "biodiversity_impact": { "type": ["number", "string"] },
    "biodiversity_impact_source": { "type": "string" },
    "biodiversity_impact_history": { "type": "string" },
    "biodiversity_impact_raw": { "type": "string" },

    "sustainability_certifications": { "type": "string" },
    "sustainability_certifications_source": { "type": "string" },
    "sustainability_certifications_history": { "type": "string" },
    "sustainability_certifications_raw": { "type": "string" },

    "average_consumption": { "type": ["number", "string"] },
    "average_consumption_source": { "type": "string" },
    "average_consumption_history": { "type": "string" },
    "average_consumption_raw": { "type": "string" },

    "popular_preparations": { "type": "string" },
    "popular_preparations_source": { "type": "string" },
    "popular_preparations_history": { "type": "string" },
    "popular_preparations_raw": { "type": "string" },

    "main_consumers": { "type": "string" },
    "main_consumers_source": { "type": "string" },
    "main_consumers_history": { "type": "string" },
    "main_consumers_raw": { "type": "string" },

    "consumption_trends": { "type": "string" },
    "consumption_trends_source": { "type": "string" },
    "consumption_trends_history": { "type": "string" },
    "consumption_trends_raw": { "type": "string" },

    "type_history": { "type": "string" },
    "type_raw": { "type": "string" },
    "typical_diet": { "type": "string" },
    "typical_diet_source": { "type": "string" },
    "typical_diet_history": { "type": "string" },
    "typical_diet_raw": { "type": "string" },

    "processing_degree": { "type": "string" },
    "processing_degree_source": { "type": "string" },
    "processing_degree_history": { "type": "string" },
    "processing_degree_raw": { "type": "string" },

    "typical_cooking_method": { "type": "string" },
    "typical_cooking_method_source": { "type": "string" },
    "typical_cooking_method_history": { "type": "string" },
    "typical_cooking_method_raw": { "type": "string" },

    "shelf_life": { "type": "string" },
    "shelf_life_source": { "type": "string" },
    "shelf_life_history": { "type": "string" },
    "shelf_life_raw": { "type": "string" },

    "price_per_100g": { "type": ["number", "string"] },
    "price_per_100g_source": { "type": "string" },
    "price_per_100g_history": { "type": "string" },
    "price_per_100g_raw": { "type": "string" },

    "nutrition": {
      "type": "object",
      "properties": {
        "calcium": { "type": ["number", "string"] },
        "calcium_source": { "type": "string" },
        "calcium_history": { "type": "string" },
        "calcium_raw": { "type": "string" },
        
        "iron": { "type": ["number", "string"] },
        "iron_source": { "type": "string" },
        "iron_history": { "type": "string" },
        "iron_raw": { "type": "string" },
        
        "magnesium": { "type": ["number", "string"] },
        "magnesium_source": { "type": "string" },
        "magnesium_history": { "type": "string" },
        "magnesium_raw": { "type": "string" },
        
        "phosphorus": { "type": ["number", "string"] },
        "phosphorus_source": { "type": "string" },
        "phosphorus_history": { "type": "string" },
        "phosphorus_raw": { "type": "string" },
        
        "potassium": { "type": ["number", "string"] },
        "potassium_source": { "type": "string" },
        "potassium_history": { "type": "string" },
        "potassium_raw": { "type": "string" },
        
        "sodium": { "type": ["number", "string"] },
        "sodium_source": { "type": "string" },
        "sodium_history": { "type": "string" },
        "sodium_raw": { "type": "string" },
        
        "zinc": { "type": ["number", "string"] },
        "zinc_source": { "type": "string" },
        "zinc_history": { "type": "string" },
        "zinc_raw": { "type": "string" },
        
        "copper": { "type": ["number", "string"] },
        "copper_source": { "type": "string" },
        "copper_history": { "type": "string" },
        "copper_raw": { "type": "string" },
        
        "manganese": { "type": ["number", "string"] },
        "manganese_source": { "type": "string" },
        "manganese_history": { "type": "string" },
        "manganese_raw": { "type": "string" },
        
        "selenium": { "type": ["number", "string"] },
        "selenium_source": { "type": "string" },
        "selenium_history": { "type": "string" },
        "selenium_raw": { "type": "string" },
        
        "fluoride": { "type": ["number", "string"] },
        "fluoride_source": { "type": "string" },
        "fluoride_history": { "type": "string" },
        "fluoride_raw": { "type": "string" },
        
        "chloride": { "type": ["number", "string"] },
        "chloride_source": { "type": "string" },
        "chloride_history": { "type": "string" },
        "chloride_raw": { "type": "string" },
        
        "chromium": { "type": ["number", "string"] },
        "chromium_source": { "type": "string" },
        "chromium_history": { "type": "string" },
        "chromium_raw": { "type": "string" },
        
        "molybdenum": { "type": ["number", "string"] },
        "molybdenum_source": { "type": "string" },
        "molybdenum_history": { "type": "string" },
        "molybdenum_raw": { "type": "string" },
        
        "vitamin_a": { "type": ["number", "string"] },
        "vitamin_a_source": { "type": "string" },
        "vitamin_a_history": { "type": "string" },
        "vitamin_a_raw": { "type": "string" },
        
        "vitamin_d": { "type": ["number", "string"] },
        "vitamin_d_source": { "type": "string" },
        "vitamin_d_history": { "type": "string" },
        "vitamin_d_raw": { "type": "string" },
        
        "vitamin_e": { "type": ["number", "string"] },
        "vitamin_e_source": { "type": "string" },
        "vitamin_e_history": { "type": "string" },
        "vitamin_e_raw": { "type": "string" },
        
        "vitamin_k": { "type": ["number", "string"] },
        "vitamin_k_source": { "type": "string" },
        "vitamin_k_history": { "type": "string" },
        "vitamin_k_raw": { "type": "string" },
        
        "vitamin_c": { "type": ["number", "string"] },
        "vitamin_c_source": { "type": "string" },
        "vitamin_c_history": { "type": "string" },
        "vitamin_c_raw": { "type": "string" },
        
        "thiamin": { "type": ["number", "string"] },
        "thiamin_source": { "type": "string" },
        "thiamin_history": { "type": "string" },
        "thiamin_raw": { "type": "string" },
        
        "riboflavin": { "type": ["number", "string"] },
        "riboflavin_source": { "type": "string" },
        "riboflavin_history": { "type": "string" },
        "riboflavin_raw": { "type": "string" },
        
        "niacin": { "type": ["number", "string"] },
        "niacin_source": { "type": "string" },
        "niacin_history": { "type": "string" },
        "niacin_raw": { "type": "string" },
        
        "vitamin_b6": { "type": ["number", "string"] },
        "vitamin_b6_source": { "type": "string" },
        "vitamin_b6_history": { "type": "string" },
        "vitamin_b6_raw": { "type": "string" },
        
        "folate": { "type": ["number", "string"] },
        "folate_source": { "type": "string" },
        "folate_history": { "type": "string" },
        "folate_raw": { "type": "string" },
        
        "vitamin_b12": { "type": ["number", "string"] },
        "vitamin_b12_source": { "type": "string" },
        "vitamin_b12_history": { "type": "string" },
        "vitamin_b12_raw": { "type": "string" },
        
        "pantothenic_acid": { "type": ["number", "string"] },
        "pantothenic_acid_source": { "type": "string" },
        "pantothenic_acid_history": { "type": "string" },
        "pantothenic_acid_raw": { "type": "string" },
        
        "biotin": { "type": ["number", "string"] },
        "biotin_source": { "type": "string" },
        "biotin_history": { "type": "string" },
        "biotin_raw": { "type": "string" }
      },
      "required": []
    }
  },
  "required": ["id", "name", "type"]
}
```

#### Nutrient Node JSON Schema
This schema defines nutrient details based on @Tab_Vit_C_v7.csv and may include additional information such as recommended intake and deficiency symptoms.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "NutrientNode",
  "type": "object",
  "properties": {
    "id": { "type": "string" },
    "name": { "type": "string" },
    "type": { "type": "string", "enum": ["vitamin", "mineral", "trace_element"] },
    "description": { "type": "string" },
    "vitID": { "type": "string" },
    "level1_description": { "type": "string" },
    "level2_description": { "type": "string" },
    "level3_description": { "type": "string" },
    "vitamin_sub_name": { "type": "string" },
    "advantages": { "type": "string" },
    "disadvantages": { "type": "string" },
    "chemical_formula": { "type": "string" },
    "pubchem": { "type": "string" },
    "smiles": { "type": "string" },
    "recommended_daily_intake": { "type": ["number", "string"] },
    "deficiency_symptoms": { "type": "string" },
    "toxicity_levels": { "type": "string" }
  },
  "required": ["id", "name", "type", "description"]
}
```

#### Content Node JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ContentNode",
  "type": "object",
  "properties": {
    "id": { "type": "string" },
    "amount": { "type": "number" },
    "unit": { "type": "string" },
    "source": { "type": "string", "description": "Source information, e.g., 'USDA Database; Perplexity Search'" },
    "measured_at": { "type": "string", "format": "date-time" },
    "confidence": { "type": "number" },
    "ai_generated": { "type": "boolean" },
    "ai_model": { "type": ["string", "null"] },
    "validation_status": { "type": "string", "enum": ["draft", "pending_review", "approved", "rejected", "needs_revision"] },
    "flags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "notes": { "type": "string" }
  },
  "required": ["id", "amount", "unit", "source", "measured_at", "confidence", "validation_status"]
}
```

#### User Node JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "UserNode",
  "type": "object",
  "properties": {
    "id": { "type": "string" },
    "username": { "type": "string" },
    "email": { "type": "string", "format": "email" },
    "role": { "type": "string", "enum": ["admin", "editor", "reviewer"] }
  },
  "required": ["id", "username", "email", "role"]
}
```

## 5. AI-Integration

### Models & Configuration
- **Models:** OpenAI, Claude
- **API Keys:** Referenced from /keys directory as per environment variable configuration
- **Prompt Template Example:**
  > "Query: Provide updated nutrient content for {food_name} regarding {nutrient_name}. Include source details and validation notes."
- **Fallback Strategy:** Bei Scheitern des primären Modells (z.B. OpenAI) wird automatisch auf ein alternatives Modell (z.B. Claude) umgeschaltet, mit mechanischen Rückoff-Strategien und detaillierten Statusmeldungen im UI.

### Gherkin Scenario for AI Enrichment
```gherkin
Feature: AI Enrichment of Nutrient Content
  As an internal user, I want to enrich a nutrient node using AI, so that the node's details are automatically updated.

  Scenario: Successful AI Enrichment
    Given the food node "apple" exists and is linked to a content node "apple-vitc-content"
    When I send a POST request to "/api/v1/ai/enrich" with node_id "apple-vitc-content" and an appropriate prompt
    Then the response status should be 200 OK
    And the response should indicate "ai_generated": true and an updated content message
```

### Mermaid Diagram: AI Workflow
```mermaid
flowchart TD
    A[User clicks on node (Apfel)] --> B[UI triggers AI enrichment request]
    B --> C[FastAPI endpoint /api/v1/ai/enrich]
    C --> D[LangChain sends prompt to AI Model]
    D --> E[AI Model returns updated content]
    E --> F[FastAPI updates node and sets status to 'pending_review']
    F --> G[UI displays updated content and prompts HITL validation]
```

## 6. Datenquellen und Integrations-Pipeline

- **Excel-Vorlage (@Tab_Vit_C_v7.csv):** Detaillierte Informationen zu Vitamin C (Beschreibung, Dosierung, chemische Formel, biologische Rollen).
- **Nahrungsmitteldaten (@Nahrungsmittel_Database2_real.csv):** Umfasst Nahrungsmittel-Informationen (Nährstoffprofile, Umweltkennzahlen, Konsumdaten).
- **Integrationsstrategie:** Import-Skripte mappen relevante CSV-Spalten auf entsprechende Knoten (Food, Nutrient, Content). Beispiel: Verknüpfung von "Apfel" (Food) mit "Vitamin C" (Nutrient) über einen Content Node, der Messwerte, Quelle (inkl. Perplexity-Suche) und Validierung (HITL) speichert.

## 7. Entwicklungsplan & Testgetriebene Entwicklung (TDD)
1. **Planung:** Detaillierte Anforderungsanalyse, Infrastruktur- und Architekturentwurf.
2. **Datenbank-Setup:** Installation und Konfiguration von Neo4j; Implementierung grundlegender Knotenmodelle.
3. **Backend-Entwicklung:** Implementierung der FastAPI-Endpunkte mit klar definierten JSON-Schemas und Fehlerbehandlungsmiddleware.
4. **Frontend-Entwicklung:** Aufbau des React/Remix-Frontends inklusive React Flow für Graph-Visualisierung.
5. **AI-Integration:** Integration von LangChain, Einrichtung von API-Keys (aus /keys) und Prompt-Templates.
6. **Testing:** Umsetzung von Unit-, Integrations- und Regressionstests (pytest für Backend, Vitest für Frontend).
7. **Deployment & Monitoring:** Einrichtung eines CI/CD-Prozesses (Docker, GitHub Actions) und Monitoring via Prometheus & Grafana.

## 8. Rollen, Workflows & Validierung

### Benutzerrollen und Berechtigungen
```mermaid
graph LR
    A[Rollen] --> B[Administrator]
    A --> C[Medizinischer Experte]
    A --> D[Datenkurator]
    A --> E[Reviewer]

    B --> B1[Voller Zugriff auf alle Funktionen]
    C --> C1[Validierung und Freigabe]
    D --> D1[Datenpflege & -aktualisierung]
    E --> E1[Review und Kommentierung]
```

### Validierungs-Workflow (State Diagram)
```mermaid
stateDiagram-v2
    [*] --> Entwurf
    Entwurf --> draft
    draft --> pending_review
    pending_review --> approved
    pending_review --> rejected
    pending_review --> needs_revision
    approved --> Validiert
    Validiert --> Veröffentlicht
    Veröffentlicht --> Update_Needed
    Update_Needed --> Entwurf
    Entwurf --> Flagged
    Flagged --> Entwurf
```

### Validierungs-Workflow und Fehlerbehandlung
- **Validierungsstatus:** Knoten wechseln durch die Zustände: `draft`, `pending_review`, `approved`, `rejected`, `needs_revision`. Diese Änderungen werden in Echtzeit in der UI durch Badges mit unterschiedlichen Farben dargestellt.
- **Fehlermeldungen:** Bei Validierungsfehlern oder Problemen (z. B. Fehler bei API-Aufrufen) werden die betroffenen Felder in der Detailansicht mit roten Rahmen und Tooltips hervorgehoben. Zusätzlich werden modale Dialoge oder Toast-Benachrichtigungen angezeigt, um dem Nutzer sofortige Rückmeldung zu geben.
- **Daten-Logging:** Fehler und Zustandsänderungen werden detailliert mit Zeitstempeln und Kontextinformationen geloggt, um eine lückenlose Nachverfolgung und Fehleruntersuchung zu ermöglichen.

### Authentifizierungsfluss (OAuth) und UI-Unterscheidung
- **OAuth Integration:** Die Anmeldung erfolgt via OAuth (z. B. Auth0), wobei die externen Rollen auf interne Berechtigungen abgebildet werden. 
- **Dashboard Differenzierung:**
  - **Interne Nutzer:** Sehen ein umfassendes Dashboard mit editierbaren Detail-Panels, AI-Anreicherungs-Buttons und einer Validierungs-Queue.
  - **Öffentliche Nutzer:** Erhalten eine vereinfachte Visualisierung mit eingeschränktem Zugriff auf detaillierte Daten.

## 9. Frameworks, Deployment, Sicherheit & Monitoring

### Directory Structure & Project Setup
```
/Vitalyst
├── backend
│   ├── app.py
│   │   ├── endpoints.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── config
│   │   └── config.py
│   ├── tests
│   │   ├── test_api.py
│   │   └── test_models.py
│   ├── Dockerfile.backend
│   └── requirements.txt
├── frontend
│   ├── package.json
│   ├── remix.config.js
│   ├── public
│   └── src
│       ├── components
│       │   └── NodeEditor.jsx
│       ├── pages
│       │   └── index.jsx
│       ├── styles
│       └── tests
│           └── NodeEditor.test.jsx
├── keys
│   ├── openai_api_key.txt
│   ├── anthropic_api_key.txt
│   └── perplexity_api_key.txt
├── docker-compose.yml
├── .env
└── README.md
```

### Sample Dockerfile for Backend (Dockerfile.backend)
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Sample docker-compose.yml
```yaml
version: 'latest'  # Use latest supported version
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=bolt://neo4j:password@neo4j:7687
      - OPENAI_API_KEY_FILE=/keys/openai_api_key.txt
      - ANTHROPIC_API_KEY_FILE=/keys/anthropic_api_key.txt
      - PERPLEXITY_API_KEY_FILE=/keys/perplexity_api_key.txt
    volumes:
      - ./keys:/keys
  neo4j:
    image: neo4j:latest
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/password
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
```

## Error Handling & Performance Monitoring
- **Logging:** JSON-formatierte Logs mit Zeitstempeln, URL, Statuscodes und Fehlerdetails.
- **Prometheus & Grafana:** Überwachung der Request-Rate, Latenz, Fehlerquoten, CPU- und Speicherauslastung.
- **Performance Monitoring:** Regelmäßige Messung von API-Latenzen und Systemressourcen, um Skalierbarkeit zu gewährleisten.

### Configuration Details (.env file)
```
# Database Connection
DATABASE_URL=bolt://neo4j:password@localhost:7687

# OAuth Settings (example using Auth0)
OAUTH_DOMAIN=your-auth0-domain
OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-client-secret

# AI API Keys (files mounted from keys folder)
OPENAI_API_KEY_FILE=/keys/openai_api_key.txt
ANTHROPIC_API_KEY_FILE=/keys/anthropic_api_key.txt
PERPLEXITY_API_KEY_FILE=/keys/perplexity_api_key.txt

# Ports
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

### Dependencies
#### Backend (requirements.txt)
```python
# API Framework
fastapi  # Latest stable version
uvicorn  # Latest stable version
python-dotenv  # Latest stable version
pydantic  # Latest stable version
starlette  # Latest stable version
fastapi-cache2  # Latest stable version
orjson  # Latest stable version
asgi-lifespan  # Latest stable version

# Database
neo4j  # Latest stable version
redis  # Latest stable version
motor  # Latest stable version
asyncpg  # Latest stable version
alembic  # Latest stable version
sqlalchemy  # Latest stable version

# AI and Machine Learning
langchain  # Latest stable version
langchain-openai  # Latest stable version
langchain-anthropic  # Latest stable version
langchain-community  # Latest stable version
openai  # Latest stable version
anthropic  # Latest stable version
perplexity-python  # Latest stable version
numpy  # Latest stable version
scikit-learn  # Latest stable version
sentence-transformers  # Latest stable version
torch  # Latest stable version
transformers  # Latest stable version

# Testing
pytest  # Latest stable version
pytest-cov  # Latest stable version
pytest-asyncio  # Latest stable version
pytest-mock  # Latest stable version
httpx  # Latest stable version
pytest-env  # Latest stable version
coverage  # Latest stable version
pytest-benchmark  # Latest stable version
locust  # Latest stable version
faker  # Latest stable version
hypothesis  # Latest stable version

# Security
python-jose  # Latest stable version
passlib  # Latest stable version
bcrypt  # Latest stable version
cryptography  # Latest stable version
python-multipart  # Latest stable version
pyjwt  # Latest stable version
authlib  # Latest stable version
itsdangerous  # Latest stable version
oauthlib  # Latest stable version
python-keycloak  # Latest stable version

# Monitoring and Logging
prometheus-client  # Latest stable version
python-json-logger  # Latest stable version
opentelemetry-api  # Latest stable version
opentelemetry-sdk  # Latest stable version
opentelemetry-instrumentation-fastapi  # Latest stable version
opentelemetry-instrumentation-redis  # Latest stable version
opentelemetry-instrumentation-neo4j  # Latest stable version
opentelemetry-instrumentation-requests  # Latest stable version
opentelemetry-instrumentation-logging  # Latest stable version
elastic-apm  # Latest stable version
sentry-sdk  # Latest stable version
ddtrace  # Latest stable version

# Utilities
pandas  # Latest stable version
email-validator  # Latest stable version
aiohttp  # Latest stable version
python-dateutil  # Latest stable version
pytz  # Latest stable version
ujson  # Latest stable version
pydantic-extra-types  # Latest stable version
rich  # Latest stable version
structlog  # Latest stable version
tenacity  # Latest stable version
cachetools  # Latest stable version
python-slugify  # Latest stable version
pyyaml  # Latest stable version

# Development Tools
black  # Latest stable version
flake8  # Latest stable version
mypy  # Latest stable version
isort  # Latest stable version
autoflake  # Latest stable version
pylint  # Latest stable version
pre-commit  # Latest stable version
bandit  # Latest stable version
safety  # Latest stable version
ruff  # Latest stable version
pytype  # Latest stable version
vulture  # Latest stable version
```

#### Frontend (package.json snippet)
```json
{
  "dependencies": {
    "react": "latest",
    "react-dom": "latest",
    "remix": "latest",
    "react-flow-renderer": "latest"
  },
  "devDependencies": {
    "vitest": "latest"
  }
}
```

### Error Handling & Logging

#### FastAPI Error Handling Middleware
```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("uvicorn.error")

async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"Error: {exc.detail} for request: {request.url}")
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

app = FastAPI()
app.add_exception_handler(HTTPException, http_exception_handler)
```

#### Logging & Metrics
- **Logging:** JSON-formatted logs with fields: timestamp, request URL, status code, error details.
- **Prometheus Metrics:** Track request count per endpoint, request latency, error rate (4xx/5xx), CPU and memory usage.
- **Grafana Dashboards:** Display collected Prometheus metrics for system health and performance.

## 10. Fazit
Dieses Blueprint liefert einen detaillierten, gut strukturierten und vollständigen Plan für den Aufbau einer skalierbaren, modularen und testgetriebenen Wissensdatenbank für Vitamine und Spurenelemente. Es integriert klare API-Spezifikationen (mit Beispiel-Payloads und JSON-Schemas), eine empfohlene Verzeichnisstruktur, Docker-Setup, Konfigurationsdetails, Fehlerbehandlung, Logging sowie AI-Integrationsspezifika und Teststrategien. Damit bietet es einen präzisen Implementierungsleitfaden für einen AI-Coder.

## 11. User Interface and Experience (UI/UX & CX)

### Overall User Journey & Enhanced Transitions
- **Authentifizierung & Dashboard:** Erfolgreiche Anmeldung via OAuth leitet Nutzer zu rollenspezifischen Dashboards weiter. Interne Nutzer erhalten ein Dashboard mit erweiterten Bearbeitungsfunktionen, während öffentliche Nutzer eine vereinfachte Visualisierung bekommen.
- **Detail Panel & UI-Transitions:** Bei Auswahl eines Knotens im interaktiven React Flow öffnet sich ein "Detail Panel" mit sanften Slide-In -Animationen, das alle editierbaren Attribute (basierend auf dem JSON-Schema) anzeigt. Übergänge sind mit klaren visuellen Cues versehen, die angeben, wann ein Bearbeitungsmodus aktiv ist.
- **Feedback und Benachrichtigungen:** Änderungen, API-Antworten, Fehler oder Statusupdates werden sofort durch Statusbadges, Fortschrittsanzeiger, Toast-Nachrichten und modale Dialoge kommuniziert.

### Detailed Validation and Error Handling States
- **Validierungsfluss:** Knoten durchlaufen Zustände von `draft` zu `pending_review`, `approved`, `rejected` oder `needs_revision`. Diese Übergänge werden visuell (z. B. farbcodierte Badges) und protokolliert dargestellt.
- **Inline Fehleranzeige:** Bei Validierungsfehlern werden betroffene Felder rot markiert und mit erklärenden Tooltips versehen. Ein modaler Dialog kann zusätzliche Details anzeigen, sodass Nutzer direkt Korrekturen vornehmen können.
- **Logging und Überwachung:** Jeder Fehler, jede Zustandsänderung und API-Antwort wird mit Zeitstempeln und Kontextinformationen geloggt, um eine lückenlose Nachverfolgung und Fehleruntersuchung zu ermöglichen.

### Role-Based Permissions and Authentication Flow
- **OAuth und Rollenzuordnung:** Über OAuth (z.B. Auth0) authentifizieren sich alle Nutzer. Externe Rollen werden auf interne Berechtigungen abgebildet. 
- **UI-Spezifische Elemente je Rolle:**
  - **Interne Nutzer (Admin, Datenkuratoren, Experten, Reviewer):** Haben Zugriff auf editierbare Detail-Panels, erweiterten Such-/Filterfunktionen und eine Validierungs-Queue.
  - **Öffentliche Nutzer:** Erhalten eine lesebasierte Ansicht mit interaktiver Graphvisualisierung.
- **Flussdiagramm der Authentifizierung:**
```mermaid
flowchart LR
    A[Benutzer login via OAuth] --> B[Externe Rollenabruf]
    B --> C{Interne Rolle?}
    C -- Ja --> D[Interner Dashboard-Zugang (Editoren, Validierung)]
    C -- Nein --> E[Öffentliches Dashboard (Read-Only)]
```

### Integration and Testing Artifacts
- **Automatisierte Tests:** Unit-, Integrations- und End-to-End-Tests decken die Kernprozesse (z. B. Knotenauswahl, AI-Anreicherung, Fehlerbehandlung) ab.
- **Beispiel-Gherkin-Szenario:**
```gherkin
Feature: AI Enrichment of Nutrient Content
  As an internal user,
  I want to enrich a nutrient node using AI,
  So that its details are updated seamlessly.

  Scenario: Successful AI Enrichment
    Given a nutrient node exists with status "draft"
    When I select the node and click "Enrich with AI"
    Then a progress spinner appears
    And the node status changes to "pending_review"
    And a success notification is displayed
```
- **Regression & Performance Tests:** Regelmäßige Tests stellen sicher, dass neue Features bestehende Funktionen nicht beeinträchtigen. Kennzahlen wie Latenz, Durchsatz und Ressourcennutzung werden kontinuierlich überwacht.

### Additional Architectural and Scalability Considerations
- **Modulare Erweiterbarkeit:** Dank des hierarchischen Datenmodells können neue untergeordnete Knoten und zusätzliche Datenquellen integriert werden, ohne dass bestehende Strukturen verändert werden müssen.
- **Performance Monitoring:** Dashboards überwachen API-Latenzen, Fehlerquoten sowie CPU- und Speichernutzung, um Skalierbarkeit und Stabilität sicherzustellen.
- **Zukunftsausblick:** Das System ist darauf ausgelegt, zusätzliche AI-Modelle und externe Datenquellen schnell zu integrieren. Versionierung, Änderungsprotokolle und automatisierte Update-Pipelines unterstützen diesen Prozess.

### Conclusion of UI/UX & CX
Durch detaillierte UI-Transitions, robuste Fehlerbehandlung und klar definierte Rollenzugänge bietet der Vitalyst Knowledge Graph ein intuitives und zuverlässiges Nutzererlebnis. Diese Verbesserungen stärken nicht nur die Usability, sondern sorgen auch für eine lückenlose Nachvollziehbarkeit und Skalierbarkeit der Anwendung.

---

*This document serves as a living blueprint that will continuously evolve to incorporate new insights and improvements in both system architecture and user experience design.*

Upon successful login via OAuth, users are directed to a role-specific dashboard. **Internal users (administrators, data curators, medical experts, reviewers) are presented with a comprehensive dashboard** that includes graph visualization, node editing capabilities, AI enrichment triggers, and validation queues. **Public users, on the other hand, access a simplified dashboard** focused on graph exploration and read-only node information, ensuring a clear distinction in user routes and access rights from the outset. The OAuth integration ensures that user roles defined in the authentication provider (e.g., Auth0) are mapped to permissions within the Vitalyst application, controlling access to different UI features and API endpoints.

Let's detail the interaction flow for internal users:
    1. **Node Selection & Editing:** When an internal user selects a node in the React Flow graph, a **"Detail Panel" slides in**, presenting the node's attributes in an editable form. This panel includes fields corresponding to the node's JSON schema.
    2. **Initiating AI Enrichment:** Within the "Detail Panel," after editing or upon initial node view, a prominent **"Enrich with AI" button** is available. Clicking this button triggers the AI enrichment process for the selected node.
    3. **Visual Status Indicators:**
        - **Validation Status Badge:** Each node in the graph and in the "Detail Panel" displays a **status badge** (e.g., color-coded circle or label) indicating its current `validation_status` (draft, pending_review, approved, rejected, needs_revision). This badge is updated in real-time based on backend state changes.
        - **Progress Spinner:** When AI enrichment is triggered, a **spinner icon** appears next to the "Enrich with AI" button and potentially on the node itself, indicating that the AI process is running.
        - **Success/Error Notifications:** Upon completion of AI enrichment or any backend operation (like saving edits), **brief, non-intrusive success or error notifications** (e.g., toast messages) appear to provide immediate feedback.
        - **Error Highlighting in Detail Panel:** If validation fails or data is invalid upon saving, the specific fields in the "Detail Panel" with errors are **highlighted (e.g., red border, error message tooltip)**, guiding the user to correct the issues.
    4. **HITL Validation Flow:** For nodes in `pending_review` status (often after AI enrichment), they appear in a **"Validation Queue"** on the internal user dashboard. Reviewers can select nodes from this queue, examine the proposed changes (often highlighted in the "Detail Panel"), and then use **"Approve" or "Reject" buttons** within the panel to update the `validation_status` and move the node through the workflow (as depicted in the State Diagram in section 8).

   - *Internal Workflow:* Experts can click on a node to open a detail editor (the **"Detail Panel"**). From the editor, they can:
        - **Edit Node Attributes:** Modify fields directly within the "Detail Panel," with **real-time validation** and error highlighting.
        - **Trigger AI Enrichment:** Click the **"Enrich with AI" button** to initiate AI-driven content updates, observing the **progress spinner** and subsequent status updates.
        - **Review Validation Queue:** Access a dedicated **"Validation Queue"** to review nodes in `pending_review` status, using **"Approve" and "Reject" buttons** to manage the data curation workflow. The **status badge** on each node and in the "Detail Panel" reflects the current stage in the validation state diagram (Entwurf -> pending_review -> approved -> Validiert -> Veröffentlicht -> Update_Needed -> Entwurf -> Flagged).
   - *Public Workflow:* Public users can explore the interactive graph, use search and filter functions, and access summarized node details in a **read-only "Information Panel"** (distinct from the "Detail Panel" for internal users). The visualization helps users deeply understand the connections between food items and nutrient data, with a focus on clarity and accessibility.

## Technology Stack

### Backend
- Python (Latest stable version)
- FastAPI (Latest stable version)
- Neo4j (Latest stable version)
- LangChain (Latest stable version)
- Redis (Latest stable version)
- SQLAlchemy (Latest stable version)
- Alembic (Latest stable version)
- OpenTelemetry (Latest stable version)
- Sentry SDK (Latest stable version)
- Prometheus Client (Latest stable version)

### Frontend
- Node.js (Latest LTS version)
- React (Latest stable version)
- Remix (Latest stable version)
- TypeScript (Latest stable version)
- React Flow (Latest stable version)
- TailwindCSS (Latest stable version)
- Vitest (Latest stable version)

### Infrastructure
- Docker (Latest stable version)
- Docker Compose (Latest stable version)
- Kubernetes (Latest stable version)
- Redis (Latest stable version)
- Elasticsearch (Latest stable version)
- Logstash (Latest stable version)
- Kibana (Latest stable version)
- Prometheus (Latest stable version)
- Grafana (Latest stable version)
- Sentry (Latest stable version)