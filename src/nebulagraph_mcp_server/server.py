import argparse
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool

load_dotenv()

default_log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, default_log_level, logging.INFO)

logging.basicConfig(level=log_level)
logger = logging.getLogger("nebulagraph_mcp_server")


@dataclass
class NebulaContext:
    pool: ConnectionPool


# Create a global connection pool
config = Config()
config.max_connection_pool_size = 10
global_pool = ConnectionPool()


def get_connection_pool() -> ConnectionPool:
    """Get the global connection pool"""
    return global_pool


@asynccontextmanager
async def nebula_lifespan(server: FastMCP) -> AsyncIterator[NebulaContext]:
    """This is a context manager for NebulaGraph connection."""
    try:
        if os.environ["NEBULA_VERSION"] != "v3":
            raise ValueError("NebulaGraph version must be v3")

        # Initialize the connection
        try:
            global_pool.init(
                [
                    (
                        os.getenv("NEBULA_HOST", "127.0.0.1"),
                        int(os.getenv("NEBULA_PORT", "9669")),
                    )
                ],
                config,
            )
        except Exception as e:
            logger.error(f"Failed to initialize NebulaGraph connection: {e!s}")

        yield NebulaContext(pool=global_pool)
    finally:
        # Clean up the connection
        global_pool.close()


# Create MCP server
mcp = FastMCP(
    "NebulaGraph MCP Server", lifespan=nebula_lifespan, log_level=default_log_level
)


@mcp.resource("schema://space/{space}")
def get_space_schema_resource(space: str) -> str:
    """Get the schema information of the specified space
    Args:
        space: The space to get the schema for
    Returns:
        The schema information of the specified space
    """
    pool = get_connection_pool()
    session = pool.get_session(
        os.getenv("NEBULA_USER", "root"), os.getenv("NEBULA_PASSWORD", "nebula")
    )

    try:
        session.execute(f"USE {space}")
        # Get tags
        tags = session.execute("SHOW TAGS").column_values("Name")
        # Get edges
        edges = session.execute("SHOW EDGES").column_values("Name")

        schema = f"Space: {space}\n\nTags:\n"
        for tag in tags:
            tag_result = session.execute(f"DESCRIBE TAG {tag}")
            schema += f"\n{tag}:\n"
            # Iterate through all rows
            for i in range(tag_result.row_size()):
                field = tag_result.row_values(i)
                schema += f"  - {field[0]}: {field[1]}\n"

        schema += "\nEdges:\n"
        for edge in edges:
            edge_result = session.execute(f"DESCRIBE EDGE {edge}")
            schema += f"\n{edge}:\n"
            # Iterate through all rows
            for i in range(edge_result.row_size()):
                field = edge_result.row_values(i)
                schema += f"  - {field[0]}: {field[1]}\n"

        return schema
    finally:
        session.release()


@mcp.resource("path://space/{space}/from/{src}/to/{dst}/depth/{depth}/limit/{limit}")
def get_path_resource(space: str, src: str, dst: str, depth: int, limit: int) -> str:
    """Get the path between two vertices
    Args:
        space: The space to use
        src: The source vertex ID
        dst: The destination vertex ID
        depth: The maximum path depth
        limit: The maximum number of paths to return
    Returns:
        The path between the source and destination vertices
    """
    pool = get_connection_pool()
    session = pool.get_session(
        os.getenv("NEBULA_USER", "root"), os.getenv("NEBULA_PASSWORD", "nebula")
    )

    try:
        session.execute(f"USE {space}")

        query = f"""FIND ALL PATH WITH PROP FROM "{src}" TO "{dst}" OVER * BIDIRECT UPTO {depth} STEPS
                  YIELD PATH AS paths | LIMIT {limit}"""

        result = session.execute(query)
        if result.is_succeeded():
            # Format the path results
            if result.row_size() > 0:
                output = f"Find paths from {src} to {dst}: \n\n"

                # Iterate through all paths
                for i in range(result.row_size()):
                    path = result.row_values(i)[
                        0
                    ]  # The path should be in the first column
                    output += f"Path {i + 1}:\n{path}\n\n"

                return output
            return f"No paths found from {src} to {dst}"
        else:
            return f"Query failed: {result.error_msg()}"
    finally:
        session.release()


