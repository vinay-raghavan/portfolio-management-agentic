from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AgentPlatform(StrEnum):
    ADK = "adk"
    CODEX = "codex"
    CLAUDE_CODE = "claude_code"
    GEMINI_CLI = "gemini_cli"
    GENERIC_MCP_CLIENT = "generic_mcp_client"


@dataclass(frozen=True)
class PlatformProfile:
    platform: AgentPlatform
    guidance_file: str | None
    uses_mcp: bool
    notes: tuple[str, ...]


PLATFORM_PROFILES = {
    AgentPlatform.ADK: PlatformProfile(
        platform=AgentPlatform.ADK,
        guidance_file="apps/agent-service/AGENTS.md",
        uses_mcp=True,
        notes=("Primary Kaggle runtime.", "Uses ADK scaffold and eval loop."),
    ),
    AgentPlatform.CODEX: PlatformProfile(
        platform=AgentPlatform.CODEX,
        guidance_file="AGENTS.md",
        uses_mcp=True,
        notes=("Uses repo skills, tests, and MCP tools.",),
    ),
    AgentPlatform.CLAUDE_CODE: PlatformProfile(
        platform=AgentPlatform.CLAUDE_CODE,
        guidance_file="CLAUDE.md",
        uses_mcp=True,
        notes=("Uses Claude Code guidance and the same MCP policy boundary.",),
    ),
    AgentPlatform.GEMINI_CLI: PlatformProfile(
        platform=AgentPlatform.GEMINI_CLI,
        guidance_file="GEMINI.md",
        uses_mcp=True,
        notes=("Uses Gemini guidance while preserving provider neutrality.",),
    ),
    AgentPlatform.GENERIC_MCP_CLIENT: PlatformProfile(
        platform=AgentPlatform.GENERIC_MCP_CLIENT,
        guidance_file=None,
        uses_mcp=True,
        notes=("Consumes the MCP server directly.",),
    ),
}


def get_platform_profile(platform: str | AgentPlatform) -> PlatformProfile:
    return PLATFORM_PROFILES[AgentPlatform(platform)]

