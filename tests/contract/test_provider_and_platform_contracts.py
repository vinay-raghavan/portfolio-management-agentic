from portfolio_agent_platform import AgentPlatform, get_platform_profile
from portfolio_model_provider import ModelProvider, load_model_provider_config


def test_gemini_is_default_provider() -> None:
    config = load_model_provider_config({})

    assert config.provider == ModelProvider.GEMINI
    assert config.requires_api_key is True
    assert config.local is False


def test_ollama_provider_is_local_and_does_not_require_api_key() -> None:
    config = load_model_provider_config({"LLM_PROVIDER": "ollama"})

    assert config.provider == ModelProvider.OLLAMA
    assert config.base_url == "http://localhost:11434"
    assert config.requires_api_key is False
    assert config.local is True


def test_claude_and_openai_compatible_providers_are_declared() -> None:
    claude = load_model_provider_config({"LLM_PROVIDER": "claude"})
    openai_compatible = load_model_provider_config(
        {
            "LLM_PROVIDER": "openai_compatible",
            "OPENAI_COMPATIBLE_BASE_URL": "http://localhost:4000/v1",
        }
    )

    assert claude.api_key_env == "ANTHROPIC_API_KEY"
    assert openai_compatible.base_url == "http://localhost:4000/v1"


def test_agent_platforms_all_use_mcp_policy_boundary() -> None:
    for platform in AgentPlatform:
        profile = get_platform_profile(platform)

        assert profile.uses_mcp is True

