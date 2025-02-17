#!/bin/bash
set -e

# Load environment variables
source "$(dirname "$0")/../../config/${ENVIRONMENT:-development}/.env"

echo "Validating JSON schemas..."

# Check if python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is required but not installed"
    exit 1
fi

# Run schema validation
python3 << 'EOF'
import json
import os
from jsonschema import validate, ValidationError

def validate_schema(schema_path, data_path):
    with open(schema_path) as f:
        schema = json.load(f)

    with open(data_path) as f:
        data = json.load(f)

    try:
        validate(instance=data, schema=schema)
        print(f"✅ {data_path} is valid")
    except ValidationError as e:
        print(f"❌ {data_path} validation failed:")
        print(e)
        return False
    return True

# Validate all schema files
schema_dir = "src/api/v1/schemas"
all_valid = True

for root, _, files in os.walk(schema_dir):
    for file in files:
        if file.endswith(".json"):
            schema_path = os.path.join(root, file)
            data_path = os.path.join("tests/data", file)
            if not validate_schema(schema_path, data_path):
                all_valid = False

exit(0 if all_valid else 1)
EOF

echo "Schema validation completed"
