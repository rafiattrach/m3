from m3.core.mcp_config_generator import MCPConfigGenerator
from m3.core.mcp_config_generator.mcp_config_generators.claude_mcp_config import (
    ClaudeConfigGenerator,
)
from m3.core.mcp_config_generator.mcp_config_generators.fast_mcp_config import (
    FastMCPConfigGenerator,
)
from m3.core.mcp_config_generator.mcp_config_generators.universal_mcp_config import (
    UniversalConfigGenerator,
)

ALL_MCP_CONFIG_GENERATORS: dict[str, type[MCPConfigGenerator]] = {
    "fastmcp": FastMCPConfigGenerator,
    "claude": ClaudeConfigGenerator,
    "universal": UniversalConfigGenerator,
}
