# src/mcp/servers/amazon_music/tools/tool_registry.py
from typing import Dict, Any, List
import logging

# Import tool implementations
from mcp.servers.amazon_music.tools.auth import get_authentication_tool_definition, execute_authentication_tool
from mcp.servers.amazon_music.tools.playback import get_playback_tool_definitions, execute_playback_tool
from mcp.servers.amazon_music.tools.search import get_search_tool_definition, execute_search_tool
from mcp.servers.amazon_music.tools.playlists import get_playlist_tool_definitions, execute_playlist_tool

# Dictionary of tool name to execution function
_TOOL_EXECUTORS = {
    "amazon_music_authenticate": execute_authentication_tool,
    "amazon_music_search": execute_search_tool,
    "amazon_music_playback": execute_playback_tool,
    "amazon_music_playlist": execute_playlist_tool
}

def get_all_tools() -> List[Dict[str, Any]]:
    """Get definitions for all available tools."""
    tools = [
        get_authentication_tool_definition(),
        get_search_tool_definition()
    ]
    
    # Add playback tools (multiple tools from one module)
    tools.extend(get_playback_tool_definitions())
    
    # Add playlist tools (multiple tools from one module)
    tools.extend(get_playlist_tool_definitions())
    
    return tools

async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name with the given arguments."""
    if tool_name not in _TOOL_EXECUTORS:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    logging.info(f"Executing tool: {tool_name}")
    executor = _TOOL_EXECUTORS[tool_name]
    return await executor(arguments)