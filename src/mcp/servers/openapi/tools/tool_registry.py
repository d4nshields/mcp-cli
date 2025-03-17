# src/mcp/servers/openapi/tools/tool_registry.py
from typing import Dict, Any, List
import logging

# Import our tool implementation
from mcp.servers.openapi.tools.openapi_sdk import get_openapi_sdk_tool_definition, execute_openapi_sdk_tool

# Dictionary of tool name to execution function
_TOOL_EXECUTORS = {
    "openapi_sdk": execute_openapi_sdk_tool
}

def get_all_tools() -> List[Dict[str, Any]]:
    """Get definitions for all available tools."""
    return [
        get_openapi_sdk_tool_definition()
    ]

async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name with the given arguments."""
    if tool_name not in _TOOL_EXECUTORS:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    logging.info(f"Executing tool: {tool_name}")
    executor = _TOOL_EXECUTORS[tool_name]
    return await executor(arguments)