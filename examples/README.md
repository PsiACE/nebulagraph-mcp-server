# LlamaIndex Agent Example with NebulaGraph MCP Server

## Start the MCP Server

To run this example, you need to have a MCP server running.

Make sure you have a NebulaGraph services, set the environment variables first:

```bash
NEBULA_VERSION=v3
NEBULA_HOST=your-nebulagraph-server-host
NEBULA_PORT=your-nebulagraph-server-port
NEBULA_USER=your-nebulagraph-server-user
NEBULA_PASSWORD=your-nebulagraph-server-password
```

Then, run the following command:

```bash
uv sync  # To install the project, this should be done only once
uv run nebulagraph-mcp-server --transport sse
```

## Run the Example

Set the environment variables below.

- `MCP_HOST`: The host of the MCP server
- `MCP_PORT`: The port of the MCP server
- `OPENAI_API_KEY`: The API key of the OpenAI API
- `OPENAI_MODEL`: The model of the OpenAI API
- `OPENAI_ENDPOINT`: The endpoint of the OpenAI API

Then, run the example with the following command:

```bash
uv run examples/llamaindex-with-nebulagraph-mcp.py
```
