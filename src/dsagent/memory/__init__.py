"""Memory management for long conversations.

This module provides tools for managing conversation history that exceeds
the LLM context window, including:

- Automatic summarization of old messages
- Summary storage and retrieval
- Context window management

Example:
    from dsagent.memory import ConversationSummarizer, SummaryConfig

    summarizer = ConversationSummarizer(model="gpt-4o")
    summary = summarizer.summarize(messages)
"""

from dsagent.memory.summarizer import (
    ConversationSummarizer,
    SummaryConfig,
    ConversationSummary,
)

__all__ = [
    "ConversationSummarizer",
    "SummaryConfig",
    "ConversationSummary",
]
