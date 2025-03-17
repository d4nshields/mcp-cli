# src/mcp/servers/openapi/utils/code_generators/javascript.py
import logging
import jinja2
from typing import Dict, Any, Optional, List
from mcp.servers.openapi.utils.code_generators.base import CodeGenerator

# JavaScript SDK template
JAVASCRIPT_TEMPLATE = """
/**
 * JavaScript SDK for {{ api_info.title }}
 * {{ api_info.description }}
 * Version: {{ api_info.version }}
 */

class {{ api_name }}Client {
  /**
   * Create a new API client instance
   * @param {string} baseUrl - The base URL for API requests
   {% if api_key_param %}* @param {string} apiKey - API key for authentication{% endif %}
   */
  constructor(baseUrl{% if api_key_param %}, apiKey{% endif %}) {
    this.baseUrl = baseUrl;
    {% if api_key_param %}this.apiKey = apiKey;{% endif %}
  }

  {% for operation in operations %}
  /**
   * {{ operation.description }}
   {% for param in operation.parameters %}
   * @param { {{ param.js_doc_type }} } {{ param.name }} - {{ param.description }}
   {% endfor %}
   * @returns {Promise<any>} A Promise containing the response data
   */
  async {{ operation.function_name }}({% for param in operation.parameters %}{{ param.name }}{% if not loop.last %}, {% endif %}{% endfor %}) {
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
    const options = {
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

// Export the client
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { {{ api_name }}Client };
} else if (typeof window !== 'undefined') {
  window.{{ api_name }}Client = {{ api_name }}Client;
}
"""

class JavaScriptGenerator(CodeGenerator):
    """Generate JavaScript SDK code from OpenAPI spec."""
    
    def generate(self, openapi_spec: Dict[str, Any], operation_id: Optional[str] = None) -> str:
        """Generate JavaScript SDK code for the given OpenAPI spec."""
        logging.info("Generating JavaScript SDK")
        
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
        
        # Extract operations
        operations = self._extract_operations(openapi_spec, operation_id)
        
        # Render the template
        environment = jinja2.Environment()
        template = environment.from_string(JAVASCRIPT_TEMPLATE)
        rendered_code = template.render(
            api_name=api_name,
            api_info=api_info,
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
                        "js_doc_type": "string"  # Default JSDoc type
                    }
                    
                    # Determine JSDoc type for documentation
                    schema = param.get("schema", {})
                    param_info["js_doc_type"] = self._get_jsdoc_type(schema)
                    
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
                                js_doc_type = self._get_jsdoc_type(prop)
                                    
                                op_info["parameters"].append({
                                    "name": prop_name,
                                    "original_name": prop_name,
                                    "in": "body",
                                    "description": prop.get("description", ""),
                                    "required": prop_name in schema.get("required", []),
                                    "js_doc_type": js_doc_type
                                })
                
                operations.append(op_info)
        
        return operations
    
    def _get_jsdoc_type(self, schema: Dict[str, Any]) -> str:
        """Determine the appropriate JSDoc type for a schema."""
        if schema.get("type") == "integer" or schema.get("type") == "number":
            return "number"
        elif schema.get("type") == "boolean":
            return "boolean"
        elif schema.get("type") == "array":
            items_type = self._get_jsdoc_type(schema.get("items", {}))
            return f"Array<{items_type}>"
        elif schema.get("type") == "object":
            return "Object"
        else:
            return "string"  # Default to string for unknown types

def generate_javascript_sdk(openapi_spec: Dict[str, Any], operation_id: Optional[str] = None) -> str:
    """Generate JavaScript SDK code from OpenAPI spec."""
    generator = JavaScriptGenerator()
    return generator.generate(openapi_spec, operation_id)