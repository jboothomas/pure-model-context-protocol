import asyncio

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio

import json
import pypureclient
from pypureclient import flashblade

from datetime import datetime, timedelta

server = Server("pureflashblade")

class FlashbladeClient:
    """
    A client for interacting with Pure Storage Flashblade REST API 2.0
    """
    
    def __init__(self, fb_host, fb_api_token):
        """
        Initialize the Flashblade client
        
        Args:
            fb_host (str): The hostname or IP address of the Flashblade
            fb_api_token (str): The API token for authentication
        """
        try:
            self.client = flashblade.Client(target=fb_host, api_token=fb_api_token, verify_ssl=False, user_agent='MCP/0.1.0')
        except pypureclient.exceptions.PureError as e:
            print(f"Exception when logging in to the array: {e}")

    def call_endpoint(self, method_name, **kwargs):
        """
        Calls a method on the underlying flashblade.Client object by name.

        Args:
            method_name (str): The name of the method to call on the client.
            **kwargs: Any keyword arguments to pass to that method.

        Returns:
            The result of the underlying client method call, or None on error.
        """
        try:
            method = getattr(self.client, method_name)
            return method(**kwargs)
        except pypureclient.exceptions.PureError as e:
            print(f"Exception with {method_name}: {e}")
            return None
        except AttributeError:
            print(f"Method '{method_name}' not found on flashblade.Client")
            return None


def json_log(response, endpoint_name):
    """
    Serializes and logs the response from a Flashblade API endpoint.

    Args:
        response: The API response to be logged and serialized.
        endpoint_name (str): The name of the API endpoint.

    Returns:
        str: JSON-formatted string of the response data.
    """
    if isinstance(response, pypureclient.responses.ValidResponse):
        if response and hasattr(response, "items"):
            json_data = json.dumps([item.to_dict() for item in response.items])
        else:
            json_data = json.dumps({"error": f"No data available for {endpoint_name}"})
    else:
        json_data = json.dumps({"error": f"Invalid response from {endpoint_name}"})

    server.request_context.session.send_log_message(
        level="info",
        data=f"{endpoint_name}: {json_data}"
    )
    return json_data

### MCP tools ###
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON schema validation.
    """
    return [
        types.Tool(
            name="pure-fb",
            description="Run a command against a given FlashBlade",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "IP address of array management endpoint"},
                    "api_token": {"type": "string", "description": "API token for array management user"},
                    "command": {"type": "string", "description": "SDK call to run against the array"},
                    "parameters": {
                        "type": "object",
                        "description": "Optional parameters to pass to the SDK call",
                        "additionalProperties": True
                    }
                },
                "required": ["host", "api_token", "command"],
            },
        ),
        types.Tool(
            name="get-array-full",
            description="Get array full information, space and 7 days performance",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "IP address of array management endpoint"},
                    "api_token": {"type": "string", "description": "API token for array management user"},
                },
                "required": ["host", "api_token"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    """
    if name not in ["pure-fb", "get-array-full"]:
        raise ValueError(f"Unknown tool: {name}")

    if not arguments:
        raise ValueError("Missing arguments")

    query_host = arguments.get("host")
    query_api_token = arguments.get("api_token")

    server.request_context.session.send_log_message(
        level="info",
        data=f"Initializing query with '{query_host}' and '{query_api_token}'",
    )

    if not query_host or not query_api_token:
        raise ValueError("Missing host or api_token")

    # Init array client
    fb_client = FlashbladeClient(fb_host=query_host, fb_api_token=query_api_token)

    if name == "pure-fb":
        query_command = arguments.get("command")
        query_parameters = arguments.get("parameters", {})

        if not query_command:
            raise ValueError("Missing command")

        try:
            response = fb_client.call_endpoint(query_command, **query_parameters)
            response_info = json_log(response, query_command)
            return [types.TextContent(type="text", text=f"{response_info}")]
        except Exception as error:
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text=f"Error: {str(error)}")]
            )

    elif name == "get-array-full":
        try:
            arrays_info_response = fb_client.call_endpoint("get_arrays")
            arrays_info = json_log(arrays_info_response, "get_arrays")

            arrays_space_response = fb_client.call_endpoint("get_arrays_space")
            arrays_space = json_log(arrays_space_response, "get_arrays_space")
            
            e_end_time = int(datetime.now().timestamp() * 1000)
            e_start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)

            arrays_performance_response = fb_client.call_endpoint(
                "get_arrays_performance", start_time=e_start_time, end_time=e_end_time
            )
            arrays_performance = json_log(arrays_performance_response, "get_arrays_performance")

            return [
                types.TextContent(
                    type="text",
                    text=f"Arrays information: {arrays_info}, space: {arrays_space}, and performance: {arrays_performance}"
                )
            ]
        except Exception as error:
            return types.CallToolResult(
                isError=True,
                content=[types.TextContent(type="text", text=f"Error: {str(error)}")]
            )

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="pureflashblade",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
