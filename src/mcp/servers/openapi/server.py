# src/mcp/servers/openapi/server.py
import json
import sys
import asyncio
import logging
from typing import Dict, Any, Optional

# Import tool registry
from mcp.servers.openapi.tools.tool_registry import get_all_tools, execute_tool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='openapi_server.log'
)

async def handle_initialize(message: Dict[str, Any]) -> Dict[str, Any]:
    """Handle the initialize method from the client."""
    protocol_version = message.get("params", {}).get("protocolVersion")
    
    # Currently we only support protocol version 2024-11-05
    if protocol_version != "2024-11-05":
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {
                "code": -32602,
                "message": "Unsupported protocol version",
                "data": {
                    "supported": ["2024-11-05"],
                    "requested": protocol_version
                }
            }
        }
    
    # Return supported capabilities
    return {
        "jsonrpc": "2.0",
        "id": message.get("id"),
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True}
            },
            "serverInfo": {
                "name": "OpenAPI SDK Server",
                "version": "0.1.0"
            }
        }
    }

async def handle_tools_list(message: Dict[str, Any]) -> Dict[str, Any]:
    """Handle the tools/list method from the client."""
    cursor = message.get("params", {}).get("cursor")
    
    # No pagination in this implementation, ignoring cursor
    tools = get_all_tools()
    
    return {
        "jsonrpc": "2.0",
        "id": message.get("id"),
        "result": {
            "tools": tools,
            "nextCursor": None  # No pagination
        }
    }

async def handle_tools_call(message: Dict[str, Any]) -> Dict[str, Any]:
    """Handle the tools/call method from the client."""
    params = message.get("params", {})
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    try:
        result = await execute_tool(tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": result
        }
    except ValueError as e:
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {
                "code": -32602,
                "message": str(e)
            }
        }
    except Exception as e:
        logging.exception(f"Error executing tool {tool_name}")
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

async def handle_message(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process an incoming message and generate a response."""
    method = message.get("method")
    
    # Handle notifications (no response needed)
    if message.get("id") is None:
        if method == "notifications/initialized":
            logging.info("Client initialized notification received")
        return None
    
    # Handle methods that require responses
    if method == "initialize":
        return await handle_initialize(message)
    elif method == "tools/list":
        return await handle_tools_list(message)
    elif method == "tools/call":
        return await handle_tools_call(message)
    
    # Method not found
    return {
        "jsonrpc": "2.0",
        "id": message.get("id"),
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
    }

async def main():
    """Main entry point for the OpenAPI server."""
    logging.info("OpenAPI MCP Server starting")
    
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break

            line = line.strip()
            if not line:
                continue
                
            try:
                message = json.loads(line)
                response = await handle_message(message)
                if response:
                    json_response = json.dumps(response)
                    print(json_response, flush=True)
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON: {line}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error: Invalid JSON"
                    }
                }
                print(json.dumps(error_response), flush=True)
            except Exception as e:
                logging.exception("Error processing message")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id") if 'message' in locals() else None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
        except Exception as e:
            logging.exception("Unexpected error in main loop")

if __name__ == "__main__":
    asyncio.run(main())