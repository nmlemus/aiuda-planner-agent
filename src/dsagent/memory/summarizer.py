"""Conversation summarization for long-term memory.

This module provides automatic summarization of conversation history
to manage context window limits while preserving important information.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any

from litellm import completion
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Prompt for summarizing data science conversations
SUMMARIZATION_PROMPT = '''You are summarizing a data science conversation between a user and an AI assistant.

Create a concise summary that captures:
1. **Data**: What datasets were loaded, their structure, and key characteristics
2. **Analysis**: What analyses were performed (EDA, statistics, etc.)
3. **Models**: Any ML models trained, their type, and performance metrics
4. **Visualizations**: Charts/plots created and what they showed
5. **Key Findings**: Important insights or conclusions
6. **Current State**: What variables/objects exist in the kernel

Format the summary as a structured document that another AI can use to continue the conversation.

CONVERSATION TO SUMMARIZE:
{conversation}

CURRENT KERNEL STATE:
{kernel_state}

Provide a summary in this format:

## Session Summary

### Data Loaded
- [List datasets, shapes, key columns]

### Analysis Performed
- [List analyses and key results]

### Models Trained
- [List models with metrics]

### Key Findings
- [List important insights]

### Current State
- [List important variables and their purposes]

### Notes for Continuation
- [Any context needed to continue this work]
'''


class ConversationSummary(BaseModel):
    """A summary of a portion of conversation history."""

    content: str  # The summary text
    messages_summarized: int  # Number of messages included
    created_at: datetime = Field(default_factory=datetime.now)
    start_index: int = 0  # First message index summarized
    end_index: int = 0  # Last message index summarized
    token_estimate: int = 0  # Estimated tokens in original messages

    def to_system_message(self) -> Dict[str, str]:
        """Convert summary to a system message for LLM context."""
        return {
            "role": "system",
            "content": f"## Previous Conversation Summary\n\n{self.content}",
        }


@dataclass
class SummaryConfig:
    """Configuration for conversation summarization."""

    # When to trigger summarization
    max_messages: int = 30  # Summarize when history exceeds this
    keep_recent: int = 10  # Always keep this many recent messages

    # Summarization settings
    model: str = "gpt-4o-mini"  # Model for summarization (cheaper is fine)
    max_summary_tokens: int = 1000  # Max tokens for summary
    temperature: float = 0.3

    # Token estimation (rough approximation)
    avg_tokens_per_message: int = 150

    def should_summarize(self, message_count: int) -> bool:
        """Check if summarization should be triggered."""
        return message_count > self.max_messages

    def get_messages_to_summarize(self, message_count: int) -> int:
        """Get number of messages to include in summary."""
        if message_count <= self.max_messages:
            return 0
        return message_count - self.keep_recent


class ConversationSummarizer:
    """Summarizes conversation history to manage context window.

    When conversations grow long, this class:
    1. Summarizes older messages into a concise format
    2. Preserves recent messages for immediate context
    3. Creates a structured summary that can be injected into prompts

    Example:
        config = SummaryConfig(max_messages=30, keep_recent=10)
        summarizer = ConversationSummarizer(config)

        # Check if summarization needed
        if summarizer.should_summarize(session.history):
            summary = summarizer.summarize(
                messages=session.history.messages,
                kernel_state=session.kernel_snapshot,
            )
            session.history.set_summary(summary)
    """

    def __init__(
        self,
        config: Optional[SummaryConfig] = None,
    ):
        """Initialize the summarizer.

        Args:
            config: Summarization configuration
        """
        self.config = config or SummaryConfig()

    def should_summarize(self, messages: List[Any]) -> bool:
        """Check if the conversation should be summarized.

        Args:
            messages: List of conversation messages

        Returns:
            True if summarization is recommended
        """
        return self.config.should_summarize(len(messages))

    def summarize(
        self,
        messages: List[Any],
        kernel_state: Optional[Dict[str, Any]] = None,
        existing_summary: Optional[ConversationSummary] = None,
    ) -> ConversationSummary:
        """Summarize conversation messages.

        Args:
            messages: List of conversation messages to summarize
            kernel_state: Current kernel state (variables, dataframes, etc.)
            existing_summary: Previous summary to incorporate

        Returns:
            ConversationSummary with the summarized content
        """
        # Determine which messages to summarize
        num_to_summarize = self.config.get_messages_to_summarize(len(messages))
        if num_to_summarize <= 0:
            # Nothing to summarize
            return ConversationSummary(
                content="(No previous context)",
                messages_summarized=0,
            )

        messages_to_summarize = messages[:num_to_summarize]
        start_index = 0
        end_index = num_to_summarize - 1

        # Format messages for summarization
        conversation_text = self._format_messages(messages_to_summarize)

        # Include existing summary if present
        if existing_summary and existing_summary.content:
            conversation_text = (
                f"## Previous Summary:\n{existing_summary.content}\n\n"
                f"## New Messages:\n{conversation_text}"
            )
            start_index = existing_summary.start_index

        # Format kernel state
        kernel_text = self._format_kernel_state(kernel_state)

        # Build prompt
        prompt = SUMMARIZATION_PROMPT.format(
            conversation=conversation_text,
            kernel_state=kernel_text,
        )

        # Call LLM for summarization
        try:
            response = completion(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=self.config.max_summary_tokens,
            )
            summary_text = response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            # Fallback to simple truncation
            summary_text = self._fallback_summary(messages_to_summarize)

        # Estimate tokens
        token_estimate = len(messages_to_summarize) * self.config.avg_tokens_per_message

        return ConversationSummary(
            content=summary_text.strip(),
            messages_summarized=len(messages_to_summarize),
            start_index=start_index,
            end_index=end_index,
            token_estimate=token_estimate,
        )

    def _format_messages(self, messages: List[Any]) -> str:
        """Format messages for summarization prompt.

        Args:
            messages: List of messages

        Returns:
            Formatted string representation
        """
        lines = []
        for i, msg in enumerate(messages):
            # Handle both dict and object messages
            if hasattr(msg, 'role'):
                role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
                content = msg.content
            elif isinstance(msg, dict):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
            else:
                continue

            # Truncate very long messages
            if len(content) > 1000:
                content = content[:1000] + "... [truncated]"

            lines.append(f"[{role.upper()}]: {content}")

        return "\n\n".join(lines)

    def _format_kernel_state(self, kernel_state: Optional[Dict[str, Any]]) -> str:
        """Format kernel state for summarization.

        Args:
            kernel_state: Kernel state dict or snapshot

        Returns:
            Formatted string representation
        """
        if not kernel_state:
            return "(No kernel state available)"

        # Handle KernelSnapshot object
        if hasattr(kernel_state, 'get_context_summary'):
            return kernel_state.get_context_summary()

        # Handle dict
        lines = []

        if 'variables' in kernel_state:
            lines.append("Variables:")
            for name, type_name in kernel_state['variables'].items():
                lines.append(f"  - {name}: {type_name}")

        if 'dataframes' in kernel_state:
            lines.append("\nDataFrames:")
            for name, info in kernel_state['dataframes'].items():
                shape = info.get('shape', [0, 0])
                cols = info.get('columns', [])[:5]
                lines.append(f"  - {name}: {shape[0]}x{shape[1]} rows/cols")
                if cols:
                    lines.append(f"    Columns: {', '.join(cols)}")

        if 'imports' in kernel_state:
            lines.append(f"\nImports: {', '.join(kernel_state['imports'][:10])}")

        return "\n".join(lines) if lines else "(Empty kernel state)"

    def _fallback_summary(self, messages: List[Any]) -> str:
        """Create a simple fallback summary without LLM.

        Args:
            messages: Messages to summarize

        Returns:
            Simple summary string
        """
        user_msgs = []
        code_count = 0

        for msg in messages:
            if hasattr(msg, 'role'):
                role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
                content = msg.content
            elif isinstance(msg, dict):
                role = msg.get('role', '')
                content = msg.get('content', '')
            else:
                continue

            if role == 'user' and content:
                # Keep first 100 chars of user messages
                user_msgs.append(content[:100])
            if '<code>' in str(content):
                code_count += 1

        summary_lines = [
            "## Previous Session Summary (auto-generated)",
            f"- {len(messages)} messages exchanged",
            f"- {code_count} code executions",
            "",
            "User requests included:",
        ]
        for msg in user_msgs[:5]:
            summary_lines.append(f"- {msg}...")

        return "\n".join(summary_lines)


def estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars per token on average).

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    return len(text) // 4
