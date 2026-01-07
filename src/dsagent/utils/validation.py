"""Validation utilities for DSAgent configuration."""

from __future__ import annotations

import os
from typing import Optional, Tuple


class ConfigurationError(Exception):
    """Raised when there's a configuration issue."""

    pass


def apply_llm_api_base(model: str) -> None:
    """Map LLM_API_BASE to provider-specific base env vars when appropriate."""
    api_base = os.getenv("LLM_API_BASE")
    if not api_base:
        return

    model_lower = model.lower()
    target_env = None

    if model_lower.startswith("azure/"):
        target_env = "AZURE_API_BASE"
    elif model_lower.startswith(("gpt-", "o1", "o3", "openai/")):
        target_env = "OPENAI_API_BASE"

    if target_env and not os.getenv(target_env):
        os.environ[target_env] = api_base


# Mapping of model prefixes to required environment variables
MODEL_PROVIDER_KEYS = {
    # OpenAI models
    "gpt-": "OPENAI_API_KEY",
    "o1": "OPENAI_API_KEY",
    "o3": "OPENAI_API_KEY",
    # Anthropic models
    "claude": "ANTHROPIC_API_KEY",
    "anthropic/": "ANTHROPIC_API_KEY",
    # Google models
    "gemini": "GOOGLE_API_KEY",
    "google/": "GOOGLE_API_KEY",
    # DeepSeek
    "deepseek/": "DEEPSEEK_API_KEY",
    # Azure OpenAI
    "azure/": "AZURE_API_KEY",
    # Local models (no key required)
    "ollama/": None,
    "ollama_chat/": None,
    "local/": None,
}


def get_provider_for_model(model: str) -> Tuple[str, Optional[str]]:
    """Get the provider name and required API key for a model.

    Args:
        model: The model name/identifier

    Returns:
        Tuple of (provider_name, required_env_var or None if no key needed)
    """
    model_lower = model.lower()

    for prefix, env_var in MODEL_PROVIDER_KEYS.items():
        if model_lower.startswith(prefix):
            provider = prefix.rstrip("/-")
            return provider, env_var

    # Default: assume OpenAI-compatible
    return "openai", "OPENAI_API_KEY"


def validate_api_key(model: str) -> None:
    """Validate that the required API key exists for the given model.

    Args:
        model: The model name/identifier

    Raises:
        ConfigurationError: If the required API key is not set
    """
    provider, env_var = get_provider_for_model(model)

    # No key required for local models
    if env_var is None:
        return

    api_key = os.getenv(env_var)

    if not api_key:
        raise ConfigurationError(
            f"Model '{model}' requires {env_var} to be set.\n\n"
            f"Set it using one of these methods:\n"
            f"  1. Environment variable: export {env_var}='your-api-key'\n"
            f"  2. .env file: Add {env_var}=your-api-key to your .env file\n\n"
            f"See .env.example for configuration options."
        )

    # Basic validation of key format
    if env_var == "OPENAI_API_KEY" and not api_key.startswith("sk-"):
        # Note: This is a soft warning, not an error, as key formats may change
        pass

    if env_var == "ANTHROPIC_API_KEY" and not api_key.startswith("sk-ant-"):
        # Note: This is a soft warning, not an error
        pass


def validate_model_name(model: str) -> None:
    """Validate that the model name is reasonable.

    Args:
        model: The model name/identifier

    Raises:
        ConfigurationError: If the model name appears invalid
    """
    if not model or not isinstance(model, str):
        raise ConfigurationError("Model name must be a non-empty string")

    # Check for common mistakes
    model_lower = model.lower()

    # GPT-5 doesn't exist yet
    if "gpt-5" in model_lower:
        raise ConfigurationError(
            f"Model '{model}' does not exist. "
            f"Did you mean 'gpt-4o' or 'gpt-4-turbo'?"
        )

    # Check for typos in common models
    typo_corrections = {
        "gpt4": "gpt-4",
        "gpt4o": "gpt-4o",
        "claude3": "claude-3",
        "claude-sonnet": "claude-3-5-sonnet-20241022",
        "claude-opus": "claude-3-opus-20240229",
    }

    for typo, correction in typo_corrections.items():
        if model_lower == typo:
            raise ConfigurationError(
                f"Model '{model}' appears to be a typo. "
                f"Did you mean '{correction}'?"
            )


def validate_configuration(model: str) -> None:
    """Validate all configuration for running with the given model.

    Args:
        model: The model name/identifier

    Raises:
        ConfigurationError: If any configuration is invalid
    """
    apply_llm_api_base(model)
    # validate_model_name(model)
    validate_api_key(model)
