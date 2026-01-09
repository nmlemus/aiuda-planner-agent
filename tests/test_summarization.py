"""Tests for conversation summarization (Phase 5)."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from dsagent.memory import ConversationSummarizer, SummaryConfig, ConversationSummary
from dsagent.session.models import ConversationMessage, ConversationHistory, MessageRole


class TestSummaryConfig:
    """Tests for SummaryConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SummaryConfig()
        assert config.max_messages == 30
        assert config.keep_recent == 10
        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.3

    def test_should_summarize(self):
        """Test should_summarize threshold check."""
        config = SummaryConfig(max_messages=30)

        # Below threshold
        assert not config.should_summarize(29)
        assert not config.should_summarize(30)

        # Above threshold
        assert config.should_summarize(31)
        assert config.should_summarize(50)

    def test_get_messages_to_summarize(self):
        """Test calculation of messages to summarize."""
        config = SummaryConfig(max_messages=30, keep_recent=10)

        # No summarization needed
        assert config.get_messages_to_summarize(20) == 0
        assert config.get_messages_to_summarize(30) == 0

        # Summarization needed
        assert config.get_messages_to_summarize(35) == 25  # 35 - 10 = 25
        assert config.get_messages_to_summarize(50) == 40  # 50 - 10 = 40


class TestConversationSummary:
    """Tests for ConversationSummary model."""

    def test_create_summary(self):
        """Test creating a conversation summary."""
        summary = ConversationSummary(
            content="## Session Summary\n- Loaded data\n- Ran analysis",
            messages_summarized=20,
            start_index=0,
            end_index=19,
            token_estimate=3000,
        )

        assert summary.content == "## Session Summary\n- Loaded data\n- Ran analysis"
        assert summary.messages_summarized == 20
        assert summary.start_index == 0
        assert summary.end_index == 19

    def test_to_system_message(self):
        """Test conversion to system message format."""
        summary = ConversationSummary(
            content="Test summary content",
            messages_summarized=10,
        )

        msg = summary.to_system_message()
        assert msg["role"] == "system"
        assert "Previous Conversation Summary" in msg["content"]
        assert "Test summary content" in msg["content"]


