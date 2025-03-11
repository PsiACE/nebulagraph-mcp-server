# Model Context Protocol Server for NebulaGraph


A Model Context Protocol (MCP) server implementation that provides access to [NebulaGraph](https://github.com/vesoft-inc/nebula).

[![PyPI - Version](https://img.shields.io/pypi/v/nebulagraph-mcp-server)](https://pypi.org/project/nebulagraph-mcp-server/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nebulagraph-mcp-server)](https://pypi.org/project/nebulagraph-mcp-server/)
[![Lint and Test](https://github.com/PsiACE/nebulagraph-mcp-server/actions/workflows/test.yml/badge.svg)](https://github.com/PsiACE/nebulagraph-mcp-server/actions/workflows/test.yml)

## Features

- Seamless access to NebulaGraph 3.x .
- Get ready for graph exploration, you know, Schema, Query, and a few shortcut algorithms.
- Follow Model Context Protocol, ready to integrate with LLM tooling systems.
- Simple command-line interface with support for configuration via environment variables and .env files.

![LlamaIndex with NebulaGraph MCP](./assets/llamaindex-with-nebulagraph-mcp.png)

## Installation

```shell
pip install nebulagraph-mcp-server
```

## Usage

`nebulagraph-mcp-server` will load configs from `.env`, for example:

```
NEBULA_VERSION=v3 # only v3 is supported
NEBULA_HOST=<your-nebulagraph-server-host>
NEBULA_PORT=<your-nebulagraph-server-port>
NEBULA_USER=<your-nebulagraph-server-user>
NEBULA_PASSWORD=<your-nebulagraph-server-password>
```

> It requires the value of `NEBULA_VERSION` to be equal to v3 until we are ready for v5.

## Development

```shell
npx @modelcontextprotocol/inspector \
  uv run nebulagraph-mcp-server
```

## Credits

The layout and workflow of this repo is copied from [mcp-server-opendal](https://github.com/Xuanwo/mcp-server-opendal).