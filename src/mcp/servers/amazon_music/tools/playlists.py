# src/mcp/servers/amazon_music/tools/playlists.py
import logging
from typing import Dict, Any, List

from mcp.servers.amazon_music.utils.token_manager import TokenManager
from mcp.servers.amazon_music.client.amazon_music_client import AmazonMusicClient

def get_playlist_tool_definitions() -> List[Dict[str, Any]]:
    """Get the definitions for playlist-related tools."""
    return [
        {
            "name": "amazon_music_playlist",
            "description": "Manage playlists on Amazon Music",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Unique identifier for the user account"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["list", "create", "delete", "add_track", "remove_track"],
                        "description": "Playlist action to perform"
                    },
                    "playlist_id": {
                        "type": "string",
                        "description": "Playlist ID for operations on existing playlists"
                    },
                    "playlist_name": {
                        "type": "string",
                        "description": "Name for new playlist (for create action)"
                    },
                    "playlist_description": {
                        "type": "string",
                        "description": "Description for new playlist (for create action)"
                    },
                    "track_id": {
                        "type": "string",
                        "description": "Track ID to add or remove"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 20,
                        "description": "Maximum number of playlists to return (for list action)"
                    }
                },
                "required": ["user_id", "action"]
            }
        }
    ]

async def execute_playlist_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a playlist action on Amazon Music."""
    user_id = args.get("user_id")
    action = args.get("action")
    playlist_id = args.get("playlist_id")
    playlist_name = args.get("playlist_name")
    playlist_description = args.get("playlist_description")
    track_id = args.get("track_id")
    limit = args.get("limit", 20)
    
    if not user_id:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Error: user_id is required for playlist operations."
                }
            ],
            "isError": True
        }
    
    if not action:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Error: action is required for playlist operations."
                }
            ],
            "isError": True
        }
        
    # Check required parameters for specific actions
    if action == "create" and not playlist_name:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Error: playlist_name is required for creating a playlist."
                }
            ],
            "isError": True
        }
    
    if action in ["delete", "add_track", "remove_track"] and not playlist_id:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error: playlist_id is required for {action} action."
                }
            ],
            "isError": True
        }
    
    if action in ["add_track", "remove_track"] and not track_id:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error: track_id is required for {action} action."
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
        
        # Placeholder response for each action type
        content = [
            {
                "type": "text",
                "text": f"Performing {action} action on Amazon Music playlists."
            },
            {
                "type": "text",
                "text": "Note: This is a placeholder response. Actual playlist operations will be implemented when the Amazon Music SDK is available."
            }
        ]
        
        # In a real implementation, we would call the appropriate SDK method based on the action
        # For now, return the placeholder response
        
        return {
            "content": content,
            "isError": False
        }
    except Exception as e:
        logging.exception(f"Error during playlist operation: {str(e)}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error performing playlist operation: {str(e)}"
                }
            ],
            "isError": True
        }