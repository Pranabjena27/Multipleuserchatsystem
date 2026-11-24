"""
Message Processor Module
========================
Demonstrates:
- String operations (regex, parsing, slicing, string interpolation)
- Sets, lists, and dict comprehensions
- Exception handling with custom hierarchy
- Recursion for nested conversation reply trees
"""

import re
from typing import Any


class ProcessingError(Exception):
    """Base exception for message processing failures."""
    pass


class MessageProcessor:
    """
    Handles message sanitization, profanity filtering, link extraction,
    user mentions, and recursive thread hierarchy construction.
    """

    # Academic regex patterns for message tokenization and entity extraction
    MENTION_REGEX = re.compile(r"@([a-zA-Z0-9_]{3,32})")
    URL_REGEX = re.compile(
        r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|"
        r"www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|"
        r"https?:\/\/[a-zA-Z0-9]+\.[^\s]{2,})"
    )
    CODE_BLOCK_REGEX = re.compile(r"```([a-zA-Z0-9_+-]*)\n?(.*?)```", re.DOTALL)

    # Standard profanity lexicon for educational content filtering
    PROFANITY_LIST = {
        "abuse", "badword", "idiot", "stupid", "hate", "spam", "scam",
        "phishing", "fool", "nonsense", "vulgar"
    }

    def __init__(self, profanity_set: set[str] | None = None) -> None:
        """Initialize with default or custom profanity filter list."""
        self.profanity_set = set(profanity_set) if profanity_set else self.PROFANITY_LIST

    def sanitize(self, text: str) -> str:
        """
        Sanitize and normalize raw message string.
        Demonstrates string strip, length checks, and escaping.
        """
        if not isinstance(text, str):
            raise ProcessingError("Message text must be a valid string")

        trimmed = text.strip()
        if not trimmed:
            raise ProcessingError("Message cannot be empty or whitespace only")

        # HTML entity basic escaping for security
        escaped = (
            trimmed.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
        # Neutralize dangerous pseudo-protocols in links or attributes
        sanitized = re.sub(r"(?i)javascript\s*:", "blocked-uri:", escaped)
        sanitized = re.sub(r"(?i)data\s*:\s*text\/html", "blocked-uri:", sanitized)
        sanitized = re.sub(r"(?i)vbscript\s*:", "blocked-uri:", sanitized)
        return sanitized

    def filter_profanity(self, text: str) -> tuple[str, bool]:
        """
        Filter offensive terms replacing them with asterisks.
        Demonstrates loops, string operations, and word boundary regex.
        Returns: (filtered_text, was_flagged)
        """
        flagged = False
        result = text
        for word in self.profanity_set:
            pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            if pattern.search(result):
                flagged = True
                replacement = word[0] + ("*" * (len(word) - 1))
                result = pattern.sub(replacement, result)
        return result, flagged

    def extract_mentions(self, text: str) -> list[str]:
        """
        Extract unique @username tags from message.
        Demonstrates regex findall and set comprehension to remove duplicates.
        """
        matches = self.MENTION_REGEX.findall(text)
        # Using a set to guarantee uniqueness while preserving deterministic sorted order
        unique_mentions = sorted(list({m.lower() for m in matches}))
        return unique_mentions

    def extract_urls(self, text: str) -> list[str]:
        """
        Extract valid URLs from message content.
        Demonstrates regex extraction and list filtering.
        """
        matches = self.URL_REGEX.findall(text)
        return [url.strip() for url in matches]

    def render_markdown_safe(self, text: str) -> str:
        """
        Safely convert basic markdown syntax: **bold**, *italic*, `code`, and @mentions.
        Demonstrates multiple chained regex substitutions.
        """
        # Bold
        formatted = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        # Italic
        formatted = re.sub(r"\*(.+?)\*", r"<em>\1</em>", formatted)
        # Inline code
        formatted = re.sub(
            r"`([^`]+)`",
            r"<code class='chat-inline-code'>\1</code>",
            formatted,
        )
        # Mentions highlight
        formatted = self.MENTION_REGEX.sub(
            r'<span class="chat-mention">@\1</span>', formatted
        )
        # Hyperlinks
        formatted = self.URL_REGEX.sub(
            r'<a href="\1" target="_blank" rel="noopener noreferrer" class="chat-link">\1</a>',
            formatted,
        )
        return formatted

    # =========================================================================
    # RECURSIVE THREAD HIERARCHY (Demonstrating Academic Recursion Requirement)
    # =========================================================================

    def build_nested_thread_tree(
        self, messages: list[dict[str, Any]], parent_id: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Recursively construct a hierarchical reply tree from flat message dictionaries.
        Demonstrates:
        - Base case: no children matching parent_id.
        - Recursive step: for each child, recurse to find its descendant replies.
        """
        tree: list[dict[str, Any]] = []

        for msg in messages:
            # Match messages belonging to this parent level
            if msg.get("parent_id") == parent_id:
                # Recursive call to collect all descendant replies
                children = self.build_nested_thread_tree(
                    messages, parent_id=msg.get("id")
                )
                node = dict(msg)
                node["replies"] = children
                node["reply_count"] = len(children)
                tree.append(node)

        return tree

    def calculate_tree_depth(self, node: dict[str, Any]) -> int:
        """
        Recursively calculate the maximum depth of a message thread branch.
        Demonstrates recursive depth traversal.
        """
        replies = node.get("replies", [])
        if not replies:
            return 1
        # Recursive step across all child branches
        return 1 + max(self.calculate_tree_depth(child) for child in replies)

