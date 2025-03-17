# src/mcp/servers/openapi/utils/code_generators/typescript.py
import logging
import jinja2
from typing import Dict, Any, Optional, List
from mcp.servers.openapi.utils.code_generators.base import CodeGenerator

# TypeScript SDK template
TYPESCRIPT_TEMPLATE = """
/**
 * TypeScript SDK for {{ api_info.title }}
 * {{ api_info.description }}
 * Version: {{ api_info.version }}
 */

// Types for request and response data
{% for type in types %}
export interface {{ type.name }} {
  {% for prop_name, prop in type.properties.items() %}
  {{ prop_name }}{% if not prop.required %}?{% endif %}: {{ prop.type }};
  {% endfor %}
}

{% endfor %}

export class {{ api_name }}Client {
  private baseUrl: string;
  {% if api_key_param %}private apiKey: string;{% endif %}

  constructor(baseUrl: string{% if api_key_param %}, apiKey: string{% endif %}) {
    this.baseUrl = baseUrl;
    {% if api_key_param %}this.apiKey = apiKey;{% endif %}
  }

  {% for operation in operations %}
  /**
   * {{ operation.description }}
   {% for param in operation.parameters %}
   * @param {{ param.name }} - {{ param.description }}
   {% endfor %}
   * @returns A Promise containing the response data
   */
  public async {{ operation.function_name }}({% for param in operation.parameters %}
    {{ param.name }}{% if not param.required %}?{% endif %}: {{ param.type }}{% if not loop.last %},{% endif %}
    {% endfor %}): Promise<{{ operation.response_type }}> {
    let url = `${this.baseUrl}{{ operation.path }}`;
    
    {% if operation.parameters|selectattr("in", "equalto", "path")|list %}
    // Replace path parameters
    {% for param in operation.parameters|selectattr("in", "equalto", "path")|list %}
    url = url.replace('{{ '{' + param.original_name + '}' }}', String({{ param.name }}));
    {% endfor %}
    {% endif %}
    
    {% if operation.parameters|selectattr("in", "equalto", "query")|list %}
    // Add query parameters
    const queryParams = new URLSearchParams();
    {% for param in operation.parameters|selectattr("in", "equalto", "query")|list %}
    if ({{ param.name }} !== undefined) {
      queryParams.set('{{ param.original_name }}', String({{ param.name }}));
    }
    {% endfor %}
    
    // Append query string if parameters exist
    const queryString = queryParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
    {% endif %}
    
    // Prepare request options
    const options: RequestInit = {
      method: '{{ operation.method|upper }}',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        {% if api_key_param %}'Authorization': `Bearer ${this.apiKey}`,{% endif %}
        {% for param in operation.parameters|selectattr("in", "equalto", "header")|list %}
        '{{ param.original_name }}': String({{ param.name }}),
        {% endfor %}
      },
      {% if operation.request_body %}
      body: JSON.stringify({
        {% for prop_name, prop in operation.request_body.properties.items() %}
        {{ prop_name }},
        {% endfor %}
      }),
      {% endif %}
    };
    
    // Make the request
    const response = await fetch(url, options);
    
    // Handle errors
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }
    
    // Parse and return the response
    return await response.json();
  }
  
  {% endfor %}
}

// Usage example:
// const client = new {{ api_name }}Client('https://api.example.com'{% if api_key_param %}, 'your-api-key'{% endif %});
// client.{{ operations[0].function_name if operations else "methodName" }}()
//   .then(result => console.log(result))
//   .catch(error => console.error(error));
"""

class TypeScriptGenerator(CodeGenerator):
    """Generate TypeScript SDK code from OpenAPI spec."""
    
    def generate(self, openapi_spec: Dict[str, Any], operation_id: Optional[str] = None) -> str:
        """Generate TypeScript SDK code for the given OpenAPI spec."""
        logging.info("Generating TypeScript SDK")
        
        # Extract API details
        api_info = openapi_spec.get("info", {})
        api_name = api_info.get("title", "API").replace(" ", "")
        
        # Extract security schemes
        security_schemes = openapi_spec.get("components", {}).get("securitySchemes", {})
        api_key_param = None
        for scheme_name, scheme in security_schemes.items():
            if scheme.get("type") == "apiKey" or scheme.get("type") == "http":
                api_key_param = scheme_name
                break
        
        # Extract operations and types
        operations = self._extract_operations(openapi_spec, operation_id)
        types = self._extract_types(openapi_spec)
        
        # Render the template
        environment = jinja2.Environment()
        template = environment.from_string(TYPESCRIPT_TEMPLATE)
        rendered_code = template.render(
            api_name=api_name,
            api_info=api_info,
            operations=operations,
            types=types,
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
                    "parameters": [],
                    "response_type": "any"  # Default response type
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
                        "type": "string"  # Default type
                    }
                    
                    # Determine TypeScript type
                    schema = param.get("schema", {})
                    param_info["type"] = self._get_typescript_type(schema)
                    
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
                                prop_type = self._get_typescript_type(prop)
                                    
                                op_info["parameters"].append({
                                    "name": prop_name,
                                    "original_name": prop_name,
                                    "in": "body",
                                    "description": prop.get("description", ""),
                                    "required": prop_name in schema.get("required", []),
                                    "type": prop_type
                                })
                
                # Determine response type
                responses = operation.get("responses", {})
                success_response = responses.get("200", {})
                if not success_response:
                    success_response = next((resp for code, resp in responses.items() 
                                           if code.startswith("2")), {})
                
                if success_response:
                    content = success_response.get("content", {})
                    if "application/json" in content:
                        schema = content["application/json"].get("schema", {})
                        op_info["response_type"] = self._get_typescript_type(schema)
                
                operations.append(op_info)
        
        return operations
    
    def _extract_types(self, openapi_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract types from the OpenAPI spec components."""
        types = []
        schemas = openapi_spec.get("components", {}).get("schemas", {})
        
        for schema_name, schema in schemas.items():
            if schema.get("type") == "object":
                type_info = {
                    "name": schema_name,
                    "properties": {}
                }
                
                for prop_name, prop in schema.get("properties", {}).items():
                    type_info["properties"][prop_name] = {
                        "type": self._get_typescript_type(prop),
                        "required": prop_name in schema.get("required", [])
                    }
                
                types.append(type_info)
        
        return types
    
    def _get_typescript_type(self, schema: Dict[str, Any]) -> str:
        """Determine the appropriate TypeScript type for a schema."""
        if schema.get("type") == "integer" or schema.get("type") == "number":
            return "number"
        elif schema.get("type") == "boolean":
            return "boolean"
        elif schema.get("type") == "array":
            items_type = self._get_typescript_type(schema.get("items", {}))
            return f"{items_type}[]"
        elif schema.get("type") == "object":
            if schema.get("properties"):
                # If this is a complex object with properties, we could create an interface
                # But for simplicity, we'll use Record<string, any>
                return "Record<string, any>"
            else:
                return "Record<string, any>"
        elif schema.get("$ref"):
            # Handle reference to a schema component
            ref_path = schema.get("$ref")
            # Extract the type name from the reference path
            # Format is typically "#/components/schemas/TypeName"
            ref_parts = ref_path.split("/")
            return ref_parts[-1] if len(ref_parts) > 0 else "any"
        else:
            return "string"  # Default to string for unknown types

def generate_typescript_sdk(openapi_spec: Dict[str, Any], operation_id: Optional[str] = None) -> str:
    """Generate TypeScript SDK code from OpenAPI spec."""
    generator = TypeScriptGenerator()
    return generator.generate(openapi_spec, operation_id)