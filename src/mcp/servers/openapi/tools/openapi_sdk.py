# src/mcp/servers/openapi/tools/openapi_sdk.py
import time
import json
import logging
from typing import Dict, Any

# Import utility functions
from mcp.servers.openapi.utils.openapi_parser import parse_openapi_spec
from mcp.servers.openapi.utils.code_generators.python import generate_python_sdk
from mcp.servers.openapi.utils.code_generators.typescript import generate_typescript_sdk
from mcp.servers.openapi.utils.code_generators.javascript import generate_javascript_sdk
from mcp.servers.openapi.utils.api_client import execute_api_request

def get_openapi_sdk_tool_definition() -> Dict[str, Any]:
    """Get the definition for the OpenAPI SDK tool."""
    return {
        "name": "openapi_sdk",
        "description": "Generate code for an OpenAPI specification and optionally make API requests",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec_source": {
                    "type": "string",
                    "description": "URL to OpenAPI spec or JSON string containing the spec"
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "typescript", "javascript"],
                    "default": "python",
                    "description": "Programming language for the generated code"
                },
                "operation_id": {
                    "type": "string",
                    "description": "Specific operation to generate code for (optional)"
                },
                "execute_request": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to execute the API request"
                },
                "request_params": {
                    "type": "object",
                    "description": "Parameters for the API request (if execute_request is true)"
                }
            },
            "required": ["spec_source"]
        }
    }

async def execute_openapi_sdk_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the OpenAPI SDK tool with the given arguments."""
    try:
        # Extract arguments
        spec_source = args.get("spec_source")
        language = args.get("language", "python")
        operation_id = args.get("operation_id")
        execute_request = args.get("execute_request", False)
        request_params = args.get("request_params", {})
        
        # 1. Parse OpenAPI spec
        logging.info(f"Parsing OpenAPI spec from: {spec_source[:50]}...")
        openapi_spec = await parse_openapi_spec(spec_source)
        
        # 2. Generate SDK code
        logging.info(f"Generating {language} SDK code...")
        if language == "python":
            generated_code = generate_python_sdk(openapi_spec, operation_id)
        elif language == "typescript":
            generated_code = generate_typescript_sdk(openapi_spec, operation_id)
        elif language == "javascript":
            generated_code = generate_javascript_sdk(openapi_spec, operation_id)
        else:
            raise ValueError(f"Unsupported language: {language}")
        
        # 3. Optionally execute request
        response_data = None
        if execute_request:
            logging.info("Executing API request...")
            response_data = await execute_api_request(
                openapi_spec, 
                operation_id,
                request_params
            )
        
        # 4. Format and return results
        content = [
            {
                "type": "text",
                "text": f"SDK generated successfully for {openapi_spec.get('info', {}).get('title', 'API')}"
            },
            {
                "type": "resource",
                "resource": {
                    "uri": f"sdk-code-{int(time.time())}",
                    "mimeType": "text/plain",
                    "text": generated_code
                }
            }
        ]
        
        # Add API response if executed
        if response_data:
            content.append({
                "type": "resource",
                "resource": {
                    "uri": f"api-response-{int(time.time())}",
                    "mimeType": "application/json",
                    "text": json.dumps(response_data, indent=2)
                }
            })
        
        return {
            "content": content,
            "isError": False
        }
    except Exception as e:
        logging.exception("Error in OpenAPI SDK tool")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error generating SDK: {str(e)}"
                }
            ],
            "isError": True
        }