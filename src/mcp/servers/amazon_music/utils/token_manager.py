# src/mcp/servers/amazon_music/utils/token_manager.py
import os
import json
import time
import logging
import requests
import aiosqlite
from typing import Dict, Any, Optional

from mcp.servers.amazon_music.utils.db import get_connection

# Constants
TOKEN_ENDPOINT = "https://api.amazon.com/auth/o2/token"

class TokenManager:
    """Manages access tokens for Amazon Music SDK."""
    
    @staticmethod
    async def get_valid_token(user_id: str) -> Optional[str]:
        """Get a valid access token, refreshing if necessary."""
        try:
            async with await get_connection() as db:
                # Get the user's token data
                async with db.execute(
                    "SELECT access_token, refresh_token, expires_at FROM amazon_tokens WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    
                    if not row:
                        return None
                    
                    access_token, refresh_token, expires_at = row
                    
                    # Check if token is expired or about to expire (within 5 minutes)
                    if expires_at < time.time() + 300:
                        # Refresh the token
                        new_token_data = await TokenManager._refresh_token(refresh_token)
                        
                        if new_token_data:
                            access_token = new_token_data["access_token"]
                            new_expires_at = time.time() + new_token_data["expires_in"]
                            
                            # Update refresh token if provided
                            if "refresh_token" in new_token_data:
                                refresh_token = new_token_data["refresh_token"]
                            
                            # Update in database
                            await db.execute(
                                """
                                UPDATE amazon_tokens 
                                SET access_token = ?, refresh_token = ?, expires_at = ?
                                WHERE user_id = ?
                                """,
                                (access_token, refresh_token, new_expires_at, user_id)
                            )
                            await db.commit()
                        else:
                            # Refresh failed, return None
                            return None
                    
                    return access_token
        except Exception as e:
            logging.exception(f"Error getting valid token for user {user_id}")
            return None
    
    @staticmethod
    async def save_token(user_id: str, access_token: str, refresh_token: str, expires_at: float) -> bool:
        """Save token data to the database."""
        try:
            async with await get_connection() as db:
                # Check if user already exists
                async with db.execute(
                    "SELECT COUNT(*) FROM amazon_tokens WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    count = await cursor.fetchone()
                    exists = count[0] > 0
                
                if exists:
                    # Update existing record
                    await db.execute(
                        """
                        UPDATE amazon_tokens 
                        SET access_token = ?, refresh_token = ?, expires_at = ?
                        WHERE user_id = ?
                        """,
                        (access_token, refresh_token, expires_at, user_id)
                    )
                else:
                    # Insert new record
                    await db.execute(
                        """
                        INSERT INTO amazon_tokens (user_id, access_token, refresh_token, expires_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (user_id, access_token, refresh_token, expires_at)
                    )
                
                await db.commit()
                return True
        except Exception as e:
            logging.exception(f"Error saving token for user {user_id}")
            return False
    
    @staticmethod
    async def revoke_token(user_id: str) -> bool:
        """Revoke token for a user."""
        try:
            async with await get_connection() as db:
                await db.execute(
                    "DELETE FROM amazon_tokens WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()
                return True
        except Exception as e:
            logging.exception(f"Error revoking token for user {user_id}")
            return False
    
    @staticmethod
    async def _refresh_token(refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh an access token."""
        client_id = os.environ.get("AMAZON_CLIENT_ID")
        client_secret = os.environ.get("AMAZON_CLIENT_SECRET", "")
        
        if not client_id:
            logging.error("Missing AMAZON_CLIENT_ID for token refresh")
            return None
        
        try:
            response = requests.post(TOKEN_ENDPOINT, data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret
            })
            
            if response.status_code == 200:
                return response.json()
            
            logging.error(f"Token refresh failed: {response.status_code} - {response.text}")
            return None
        except Exception as e:
            logging.exception(f"Exception during token refresh: {str(e)}")
            return None