class TestConversationSummarizer:
    """Tests for ConversationSummarizer."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        summarizer = ConversationSummarizer()
        assert summarizer.config.max_messages == 30

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = SummaryConfig(max_messages=50, keep_recent=15)
        summarizer = ConversationSummarizer(config=config)
        assert summarizer.config.max_messages == 50
        assert summarizer.config.keep_recent == 15

    def test_should_summarize(self):
        """Test should_summarize check."""
        summarizer = ConversationSummarizer(
            config=SummaryConfig(max_messages=30)
        )

        # Create mock messages
        short_messages = [Mock() for _ in range(20)]
        long_messages = [Mock() for _ in range(35)]

        assert not summarizer.should_summarize(short_messages)
        assert summarizer.should_summarize(long_messages)

    @patch("dsagent.memory.summarizer.completion")
    def test_summarize_calls_llm(self, mock_completion):
        """Test that summarize calls the LLM."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "## Session Summary\n- Test summary"
        mock_completion.return_value = mock_response

        summarizer = ConversationSummarizer(
            config=SummaryConfig(max_messages=5, keep_recent=2)
        )

        # Create messages
        messages = [
            ConversationMessage.user("Message 1"),
            ConversationMessage.assistant("Response 1"),
            ConversationMessage.user("Message 2"),
            ConversationMessage.assistant("Response 2"),
            ConversationMessage.user("Message 3"),
            ConversationMessage.assistant("Response 3"),
        ]

        summary = summarizer.summarize(messages)

        # Verify LLM was called
        assert mock_completion.called
        assert summary.content == "## Session Summary\n- Test summary"
        assert summary.messages_summarized == 4  # 6 - 2 = 4

    def test_summarize_no_messages_needed(self):
        """Test summarize when no messages need summarization."""
        summarizer = ConversationSummarizer(
            config=SummaryConfig(max_messages=30, keep_recent=10)
        )

        messages = [ConversationMessage.user("Test") for _ in range(5)]
        summary = summarizer.summarize(messages)

        assert summary.messages_summarized == 0
        assert summary.content == "(No previous context)"

    @patch("dsagent.memory.summarizer.completion")
    def test_summarize_with_kernel_state(self, mock_completion):
        """Test summarize with kernel state context."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary with kernel info"
        mock_completion.return_value = mock_response

        summarizer = ConversationSummarizer(
            config=SummaryConfig(max_messages=3, keep_recent=1)
        )

        messages = [
            ConversationMessage.user("Load data"),
            ConversationMessage.assistant("Done"),
            ConversationMessage.user("Analyze"),
            ConversationMessage.assistant("Done"),
        ]

        kernel_state = {
            "variables": {"df": "DataFrame"},
            "dataframes": {"df": {"shape": [100, 5], "columns": ["a", "b"]}},
            "imports": ["pandas", "numpy"],
        }

        summary = summarizer.summarize(messages, kernel_state=kernel_state)

        # Check the prompt includes kernel state
        call_args = mock_completion.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "Variables:" in prompt or "DataFrame" in prompt

    @patch("dsagent.memory.summarizer.completion")
    def test_summarize_with_existing_summary(self, mock_completion):
        """Test summarize with existing summary to incorporate."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Updated summary"
        mock_completion.return_value = mock_response

        summarizer = ConversationSummarizer(
            config=SummaryConfig(max_messages=3, keep_recent=1)
        )

        messages = [
            ConversationMessage.user("New message 1"),
            ConversationMessage.assistant("Response 1"),
            ConversationMessage.user("New message 2"),
            ConversationMessage.assistant("Response 2"),
        ]

        existing = ConversationSummary(
            content="Previous work summary",
            messages_summarized=10,
            start_index=0,
            end_index=9,
        )

        summary = summarizer.summarize(messages, existing_summary=existing)

        # Verify existing summary was included
        call_args = mock_completion.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "Previous Summary" in prompt
        assert summary.start_index == 0  # Should preserve original start

    @patch("dsagent.memory.summarizer.completion")
    def test_summarize_fallback_on_error(self, mock_completion):
        """Test fallback summary when LLM fails."""
        mock_completion.side_effect = Exception("API Error")

        summarizer = ConversationSummarizer(
            config=SummaryConfig(max_messages=3, keep_recent=1)
        )

        messages = [
            ConversationMessage.user("Test message"),
            ConversationMessage.assistant("Test response"),
            ConversationMessage.user("Another message"),
            ConversationMessage.assistant("Another response"),
        ]

        summary = summarizer.summarize(messages)

        # Should get fallback summary
        assert "auto-generated" in summary.content
        assert "messages exchanged" in summary.content

    def test_format_messages(self):
        """Test message formatting for summarization."""
        summarizer = ConversationSummarizer()

        messages = [
            ConversationMessage.user("Hello"),
            ConversationMessage.assistant("Hi there!"),
        ]

        formatted = summarizer._format_messages(messages)

        assert "[USER]:" in formatted
        assert "[ASSISTANT]:" in formatted
        assert "Hello" in formatted
        assert "Hi there!" in formatted

    def test_format_messages_truncation(self):
        """Test that long messages are truncated."""
        summarizer = ConversationSummarizer()

        long_content = "x" * 2000  # Very long message
        messages = [ConversationMessage.user(long_content)]

        formatted = summarizer._format_messages(messages)

        # Should be truncated with indicator
        assert "[truncated]" in formatted
        assert len(formatted) < len(long_content)

    def test_format_kernel_state(self):
        """Test kernel state formatting."""
        summarizer = ConversationSummarizer()

        kernel_state = {
            "variables": {"x": "int", "y": "float"},
            "dataframes": {"df": {"shape": [100, 5], "columns": ["a", "b", "c"]}},
            "imports": ["pandas", "numpy", "sklearn"],
        }

        formatted = summarizer._format_kernel_state(kernel_state)

        assert "Variables:" in formatted
        assert "x: int" in formatted
        assert "DataFrames:" in formatted
        assert "100x5" in formatted
        assert "Imports:" in formatted
        assert "pandas" in formatted

    def test_format_kernel_state_empty(self):
        """Test kernel state formatting with empty state."""
        summarizer = ConversationSummarizer()

        assert "(No kernel state available)" in summarizer._format_kernel_state(None)
        # Empty dict also returns "No kernel state available" since there's nothing to format
        assert "(No kernel state available)" in summarizer._format_kernel_state({})


