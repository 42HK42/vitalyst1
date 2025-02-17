# API Reference

## Authentication
All API endpoints require authentication unless explicitly marked as public.

### Authentication Headers
```
Authorization: Bearer <jwt_token>
```

## API Endpoints

### Knowledge Graph Operations

#### Query Graph
```http
GET /api/v1/graph/query
Content-Type: application/json
Authorization: Bearer <token>

{
  "query": "string",
  "filters": {},
  "limit": 100
}
```

#### Update Graph
```http
POST /api/v1/graph/update
Content-Type: application/json
Authorization: Bearer <token>

{
  "nodes": [],
  "relationships": []
}
```

### AI Operations

#### Generate Content
```http
POST /api/v1/ai/generate
Content-Type: application/json
Authorization: Bearer <token>

{
  "prompt": "string",
  "parameters": {}
}
```

#### Analyze Content
```http
POST /api/v1/ai/analyze
Content-Type: application/json
Authorization: Bearer <token>

{
  "content": "string",
  "type": "string"
}
```

### User Management

#### User Profile
```http
GET /api/v1/users/profile
Authorization: Bearer <token>
```

#### Update Settings
```http
PUT /api/v1/users/settings
Content-Type: application/json
Authorization: Bearer <token>

{
  "preferences": {}
}
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

### Common Error Codes
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Too Many Requests
- 500: Internal Server Error

## Rate Limiting
- Default: 100 requests per minute
- Bulk Operations: 10 requests per minute
- AI Operations: 20 requests per minute

## Data Types

### Node
```typescript
interface Node {
  id: string;
  type: string;
  properties: Record<string, any>;
  metadata: {
    created: string;
    updated: string;
    version: number;
  };
}
```

### Relationship
```typescript
interface Relationship {
  id: string;
  type: string;
  source: string;
  target: string;
  properties: Record<string, any>;
}
```

## Versioning
API versioning is handled through the URL path:
- Current version: v1
- Beta features: v1-beta
- Legacy support: v0 (deprecated)
