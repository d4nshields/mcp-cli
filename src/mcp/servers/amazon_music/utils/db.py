# src/mcp/servers/amazon_music/utils/db.py
import os
import logging
import aiosqlite
from pathlib import Path
from typing import Any

# Define the database path
DB_DIR = Path.home() / ".config" / "amazon-music-mcp"
DB_PATH = DB_DIR / "amazon_music.db"

async def get_connection() -> aiosqlite.Connection:
    """Get a connection to the database."""
    # Ensure directory exists
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    # Open and return the connection
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn

async def initialize_database() -> None:
    """Initialize the database with required tables."""
    try:
        logging.info("Initializing database")
        
        # Ensure directory exists
        DB_DIR.mkdir(parents=True, exist_ok=True)
        
        async with await get_connection() as db:
            # Create amazon_tokens table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS amazon_tokens (
                    user_id TEXT PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            
            # Create amazon_user_metadata table for storing user-specific settings
            await db.execute("""
                CREATE TABLE IF NOT EXISTS amazon_user_metadata (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT,
                    country_code TEXT,
                    last_login REAL,
                    settings TEXT  -- JSON blob for extensible settings
                )
            """)
            
            # Create amazon_playlists table for caching playlist data
            await db.execute("""
                CREATE TABLE IF NOT EXISTS amazon_playlists (
                    playlist_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    last_updated REAL,
                    FOREIGN KEY (user_id) REFERENCES amazon_tokens(user_id)
                )
            """)
            
            await db.commit()
            logging.info("Database initialization complete")
    except Exception as e:
        logging.exception(f"Error initializing database: {str(e)}")
        raise