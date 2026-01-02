"""Tests for configuration validation utilities."""

import os
import pytest
from unittest.mock import patch

from dsagent.utils.validation import (
    ConfigurationError,
    get_provider_for_model,
    validate_api_key,
    validate_model_name,
    validate_configuration,
)


class TestGetProviderForModel:
    """Tests for get_provider_for_model function."""

    def test_openai_models(self):
        """Test OpenAI model detection."""
        assert get_provider_for_model("gpt-4o") == ("gpt", "OPENAI_API_KEY")
        assert get_provider_for_model("gpt-4-turbo") == ("gpt", "OPENAI_API_KEY")
        assert get_provider_for_model("gpt-3.5-turbo") == ("gpt", "OPENAI_API_KEY")
        assert get_provider_for_model("o1-preview") == ("o1", "OPENAI_API_KEY")

    def test_anthropic_models(self):
        """Test Anthropic model detection."""
        assert get_provider_for_model("claude-3-5-sonnet-20241022") == ("claude", "ANTHROPIC_API_KEY")
        assert get_provider_for_model("claude-3-opus-20240229") == ("claude", "ANTHROPIC_API_KEY")
        assert get_provider_for_model("anthropic/claude-3-sonnet") == ("anthropic", "ANTHROPIC_API_KEY")

    def test_google_models(self):
        """Test Google model detection."""
        assert get_provider_for_model("gemini-pro") == ("gemini", "GOOGLE_API_KEY")
        assert get_provider_for_model("gemini-1.5-pro") == ("gemini", "GOOGLE_API_KEY")
        assert get_provider_for_model("google/gemini-pro") == ("google", "GOOGLE_API_KEY")

    def test_azure_models(self):
        """Test Azure model detection."""
        assert get_provider_for_model("azure/gpt-4") == ("azure", "AZURE_API_KEY")

    def test_ollama_models(self):
        """Test Ollama models (no key required)."""
        assert get_provider_for_model("ollama/llama3") == ("ollama", None)
        assert get_provider_for_model("ollama_chat/codellama") == ("ollama_chat", None)

    def test_unknown_model_defaults_to_openai(self):
        """Test unknown models default to OpenAI."""
        assert get_provider_for_model("some-unknown-model") == ("openai", "OPENAI_API_KEY")


class TestValidateApiKey:
    """Tests for validate_api_key function."""

    def test_valid_openai_key(self):
        """Test with valid OpenAI key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            # Should not raise
            validate_api_key("gpt-4o")

    def test_missing_openai_key(self):
        """Test with missing OpenAI key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_api_key("gpt-4o")
            assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_valid_anthropic_key(self):
        """Test with valid Anthropic key."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test123"}):
            validate_api_key("claude-3-5-sonnet-20241022")

    def test_missing_anthropic_key(self):
        """Test with missing Anthropic key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_api_key("claude-3-opus-20240229")
            assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_ollama_no_key_required(self):
        """Test Ollama models don't require API key."""
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise
            validate_api_key("ollama/llama3")


class TestValidateModelName:
    """Tests for validate_model_name function."""

    def test_valid_model_names(self):
        """Test valid model names."""
        validate_model_name("gpt-4o")
        validate_model_name("claude-3-5-sonnet-20241022")
        validate_model_name("ollama/llama3")

    def test_empty_model_name(self):
        """Test empty model name raises error."""
        with pytest.raises(ConfigurationError):
            validate_model_name("")

    def test_gpt5_not_exists(self):
        """Test GPT-5 doesn't exist yet."""
        with pytest.raises(ConfigurationError) as exc_info:
            validate_model_name("gpt-5")
        assert "does not exist" in str(exc_info.value)
        assert "gpt-4o" in str(exc_info.value)

    def test_typo_corrections(self):
        """Test common typos are caught."""
        with pytest.raises(ConfigurationError) as exc_info:
            validate_model_name("gpt4o")
        assert "typo" in str(exc_info.value).lower()


class TestValidateConfiguration:
    """Tests for validate_configuration function."""

    def test_valid_configuration(self):
        """Test valid configuration passes."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            validate_configuration("gpt-4o")

    def test_invalid_model_name(self):
        """Test invalid model name is caught."""
        with pytest.raises(ConfigurationError):
            validate_configuration("gpt-5")

    def test_missing_api_key(self):
        """Test missing API key is caught."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError):
                validate_configuration("gpt-4o")
