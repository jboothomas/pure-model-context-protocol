# pure-model-context-protocol

A simple MCP server to interact with Pure storage arrays, retrieves realtime information from a Pure Storage FlashBlade array

## Components

### Tools
The server provides a single tool:
 - pure-fb: Modular tool to process a command and arguments to retreive an array's information, volumes, hosts, ...

## Quickstart

### Install

#### Claude Desktop
Add the relevant entry to the claude_desktop_config.json file

- On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
- On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  ```
  "mcpServers": {
    "pureflashblade": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/jthomas/git/python/pureflashblade",
        "run",
        "pureflashblade"
      ]
    }
  }
  ```
</details>


