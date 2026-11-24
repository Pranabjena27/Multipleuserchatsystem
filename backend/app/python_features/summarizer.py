"""
Conversation Summarizer Module
==============================
Academic Concepts Demonstrated:
- Extractive text summarization algorithms in pure Python
- List comprehensions, dictionary sorting with lambda functions
- Term frequency calculations and sentence ranking
- Set operations for stopword filtering
- Exception handling with custom exception hierarchy
"""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any


class SummarizerError(Exception):
    """Custom exception raised when conversation summarization fails."""
    pass


@dataclass
class SummaryResult:
    """Encapsulates the structured outcome of a conversation summarization pass."""
    summary: str
    bullets: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    key_topics: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    message_count: int = 0
    participant_count: int = 0
    participants: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a serializable dictionary."""
        return {
            "summary": self.summary,
            "bullets": self.bullets,
            "action_items": self.action_items,
            "key_topics": self.key_topics,
            "decisions": self.decisions,
            "message_count": self.message_count,
            "participant_count": self.participant_count,
            "participants": self.participants,
        }


class ConversationSummarizer:
    """
    Summarizes multi-user conversation streams into concise bullet points,
    extracts action items, decisions, and top discussed vocabulary.
    Handles empty, brief, and very long conversation histories gracefully.
    """

    # Comprehensive set of common English stopwords to filter non-informative terms
    STOPWORDS: set[str] = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an",
        "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
        "before", "being", "below", "between", "both", "but", "by", "can",
        "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
        "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
        "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't",
        "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers",
        "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
        "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its",
        "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
        "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
        "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
        "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't",
        "so", "some", "such", "than", "that", "that's", "the", "their", "theirs",
        "them", "themselves", "then", "there", "there's", "these", "they",
        "they'd", "they'll", "they're", "they've", "this", "those", "through",
        "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
        "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's",
        "when", "when's", "where", "where's", "which", "while", "who", "who's",
        "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you",
        "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
        "yourselves", "ok", "okay", "yeah", "yes", "sure", "hey", "hello", "hi", "bye"
    }

    ACTION_MARKERS: set[str] = {
        "todo", "to-do", "will fix", "will do", "working on", "assigned",
        "please", "deadline", "by tomorrow", "we need to", "i need to",
        "plan", "scheduled", "meeting", "submit", "deliver", "review", "test"
    }

    DECISION_MARKERS: set[str] = {
        "decided", "agreed", "finalized", "approved", "confirmed",
        "solution is", "fixed it", "resolved", "conclusion", "settled"
    }

    def __init__(self, max_summary_sentences: int = 5, max_history_limit: int = 500) -> None:
        """
        Configure the summarizer sentence budget and safety history limit.
        Demonstrates constructor initialization and type hints.
        """
        self.max_summary_sentences = max_summary_sentences
        self.max_history_limit = max_history_limit

    def _clean_and_tokenize(self, text: str) -> list[str]:
        """
        Convert string to a list of lowercase content tokens excluding stopwords.
        Demonstrates regular expression word matching and set membership checking.
        """
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        return [w for w in words if w not in self.STOPWORDS]

    def summarize(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Summarize a list of message dictionaries.
        Demonstrates:
        - Filtering with list comprehension
        - Frequency counting using Counter
        - Sentence scoring algorithms
        - Action item and decision extraction
        - Graceful handling of empty or very long chat streams
        """
        try:
            if not isinstance(messages, list):
                raise SummarizerError("Messages parameter must be a list of dictionaries")

            # Handle empty conversation
            if not messages:
                return SummaryResult(
                    summary="No messages available in this conversation to summarize.",
                    bullets=[],
                    action_items=[],
                    key_topics=[],
                    decisions=[],
                    message_count=0,
                    participant_count=0,
                    participants=[],
                ).to_dict()

            # Filter valid text messages
            valid_msgs = [
                m for m in messages
                if not m.get("is_deleted")
                and m.get("content")
                and m.get("message_type") in ("text", None)
                and m.get("content") != "[Message deleted]"
            ]

            if not valid_msgs:
                return SummaryResult(
                    summary="No readable text messages found in this conversation to summarize.",
                    bullets=[],
                    action_items=[],
                    key_topics=[],
                    decisions=[],
                    message_count=0,
                    participant_count=0,
                    participants=[],
                ).to_dict()

            # Safety cap for very long conversations: sample latest messages to keep summarization fast
            if len(valid_msgs) > self.max_history_limit:
                valid_msgs = valid_msgs[-self.max_history_limit:]

            # 1. Collect words and calculate term frequency across conversation
            all_words: list[str] = []
            participants_set: set[str] = set()

            for msg in valid_msgs:
                sender = msg.get("sender_name") or msg.get("sender_username") or "User"
                participants_set.add(sender)
                tokens = self._clean_and_tokenize(msg["content"])
                all_words.extend(tokens)

            word_frequencies = Counter(all_words)
            max_freq = max(word_frequencies.values()) if word_frequencies else 1

            # Normalized word weights: word -> weight in [0.0, 1.0]
            word_weights = {
                word: count / max_freq for word, count in word_frequencies.items()
            }

            # 2. Score each message sentence
            scored_messages: list[tuple[float, int, dict[str, Any]]] = []
            action_items: list[str] = []
            decisions: list[str] = []

            for index, msg in enumerate(valid_msgs):
                content = msg["content"].strip()
                content_lower = content.lower()
                sender = msg.get("sender_name") or msg.get("sender_username") or "User"
                tokens = self._clean_and_tokenize(content)

                # Check action items
                if any(marker in content_lower for marker in self.ACTION_MARKERS):
                    action_items.append(f"{sender}: {content}")

                # Check decision markers
                if any(dm in content_lower for dm in self.DECISION_MARKERS):
                    decisions.append(f"{sender}: {content}")

                if not tokens:
                    continue

                # Base score: average term importance
                base_score = sum(word_weights.get(t, 0.0) for t in tokens) / len(tokens)

                # Boost for decisions or actions
                decision_boost = 0.40 if any(dm in content_lower for dm in self.DECISION_MARKERS) else 0.0
                action_boost = 0.30 if any(am in content_lower for am in self.ACTION_MARKERS) else 0.0

                # Slight recency boost for later messages
                recency_boost = (index / len(valid_msgs)) * 0.15

                total_score = base_score + decision_boost + action_boost + recency_boost
                scored_messages.append((total_score, index, msg))

            # 3. Sort messages by score descending, pick top sentences
            scored_messages.sort(key=lambda item: item[0], reverse=True)
            top_entries = scored_messages[: self.max_summary_sentences]

            # Re-sort top sentences back by original chronological order
            top_entries.sort(key=lambda item: item[1])

            bullets: list[str] = []
            for _, _, msg in top_entries:
                sender = msg.get("sender_name") or msg.get("sender_username") or "User"
                bullets.append(f"{sender}: {msg['content']}")

            # Top 5 discussed topics
            top_topics = [word for word, _ in word_frequencies.most_common(5)]

            # Generate synthetic narrative overview
            if bullets:
                summary_text = (
                    f"Conversation involving {len(participants_set)} participant(s) across "
                    f"{len(valid_msgs)} messages. Key discussion points: "
                    + " ".join(bullets)
                )
            else:
                summary_text = "Conversation too brief to extract meaningful summary bullets."

            result = SummaryResult(
                summary=summary_text,
                bullets=bullets,
                action_items=action_items[:6],
                key_topics=top_topics,
                decisions=decisions[:5],
                message_count=len(valid_msgs),
                participant_count=len(participants_set),
                participants=sorted(list(participants_set)),
            )

            return result.to_dict()

        except Exception as exc:
            if isinstance(exc, SummarizerError):
                raise
            raise SummarizerError(f"Error during summarization: {str(exc)}") from exc
