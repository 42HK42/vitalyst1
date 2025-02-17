# API Documentation

## Overview
This document provides comprehensive documentation for the Vitalyst Knowledge Graph API.

## Base URL
- Development: `http://localhost:8000`
- Production: `https://api.vitalyst.42hk42.com`

## Authentication
All API endpoints require authentication using OAuth 2.0. See [Authentication](authentication.md) for details.

## Endpoints

### Node Operations
- [GET /api/v1/nodes](endpoints/nodes.md#get-nodes) - List all nodes
- [POST /api/v1/nodes](endpoints/nodes.md#create-node) - Create a new node
- [GET /api/v1/nodes/{id}](endpoints/nodes.md#get-node) - Get a specific node
- [PUT /api/v1/nodes/{id}](endpoints/nodes.md#update-node) - Update a node
- [DELETE /api/v1/nodes/{id}](endpoints/nodes.md#delete-node) - Delete a node

### Relationship Operations
- [GET /api/v1/relationships](endpoints/relationships.md) - List all relationships
- [POST /api/v1/relationships](endpoints/relationships.md) - Create a relationship
- [DELETE /api/v1/relationships/{id}](endpoints/relationships.md) - Delete a relationship

### AI Operations
- [POST /api/v1/ai/enrich](endpoints/ai.md) - Enrich node with AI
- [POST /api/v1/ai/validate](endpoints/ai.md) - Validate node data

### Search Operations
- [GET /api/v1/search](endpoints/search.md) - Search nodes
- [GET /api/v1/search/vector](endpoints/search.md) - Vector similarity search

## Response Format
All responses follow a standard format:

```json
{
  "status": "success|error",
  "data": {},
  "message": "Optional message",
  "errors": []
}
```

## Rate Limiting
API requests are limited to:
- 100 requests per minute for authenticated users
- 20 requests per minute for unauthenticated users

## Error Codes
See [Error Codes](error-codes.md) for a complete list of error codes and their meanings.
