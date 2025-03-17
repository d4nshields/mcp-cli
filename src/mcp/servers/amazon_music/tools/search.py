# src/mcp/servers/amazon_music/tools/search.py
import logging
from typing import Dict, Any

from mcp.servers.amazon_music.utils.token_manager import TokenManager
from mcp.servers.amazon_music.client.amazon_music_client import AmazonMusicClient

def get_search_tool_definition() -> Dict[str, Any]:
    """Get the definition for the search tool."""
    return {
        "name": "amazon_music_search",
        "description": "Search Amazon Music for tracks, albums, artists, or playlists",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "Unique identifier for the user account"
                },
                "query": {
                    "type": "string", 
                    "description": "Search query text"
                },
                "type": {
                    "type": "string",
                    "enum": ["track", "album", "artist", "playlist", "all"],
                    "default": "all",
                    "description": "Type of content to search for"
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of results to return"
                }
            },
            "required": ["user_id", "query"]
        }
    }

async def execute_search_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a search on Amazon Music."""
    user_id = args.get("user_id")
    query = args.get("query")
    content_type = args.get("type", "all")
    limit = args.get("limit", 10)
    
    if not user_id:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Error: user_id is required for searching."
                }
            ],
            "isError": True
        }
    
    if not query:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Error: query is required for searching."
                }
            ],
            "isError": True
        }
        
    # Get access token for the user
    access_token = await TokenManager.get_valid_token(user_id)
    
    if not access_token:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"User {user_id} is not authenticated with Amazon Music. Please run the authentication tool first."
                }
            ],
            "isError": True
        }
    
    try:
        # Create Amazon Music client
        client = AmazonMusicClient(access_token)
        
        # Execute search
        search_results = await client.search(query, content_type, limit)
        
        # Format results for display
        content = [
            {
                "type": "text",
                "text": f"Search results for '{query}':"
            }
        ]
        
        # For now, just show a placeholder since we don't have the actual SDK yet
        content.append({
            "type": "text",
            "text": "This would display search results from Amazon Music once the SDK is integrated."
        })
        
        # In real implementation, we would format actual search results
        
        return {
            "content": content,
            "isError": False
        }
    except Exception as e:
        logging.exception(f"Error during search: {str(e)}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error performing search: {str(e)}"
                }
            ],
            "isError": True
        }