# src/mcp/servers/amazon_music/tools/auth.py
import json
import time
import os
import requests
import logging
import webbrowser
from typing import Dict, Any

from mcp.servers.amazon_music.utils.db import get_connection
from mcp.servers.amazon_music.utils.token_manager import TokenManager

# Constants for Amazon authentication
AUTH_ENDPOINT = "https://api.amazon.com/auth/o2/create/codepair"
TOKEN_ENDPOINT = "https://api.amazon.com/auth/o2/token"

def get_authentication_tool_definition() -> Dict[str, Any]:
    """Get the definition for the authentication tool."""
    return {
        "name": "amazon_music_authenticate",
        "description": "Authenticate with Amazon Music using device code flow",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "Unique identifier for the user account"
                },
                "force_reauth": {
                    "type": "boolean",
                    "default": False,
                    "description": "Force reauthentication even if valid credentials exist"
                }
            },
            "required": ["user_id"]
        }
    }

async def execute_authentication_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the authentication flow for Amazon Music."""
    user_id = args.get("user_id")
    force_reauth = args.get("force_reauth", False)
    
    if not user_id:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Error: user_id is required for authentication."
                }
            ],
            "isError": True
        }
    
    # Check if valid credentials already exist for this user
    if not force_reauth:
        token = TokenManager.get_valid_token(user_id)
        if token:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"User {user_id} is already authenticated with Amazon Music."
                    }
                ],
                "isError": False
            }
    
    # Get client credentials from environment
    client_id = os.environ.get("AMAZON_CLIENT_ID")
    if not client_id:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Error: AMAZON_CLIENT_ID environment variable not set."
                }
            ],
            "isError": True
        }
    
    try:
        # Step 1: Request device and user codes
        device_code_response = requests.post(AUTH_ENDPOINT, data={
            "client_id": client_id,
            "scope": "amazon_music:access"  # Adjust based on SDK requirements
        }).json()
        
        user_code = device_code_response["userCode"]
        verification_uri = device_code_response["verificationUri"]
        device_code = device_code_response["deviceCode"]
        expires_in = device_code_response["expiresIn"]
        interval = device_code_response["interval"]
        
        # Step 2: Display authentication instructions to the user
        content = [
            {
                "type": "text",
                "text": f"To authenticate with Amazon Music, please follow these steps:"
            },
            {
                "type": "text",
                "text": f"1. Visit {verification_uri} in your web browser"
            },
            {
                "type": "text",
                "text": f"2. Enter this code: {user_code}"
            },
            {
                "type": "text",
                "text": f"3. Sign in with your Amazon account"
            },
            {
                "type": "text",
                "text": f"The CLI will continue automatically once you've completed these steps. This code will expire in {expires_in} seconds."
            }
        ]
        
        # Optional: Try to launch the browser automatically
        try:
            webbrowser.open(verification_uri)
            content.append({
                "type": "text",
                "text": "A browser window should have opened automatically. If not, please open the URL manually."
            })
        except:
            pass
        
        # Step 3: Poll for completion
        client_secret = os.environ.get("AMAZON_CLIENT_SECRET", "")
        start_time = time.time()
        while time.time() - start_time < expires_in:
            # Wait for the specified interval
            time.sleep(interval)
            
            # Check if the user has authenticated
            token_data = None
            try:
                token_response = requests.post(TOKEN_ENDPOINT, data={
                    "grant_type": "device_code",
                    "device_code": device_code,
                    "client_id": client_id,
                    "client_secret": client_secret
                })
                
                if token_response.status_code == 200:
                    token_data = token_response.json()
                # If it's an authorization_pending error, keep polling
                elif token_response.status_code == 400 and "authorization_pending" in token_response.text:
                    continue
                # If it's any other error, stop polling
                else:
                    error_text = token_response.text
                    logging.error(f"Authentication error: {error_text}")
                    raise Exception(f"Authentication failed: {error_text}")
            except requests.exceptions.RequestException as e:
                logging.error(f"Request error: {str(e)}")
                raise Exception(f"Authentication request failed: {str(e)}")
            
            if token_data:
                # Step 4: Store the tokens in the database
                await TokenManager.save_token(
                    user_id=user_id,
                    access_token=token_data["access_token"],
                    refresh_token=token_data["refresh_token"],
                    expires_at=time.time() + token_data["expires_in"]
                )
                
                content.append({
                    "type": "text",
                    "text": f"Successfully authenticated with Amazon Music for user {user_id}!"
                })
                
                return {
                    "content": content,
                    "isError": False
                }
        
        # If we've reached this point, authentication timed out
        content.append({
            "type": "text",
            "text": "Authentication timed out. Please try again."
        })
        
        return {
            "content": content,
            "isError": True
        }
        
    except Exception as e:
        logging.exception("Authentication error")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error during authentication: {str(e)}"
                }
            ],
            "isError": True
        }