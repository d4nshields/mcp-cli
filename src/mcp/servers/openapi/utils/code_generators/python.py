# src/mcp/servers/openapi/utils/code_generators/python.py
import logging
import jinja2
from typing import Dict, Any, Optional, List
from mcp.servers.openapi.utils.code_generators.base import CodeGenerator

# Python SDK template
PYTHON_TEMPLATE = """
import requests
import json
from typing import Dict, Any, Optional, List, Union

class {{ api_name }}Client:
    def __init__(self, base_url: str{% if api_key_param %}, api_key: str{% endif %}):
        self.base_url = base_url{% if api_key_param %}
        self.api_key = api_key{% endif %}
        
    {% for operation in operations %}
    def {{ operation.function_name }}(self, {% for param in operation.parameters %}{{ param.name }}: {{ param.type }}{% if not param.required %} = None{% endif %}{% if not loop.last %}, {% endif %}{% endfor %}):
        """
        {{ operation.description }}
        {% for param in operation.parameters %}
        :param {{ param.name }}: {{ param.description }}{% endfor %}
        :return: API response
        """
        url = f"{self.base_url}{{ operation.path }}"
        
        {% if operation.parameters|selectattr("in", "equalto", "path")|list %}
        # Replace path parameters
        {% for param in operation.parameters|selectattr("in", "equalto", "path")|list %}
        url = url.replace("{{ '{' + param.name + '}' }}", str({{ param.name }}))
        {% endfor %}
        {% endif %}
        
        {% if operation.parameters|selectattr("in", "equalto", "query")|list %}
        # Add query parameters
        params = {}
        {% for param in operation.parameters|selectattr("in", "equalto", "query")|list %}
        if {{ param.name }} is not None:
            params["{{ param.original_name }}"] = {{ param.name }}
        {% endfor %}
        {% endif %}
        
        {% if operation.parameters|selectattr("in", "equalto", "header")|list %}
        # Add headers
        headers = {}
        {% for param in operation.parameters|selectattr("in", "equalto", "header")|list %}
        if {{ param.name }} is not None:
            headers["{{ param.original_name }}"] = {{ param.name }}
        {% endfor %}
        {% if api_key_param %}
        headers["Authorization"] = f"Bearer {self.api_key}"
        {% endif %}
        {% endif %}
        
        {% if operation.request_body %}
        # Prepare request body
        json_data = {
            {% for prop_name, prop in operation.request_body.properties.items() %}
            "{{ prop_name }}": {{ prop_name }},
            {% endfor %}
        }
        {% endif %}
        
        # Make the request
        response = requests.{{ operation.method }}(
            url,
            {% if operation.parameters|selectattr("in", "equalto", "query")|list %}params=params,{% endif %}
            {% if operation.parameters|selectattr("in", "equalto", "header")|list %}headers=headers,{% endif %}
            {% if operation.request_body %}json=json_data,{% endif %}
        )
        
        # Handle response
        response.raise_for_status()
        return response.json()
    {% endfor %}

# Usage example:
# client = {{ api_name }}Client("https://api.example.com")
# result = client.{{ operations[0].function_name if operations else "method_name" }}()
"""

class PythonGenerator(CodeGenerator):
    """Generate Python SDK code from OpenAPI spec."""
    
    def generate(self, openapi_spec: Dict[str, Any], operation_id: Optional[str] = None) -> str:
        """Generate Python SDK code for the given OpenAPI spec."""
        logging.info("Generating Python SDK")
        
        # Extract API details
        api_name = openapi_spec.get("info", {}).get("title", "API").replace(" ", "")
        
        # Extract security schemes
        security_schemes = openapi_spec.get("components", {}).get("securitySchemes", {})
        api_key_param = None
        for scheme_name, scheme in security_schemes.items():
            if scheme.get("type") == "apiKey" or scheme.get("type") == "http":
                api_key_param = scheme_name
                break
        
        # Extract operations
        operations = self._extract_operations(openapi_spec, operation_id)
        
        # Render the template
        environment = jinja2.Environment()
        template = environment.from_string(PYTHON_TEMPLATE)
        rendered_code = template.render(
            api_name=api_name,
            operations=operations,
            api_key_param=api_key_param
        )
        
        return rendered_code
    
    def _extract_operations(self, openapi_spec: Dict[str, Any], operation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extract operations from the OpenAPI spec."""
        operations = []
        paths = openapi_spec.get("paths", {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete", "patch"]:
                    continue
                    
                if operation_id and operation.get("operationId") != operation_id:
                    continue
                    
                # Build operation info
                op_info = {
                    "path": path,
                    "method": method,
                    "function_name": operation.get("operationId", f"{method}_{path}").replace("-", "_").replace("/", "_"),
                    "description": operation.get("summary", "") + "\n" + operation.get("description", ""),
                    "parameters": []
                }
                
                # Extract parameters
                for param in operation.get("parameters", []):
                    param_name = param.get("name", "").replace("-", "_")
                    param_info = {
                        "name": param_name,
                        "original_name": param.get("name", ""),
                        "in": param.get("in"),
                        "description": param.get("description", ""),
                        "required": param.get("required", False),
                        "type": "str"  # Default type
                    }
                    
                    # Determine Python type
                    schema = param.get("schema", {})
                    param_info["type"] = self._get_python_type(schema)
                    
                    op_info["parameters"].append(param_info)
                
                # Extract request body if present
                if "requestBody" in operation:
                    content = operation["requestBody"].get("content", {})
                    if "application/json" in content:
                        schema = content["application/json"].get("schema", {})
                        if schema.get("type") == "object":
                            op_info["request_body"] = {
                                "properties": schema.get("properties", {})
                            }
                            
                            # Add request body parameters
                            for prop_name, prop in schema.get("properties", {}).items():
                                prop_type = self._get_python_type(prop)
                                    
                                op_info["parameters"].append({
                                    "name": prop_name,
                                    "original_name": prop_name,
                                    "in": "body",
                                    "description": prop.get("description", ""),
                                    "required": prop_name in schema.get("required", []),
                                    "type": prop_type
                                })
                
                operations.append(op_info)
        
        return operations
    
    def _get_python_type(self, schema: Dict[str, Any]) -> str:
        """Determine the appropriate Python type for a schema."""
        if schema.get("type") == "integer":
            return "int"
        elif schema.get("type") == "number":
            return "float"
        elif schema.get("type") == "boolean":
            return "bool"
        elif schema.get("type") == "array":
            items_type = self._get_python_type(schema.get("items", {}))
            return f"List[{items_type}]"
        elif schema.get("type") == "object":
            return "Dict[str, Any]"
        else:
            return "str"  # Default to string for unknown types

def generate_python_sdk(openapi_spec: Dict[str, Any], operation_id: Optional[str] = None) -> str:
    """Generate Python SDK code from OpenAPI spec."""
    generator = PythonGenerator()
    return generator.generate(openapi_spec, operation_id)