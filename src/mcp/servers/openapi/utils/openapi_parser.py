# src/mcp/servers/openapi/utils/openapi_parser.py
import json
import logging
from typing import Dict, Any
import aiohttp

async def parse_openapi_spec(spec_source: str) -> Dict[str, Any]:
    """Parse an OpenAPI specification from a URL or JSON string.
    
    Args:
        spec_source: URL to OpenAPI spec or JSON string containing the spec
        
    Returns:
        Dict containing the parsed OpenAPI specification
    """
    logging.info("Parsing OpenAPI specification")
    
    try:
        # Check if spec_source is a URL
        if spec_source.startswith(('http://', 'https://')):
            logging.info(f"Fetching OpenAPI spec from URL: {spec_source}")
            async with aiohttp.ClientSession() as session:
                async with session.get(spec_source) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"Failed to fetch OpenAPI spec: HTTP {response.status} - {error_text}")
                    
                    try:
                        spec_json = await response.json()
                    except:
                        # If not JSON, try to parse as YAML
                        import yaml
                        text_content = await response.text()
                        spec_json = yaml.safe_load(text_content)
        else:
            # Assume it's a JSON string
            try:
                spec_json = json.loads(spec_source)
            except json.JSONDecodeError:
                # Try parsing as YAML
                import yaml
                spec_json = yaml.safe_load(spec_source)
        
        # Basic validation - check for required OpenAPI fields
        if not isinstance(spec_json, dict):
            raise ValueError("OpenAPI spec must be a JSON object")
            
        if "openapi" not in spec_json and "swagger" not in spec_json:
            raise ValueError("Invalid OpenAPI spec: missing 'openapi' or 'swagger' version field")
            
        if "paths" not in spec_json:
            raise ValueError("Invalid OpenAPI spec: missing 'paths' field")
            
        if "info" not in spec_json:
            raise ValueError("Invalid OpenAPI spec: missing 'info' field")
        
        logging.info(f"Successfully parsed OpenAPI spec for API: {spec_json.get('info', {}).get('title', 'Unknown')}")
        return spec_json
        
    except Exception as e:
        logging.exception("Error parsing OpenAPI spec")
        raise ValueError(f"Failed to parse OpenAPI spec: {str(e)}")