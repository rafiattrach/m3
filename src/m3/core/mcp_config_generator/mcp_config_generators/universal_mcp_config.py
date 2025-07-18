import json
import logging

from beartype import beartype
from beartype.typing import List, Optional

from m3.core.mcp_config_generator.base import MCPConfigGenerator

logger = logging.getLogger(__name__)


@beartype
class UniversalConfigGenerator(MCPConfigGenerator):  # pragma: no cover
    @classmethod
    def generate(
        cls,
        m3: "m3.m3.M3",  # noqa: F821
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        module_name: Optional[str] = None,
        pipeline_config_path: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> dict:
        env = m3.config.env_vars.copy()
        if pipeline_config_path:
            env["M3_CONFIG_PATH"] = pipeline_config_path

        logger.debug("Generating Universal config")

        config = m3.__dict__
        config["env_vars"] = env

        if save_path:
            with open(save_path, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"✅ Universal config saved to {save_path}.")

        logger.debug("Universal config generated successfully")
        return config
