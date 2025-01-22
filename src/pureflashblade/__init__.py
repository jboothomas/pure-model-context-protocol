from . import server
import asyncio
import mcp.server.stdio

def main():
    """Main entry point for the package."""
    # Run both WebSocket and STDIO servers concurrently
    asyncio.run(server.main())

# Optionally expose other important items at package level
__all__ = ['main', 'server']