@mcp.tool()
def list_spaces() -> str:
    """List all available spaces
    Returns:
        The available spaces
    """
    pool = get_connection_pool()
    session = pool.get_session(
        os.getenv("NEBULA_USER", "root"), os.getenv("NEBULA_PASSWORD", "nebula")
    )

    try:
        result = session.execute("SHOW SPACES")
        if result.is_succeeded():
            spaces = result.column_values("Name")
            return "Available spaces:\n" + "\n".join(f"- {space}" for space in spaces)
        return f"Failed to list spaces: {result.error_msg()}"
    finally:
        session.release()


@mcp.tool()
def get_space_schema(space: str) -> str:
    """Get the schema information of the specified space
    Args:
        space: The space to get the schema for
    Returns:
        The schema information of the specified space
    """
    return get_space_schema_resource(space)


@mcp.tool()
def execute_query(query: str, space: str) -> str:
    """Execute a query
    Args:
        query: The query to execute
        space: The space to use
    Returns:
        The results of the query
    """
    pool = get_connection_pool()
    session = pool.get_session(
        os.getenv("NEBULA_USER", "root"), os.getenv("NEBULA_PASSWORD", "nebula")
    )

    try:
        session.execute(f"USE {space}")
        result = session.execute(query)
        if result.is_succeeded():
            # Format the query results
            if result.row_size() > 0:
                columns = result.keys()
                output = "Results:\n"
                output += " | ".join(columns) + "\n"
                output += "-" * (len(" | ".join(columns))) + "\n"

                # Iterate through all rows
                for i in range(result.row_size()):
                    row = result.row_values(i)
                    output += " | ".join(str(val) for val in row) + "\n"
                return output
            return "Query executed successfully (no results)"
        else:
            return f"Query failed: {result.error_msg()}"
    finally:
        session.release()


@mcp.tool()
def find_path(src: str, dst: str, space: str, depth: int = 3, limit: int = 10) -> str:
    """Find paths between two vertices
    Args:
        src: The source vertex ID
        dst: The destination vertex ID
        space: The space to use
        depth: The maximum path depth
        limit: The maximum number of paths to return
    Returns:
        The path results
    """
    return get_path_resource(space, src, dst, depth, limit)


@mcp.resource("neighbors://space/{space}/vertex/{vertex}/depth/{depth}")
def get_neighbors_resource(space: str, vertex: str, depth: int) -> str:
    """Get the neighbors of the specified vertex
    Args:
        space: The space to use
        vertex: The vertex ID to query
        depth: The depth of the query
    Returns:
        The neighbors of the specified vertex
    """
    pool = get_connection_pool()
    session = pool.get_session(
        os.getenv("NEBULA_USER", "root"), os.getenv("NEBULA_PASSWORD", "nebula")
    )

    try:
        session.execute(f"USE {space}")

        query = f"""
        MATCH (u)-[e*1..{depth}]-(v)
        WHERE id(u) == "{vertex}"
        RETURN DISTINCT v, e
        """

        result = session.execute(query)
        if result.is_succeeded():
            if result.row_size() > 0:
                output = f"Vertex {vertex} neighbors (depth {depth}):\n\n"
                for i in range(result.row_size()):
                    row = result.row_values(i)
                    neighbor_vertex = row[0]
                    edges = row[1]
                    output += (
                        f"Neighbor Vertex:\n{neighbor_vertex}\nEdges:\n{edges}\n\n"
                    )
                return output
            return f"No neighbors found for vertex {vertex}"
        else:
            return f"Query failed: {result.error_msg()}"
    finally:
        session.release()


@mcp.tool()
def find_neighbors(vertex: str, space: str, depth: int = 1) -> str:
    """Find the neighbors of the specified vertex
    Args:
        vertex: The vertex ID to query
        space: The space to use
        depth: The depth of the query, default is 1
    Returns:
        The neighbors of the specified vertex
    """
    return get_neighbors_resource(space, vertex, depth)


def main():
    parser = argparse.ArgumentParser(description="NebulaGraph MCP server")
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport method (stdio or sse)",
    )

    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run("sse")
    else:
        mcp.run("stdio")


if __name__ == "__main__":
    main()
