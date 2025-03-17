# src/mcp/servers/openapi/utils/api_client.py
import json
import logging
import aiohttp
from typing import Dict, Any, Optional

async def execute_api_request(
    openapi_spec: Dict[str, Any],
    operation_id: Optional[str],
    request_params: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute an API request using the provided parameters.
    
    Args:
        openapi_spec: The parsed OpenAPI specification
        operation_id: Optional operation ID to execute
        request_params: Parameters for the API request
        
    Returns:
        Dict containing the API response or error information
    """
    logging.info(f"Executing API request: {operation_id or 'unknown operation'}")
    
    # Validate required parameters
    if "base_url" not in request_params:
        raise ValueError("base_url is required for executing requests")
    
    base_url = request_params.pop("base_url")
    
    # If operation_id is provided, extract endpoint and method from the spec
    endpoint = request_params.pop("endpoint", "")
    method = request_params.pop("method", "get").lower()
    
    if operation_id:
        # Find the operation in the spec
        operation_details = _find_operation(openapi_spec, operation_id)
        if operation_details:
            endpoint = operation_details["path"]
            method = operation_details["method"]
    
    # Validate method
    if method not in ["get", "post", "put", "delete", "patch", "head", "options"]:
        raise ValueError(f"Invalid HTTP method: {method}")
    
    # Extract headers, query params, and body from request_params
    headers = request_params.pop("headers", {})
    query_params = request_params.pop("params", {})
    request_body = request_params.pop("json", {}) or request_params.pop("body", {})
    
    # Add default headers
    headers.setdefault("Accept", "application/json")
    
    # Add body content type if there's a body
    if request_body and "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"
    
    # Format the URL
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    # Make HTTP request
    try:
        async with aiohttp.ClientSession() as session:
            http_method = getattr(session, method)
            
            # Add timeout for safety
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with http_method(
                url, 
                json=request_body if headers.get("Content-Type") == "application/json" else None,
                data=request_body if headers.get("Content-Type") != "application/json" else None,
                params=query_params,
                headers=headers,
                timeout=timeout
            ) as response:
                # Try to parse response as JSON
                try:
                    result = await response.json()
                except:
                    # If not JSON, get text
                    result = await response.text()
                
                # Return error information if request failed
                if response.status >= 400:
                    return {
                        "error": f"API request failed with status {response.status}",
                        "status": response.status,
                        "details": result
                    }
                
                return result
    except aiohttp.ClientError as e:
        logging.exception(f"API request failed: {str(e)}")
        return {
            "error": f"API request failed: {str(e)}",
            "details": str(e)
        }
    except Exception as e:
        logging.exception(f"Unexpected error during API request: {str(e)}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "details": str(e)
        }

def _find_operation(openapi_spec: Dict[str, Any], operation_id: str) -> Optional[Dict[str, Any]]:
    """Find operation details by operationId in the OpenAPI spec."""
    paths = openapi_spec.get("paths", {})
    
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method in ["get", "post", "put", "delete", "patch"] and operation.get("operationId") == operation_id:
                return {
                    "path": path,
                    "method": method
                }
    
    return None