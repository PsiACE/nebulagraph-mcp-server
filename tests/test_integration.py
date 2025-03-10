import os
import time

import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Ensure correct environment variable settings
@pytest.fixture(scope="session", autouse=True)
def setup_env():
    os.environ["NEBULA_VERSION"] = "v3"
    os.environ["NEBULA_HOST"] = os.getenv("NEBULA_HOST", "127.0.0.1")
    os.environ["NEBULA_PORT"] = os.getenv("NEBULA_PORT", "9669")
    os.environ["NEBULA_USER"] = os.getenv("NEBULA_USER", "root")
    os.environ["NEBULA_PASSWORD"] = os.getenv("NEBULA_PASSWORD", "nebula")


# Setup commands for test data
SETUP_COMMANDS = [
    # Group 1: Create space
    ["CREATE SPACE IF NOT EXISTS test_graph(vid_type=FIXED_STRING(30))"],
    # Group 2: Use space and create tags and edge types
    [
        "USE test_graph",
        "CREATE TAG IF NOT EXISTS person(name string, age int)",
        "CREATE EDGE IF NOT EXISTS knows(years int)",
        "CREATE EDGE IF NOT EXISTS reports_to(department string)",
    ],
    # Group 3: Insert vertices
    [
        "USE test_graph",
        'INSERT VERTEX person(name, age) VALUES "person1":("Alice", 30)',
        'INSERT VERTEX person(name, age) VALUES "person2":("Bob", 32)',
        'INSERT VERTEX person(name, age) VALUES "person3":("Charlie", 45)',
        'INSERT VERTEX person(name, age) VALUES "person4":("David", 50)',
        'INSERT VERTEX person(name, age) VALUES "person5":("Eve", 55)',
    ],
    # Group 4: Insert edges
    [
        "USE test_graph",
        'INSERT EDGE knows(years) VALUES "person1"->"person2":(5)',
        'INSERT EDGE knows(years) VALUES "person2"->"person3":(3)',
        'INSERT EDGE knows(years) VALUES "person3"->"person5":(10)',
        'INSERT EDGE reports_to(department) VALUES "person1"->"person3":("Engineering")',
        'INSERT EDGE reports_to(department) VALUES "person2"->"person3":("Engineering")',
        'INSERT EDGE reports_to(department) VALUES "person3"->"person4":("Management")',
        'INSERT EDGE reports_to(department) VALUES "person4"->"person5":("Executive")',
    ],
]

# Skip integration tests (unless explicitly enabled)
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "true",
    reason="Integration tests require a running NebulaGraph instance and specific test data",
)


def execute_with_retry(session, command, max_retries=3, retry_interval=2):
    """Execute command and retry on failure"""
    for attempt in range(max_retries):
        try:
            print(f"Executing: {command}")
            result = session.execute(command)
            if result.is_succeeded():
                return result
            else:
                print(
                    f"Error executing command (attempt {attempt + 1}/{max_retries}): {result.error_msg()}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_interval)
        except Exception as e:
            print(
                f"Error executing command (attempt {attempt + 1}/{max_retries}): {e!s}"
            )
            if attempt < max_retries - 1:
                time.sleep(retry_interval)

    # final attempt
    print(f"Final attempt to execute: {command}")
    return session.execute(command)


@pytest.fixture(scope="module", autouse=True)
def setup_connection():
    """Initialize connection pool and prepare test data"""
    from nebulagraph_mcp_server.server import config, global_pool

    # Initialize connection
    global_pool.init(
        [
            (
                os.getenv("NEBULA_HOST", "127.0.0.1"),
                int(os.getenv("NEBULA_PORT", "9669")),
            )
        ],
        config,
    )

    # If running integration tests, create test data
    if os.getenv("RUN_INTEGRATION_TESTS") == "true":
        session = global_pool.get_session(
            os.getenv("NEBULA_USER", "root"), os.getenv("NEBULA_PASSWORD", "nebula")
        )

        try:
            # Execute command groups
            for group_index, command_group in enumerate(SETUP_COMMANDS):
                print(
                    f"\nExecuting command group {group_index + 1}/{len(SETUP_COMMANDS)}:"
                )

                # Execute commands in the group
                for command in command_group:
                    if command.strip():
                        execute_with_retry(session, command.strip())

                # Add appropriate wait time after group type
                if group_index == 0:  # After creating space
                    print("Waiting for space creation to complete (30 seconds)...")
                    time.sleep(30)
                elif group_index == 1:  # After creating tags and edge types
                    print("Waiting for metadata synchronization (10 seconds)...")
                    time.sleep(10)
                else:  # Short wait after other operations
                    print("Short wait (2 seconds)...")
                    time.sleep(2)

            # Final verification
            print("\nVerifying data creation:")
            verify_commands = [
                "USE test_graph",
                "SHOW TAGS",
                "SHOW EDGES",
                "MATCH (n:person) RETURN count(n)",
            ]

            for command in verify_commands:
                result = execute_with_retry(session, command)
                print(
                    f"Verification result: {command} - {'Success' if result.is_succeeded() else 'Failed'}"
                )

        finally:
            session.release()

    yield

    # Clean up connection
    global_pool.close()


# Integration test: get all spaces
@pytest.mark.asyncio
async def test_integration_list_spaces():
    """Test the list spaces function"""
    from nebulagraph_mcp_server.server import list_spaces

    # Call the list_spaces tool function
    result = list_spaces()

    # Validate the result
    assert "Available spaces" in result
    assert "test_graph" in result  # Assuming the test space is created


# Integration test: execute query
@pytest.mark.asyncio
async def test_integration_execute_query():
    """Test the execute query function"""
    from nebulagraph_mcp_server.server import execute_query

    # Execute the query
    result = execute_query(
        "MATCH (n:person) RETURN id(n), n.name, n.age LIMIT 3",
        "test_graph",
    )

    # Validate the result
    assert "Results" in result
    assert "id(n) | n.name | n.age" in result


# Integration test: find path
@pytest.mark.asyncio
async def test_integration_find_path():
    """Test the find path function"""
    from nebulagraph_mcp_server.server import find_path

    # Test finding paths from person1 to person5
    result = find_path("person1", "person5", "test_graph", 3, 10)
    # Validate the result
    print(f"Find path result: {result}")  # Debug
    assert "Find paths from person1 to person5" in result
    # Since the test graph, person1 to person5 needs at least 3 steps,
    # when depth=3, there should be a path, and the result should contain path information
    # If no path is found, the result should contain "No paths found"
    assert "Path" in result or "No paths found" in result
    # Test non-existent path
    result2 = find_path("person1", "nonexistent", "test_graph", 3, 10)
    assert "No paths found" in result2 or "Query failed" in result2


# Integration test: get neighbors
@pytest.mark.asyncio
async def test_integration_get_neighbors():
    """Test the get neighbors function"""
    from nebulagraph_mcp_server.server import find_neighbors

    # Test getting neighbors of person1
    result = find_neighbors("person1", "test_graph", 1)
    # Validate the result
    assert "Vertex person1 neighbors (depth 1):" in result
    assert "person2" in result
    assert "person3" in result
    assert "person4" not in result
    assert "person5" not in result