class TestConversationHistorySummary:
    """Tests for summary methods in ConversationHistory."""

    def test_needs_summarization(self):
        """Test needs_summarization check."""
        history = ConversationHistory()

        # Add messages below threshold
        for i in range(25):
            history.add_user(f"Message {i}")

        assert not history.needs_summarization(threshold=30)

        # Add more to exceed threshold
        for i in range(10):
            history.add_user(f"More {i}")

        assert history.needs_summarization(threshold=30)

    def test_get_messages_for_summary(self):
        """Test getting messages for summarization."""
        history = ConversationHistory()

        for i in range(20):
            history.add_user(f"Message {i}")

        # Keep 5 recent
        to_summarize = history.get_messages_for_summary(keep_recent=5)

        assert len(to_summarize) == 15
        assert to_summarize[-1].content == "Message 14"  # Up to but not including last 5

    def test_set_summary(self):
        """Test setting a summary."""
        history = ConversationHistory()

        history.set_summary("Test summary content", messages_covered=20)

        assert history.summary == "Test summary content"
        assert history.summary_messages_count == 20
        assert history.summary_created_at is not None

    def test_apply_summary(self):
        """Test applying summary (removing old messages)."""
        history = ConversationHistory()

        for i in range(30):
            history.add_user(f"Message {i}")

        history.set_summary("Summary", messages_covered=20)
        removed = history.apply_summary(keep_recent=10)

        assert removed == 20
        assert len(history.messages) == 10
        assert history.truncated_count == 20
        # Should keep the most recent 10
        assert history.messages[0].content == "Message 20"

    def test_to_llm_messages_with_summary(self):
        """Test LLM message generation includes summary."""
        history = ConversationHistory()

        # Add some messages and a summary
        history.add_user("Recent message")
        history.add_assistant("Recent response")
        history.set_summary("Previous conversation summary", messages_covered=50)

        messages = history.to_llm_messages()

        # Should have summary injected
        summary_found = False
        for msg in messages:
            if "Previous conversation summary" in msg.get("content", ""):
                summary_found = True
                break

        assert summary_found


class TestEstimateTokens:
    """Tests for token estimation utility."""

    def test_estimate_tokens(self):
        """Test rough token estimation."""
        from dsagent.memory.summarizer import estimate_tokens

        text = "Hello world"  # 11 chars
        tokens = estimate_tokens(text)

        # ~4 chars per token
        assert tokens == 2  # 11 // 4 = 2

    def test_estimate_tokens_long_text(self):
        """Test token estimation for longer text."""
        from dsagent.memory.summarizer import estimate_tokens

        text = "x" * 1000  # 1000 chars
        tokens = estimate_tokens(text)

        assert tokens == 250  # 1000 // 4 = 250


class TestIntegration:
    """Integration tests for summarization flow."""

    @patch("dsagent.memory.summarizer.completion")
    def test_full_summarization_flow(self, mock_completion):
        """Test complete summarization workflow."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """## Session Summary

### Data Loaded
- sales_data.csv: 1000 rows, 10 columns

### Analysis Performed
- Basic statistics computed
- Correlation analysis done

### Key Findings
- Revenue increased 25% YoY
"""
        mock_completion.return_value = mock_response

        # Create history with many messages
        history = ConversationHistory()
        for i in range(35):
            if i % 2 == 0:
                history.add_user(f"User message {i}")
            else:
                history.add_assistant(f"Assistant response {i}")

        # Create summarizer
        config = SummaryConfig(max_messages=30, keep_recent=10)
        summarizer = ConversationSummarizer(config=config)

        # Check summarization needed
        assert summarizer.should_summarize(history.messages)

        # Get messages to summarize
        to_summarize = history.get_messages_for_summary(keep_recent=10)
        assert len(to_summarize) == 25

        # Perform summarization
        summary = summarizer.summarize(history.messages)

        # Apply to history
        history.set_summary(summary.content, summary.messages_summarized)
        removed = history.apply_summary(keep_recent=10)

        # Verify results
        assert removed == 25
        assert len(history.messages) == 10
        assert "Session Summary" in history.summary

        # Verify LLM messages include summary
        llm_messages = history.to_llm_messages()
        summary_in_context = any(
            "Session Summary" in msg.get("content", "")
            for msg in llm_messages
        )
        assert summary_in_context
