"""Plan parsing and management utilities."""

from __future__ import annotations

import re
from typing import Optional

from dsagent.schema.models import PlanStep, PlanState


class PlanParser:
    """Parses and manages agent plans from LLM responses.

    The agent uses a tag-based protocol for structured responses:
    - <plan>...</plan>: Current plan with numbered steps
    - <plan_update>...</plan_update>: Explanation of plan changes
    - <think>...</think>: Agent reasoning (not executed)
    - <code>...</code>: Python code to execute
    - <answer>...</answer>: Final answer (only when plan is complete)

    Example plan format:
        <plan>
        1. [x] Load and explore dataset
        2. [ ] Handle missing values
        3. [ ] Build model
        </plan>
    """

    # Regex patterns for tag extraction
    PLAN_PATTERN = re.compile(r"<plan>(.*?)</plan>", re.DOTALL | re.IGNORECASE)
    PLAN_UPDATE_PATTERN = re.compile(
        r"<plan_update>(.*?)</plan_update>", re.DOTALL | re.IGNORECASE
    )
    CODE_PATTERN = re.compile(r"<code>(.*?)</code>", re.DOTALL | re.IGNORECASE)
    CODE_PARTIAL_PATTERN = re.compile(r"<code>(.*?)$", re.DOTALL | re.IGNORECASE)
    THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
    ANSWER_PATTERN = re.compile(r"<answer>(.*?)</answer>", re.DOTALL | re.IGNORECASE)
    ANSWER_PARTIAL_PATTERN = re.compile(r"<answer>(.*?)$", re.DOTALL | re.IGNORECASE)
    ANSWER_TAG_PATTERN = re.compile(r"<answer>", re.IGNORECASE)

    # Pattern for parsing individual steps
    STEP_PATTERN = re.compile(r"(\d+)\.\s*\[(x| )\]\s*(.+)", re.IGNORECASE)

    @classmethod
    def parse_plan(cls, response: str) -> Optional[PlanState]:
        """Extract and parse the plan from a response.

        Args:
            response: LLM response text

        Returns:
            PlanState if a valid plan is found, None otherwise
        """
        match = cls.PLAN_PATTERN.search(response)
        if not match:
            return None

        plan_text = match.group(1).strip()
        steps = []

        for line in plan_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            step_match = cls.STEP_PATTERN.match(line)
            if step_match:
                number = int(step_match.group(1))
                completed = step_match.group(2).lower() == "x"
                description = step_match.group(3).strip()
                steps.append(
                    PlanStep(number=number, description=description, completed=completed)
                )

        if steps:
            return PlanState(steps=steps, raw_text=plan_text)
        return None

    @classmethod
    def extract_plan_update(cls, response: str) -> Optional[str]:
        """Extract plan update explanation if present.

        Args:
            response: LLM response text

        Returns:
            Update explanation text or None
        """
        match = cls.PLAN_UPDATE_PATTERN.search(response)
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def extract_code(cls, response: str) -> Optional[str]:
        """Extract Python code from response.

        Handles both complete (<code>...</code>) and partial
        (<code>... without closing tag) code blocks.

        Args:
            response: LLM response text

        Returns:
            Python code string or None
        """
        # Try complete code block first
        match = cls.CODE_PATTERN.search(response)
        if match:
            return match.group(1).strip()

        # Try partial code block (stopped at </code>)
        match = cls.CODE_PARTIAL_PATTERN.search(response)
        if match:
            content = match.group(1).strip()
            # Remove trailing markdown code fence if present
            return re.sub(r"```\s*$", "", content).strip() or None

        return None

    @classmethod
    def extract_thinking(cls, response: str) -> Optional[str]:
        """Extract agent thinking/reasoning from response.

        Args:
            response: LLM response text

        Returns:
            Thinking text or None
        """
        match = cls.THINK_PATTERN.search(response)
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def has_final_answer(cls, response: str) -> bool:
        """Check if response contains a final answer tag.

        Args:
            response: LLM response text

        Returns:
            True if <answer> tag is present
        """
        return bool(cls.ANSWER_TAG_PATTERN.search(response))

    @classmethod
    def extract_answer(cls, response: str) -> str:
        """Extract the final answer from response.

        Args:
            response: LLM response text

        Returns:
            Answer text (or full response if no tag found)
        """
        # Try complete answer block
        match = cls.ANSWER_PATTERN.search(response)
        if match:
            return match.group(1).strip()

        # Try partial answer block (stopped at </answer>)
        match = cls.ANSWER_PARTIAL_PATTERN.search(response)
        if match:
            return match.group(1).strip()

        return response

    @classmethod
    def clean_ansi(cls, text: str) -> str:
        """Remove ANSI escape codes from text.

        Args:
            text: Text potentially containing ANSI codes

        Returns:
            Cleaned text
        """
        return re.sub(r"\x1b\[[0-9;]*m", "", text)
