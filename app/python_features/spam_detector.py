"""
Spam Detector Module
====================
Academic Concepts Demonstrated:
- Mathematical calculations (Shannon Informational Entropy: H(X) = -sum(P(x) * log2(P(x))))
- Sets, dictionaries, and collections (sliding window rate limiter, frequency maps)
- Class design with encapsulation and dataclasses
- Configurable rules, exception handling, string processing, and regex heuristics
"""

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any


class SpamDetectionError(Exception):
    """Custom exception raised when spam evaluation fails unexpectedly."""
    pass


@dataclass
class SpamRules:
    """
    Configurable detection rules for the spam evaluation engine.
    Demonstrates default arguments, dataclasses, and custom types.
    """
    trigger_threshold: float = 0.55
    max_links_allowed: int = 2
    rate_limit_window_seconds: int = 10
    max_messages_per_window: int = 6
    min_entropy_threshold: float = 2.2
    max_caps_ratio: float = 0.70
    custom_keywords: set[str] = field(default_factory=set)


@dataclass
class SpamCheckResult:
    """
    Encapsulates the verdict, metrics, and human-readable explanation of a spam check.
    """
    is_spam: bool
    score: float  # Normalized score from 0.0 (clean) to 1.0 (flagrant spam)
    reasons: list[str] = field(default_factory=list)
    explanation: str = ""
    entropy: float = 0.0
    caps_ratio: float = 0.0
    url_count: int = 0
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a serializable dictionary."""
        return {
            "is_spam": self.is_spam,
            "score": self.score,
            "reasons": self.reasons,
            "explanation": self.explanation,
            "entropy": self.entropy,
            "caps_ratio": self.caps_ratio,
            "url_count": self.url_count,
            "metrics": self.metrics,
        }


class SpamDetector:
    """
    Analyzes message payloads using statistical heuristics, Shannon entropy,
    excessive links, repetitive patterns, keyword sets, and sliding-window rate tracking.
    """

    # Base high-probability spam keywords and phishing phrases
    DEFAULT_SPAM_KEYWORDS = {
        "free crypto", "guaranteed profit", "click here now", "congratulations winner",
        "lottery won", "wire transfer", "fast money", "claim your prize", "100% free",
        "earn cash", "urgent reply", "bank account blocked", "credit card limit",
        "work from home earn", "double your money", "discount pills", "limited offer buy",
        "risk free", "instant payout", "special promo link", "giveaway claim"
    }

    # URL matching regex
    URL_REGEX = re.compile(
        r"(?:https?://|www\.)[^\s/$.?#].[^\s]*",
        re.IGNORECASE,
    )

    def __init__(self, rules: SpamRules | None = None) -> None:
        """
        Initialize the spam detector with optional custom rules.
        Demonstrates dependency injection and dictionary collections.
        """
        self.rules = rules or SpamRules()
        # Merge default keywords with custom keywords using set union
        self.keywords: set[str] = self.DEFAULT_SPAM_KEYWORDS | self.rules.custom_keywords

        # User sliding window tracking: user_id -> list of float epoch timestamps
        self._user_timestamps: dict[int, list[float]] = defaultdict(list)
        # User message repetition tracking: user_id -> list of recent message hashes or strings
        self._user_recent_messages: dict[int, list[str]] = defaultdict(list)

    @staticmethod
    def calculate_shannon_entropy(text: str) -> float:
        """
        Calculate the Shannon Informational Entropy of the input text string.
        Demonstrates mathematical formulas, loops, and dictionary frequency counting.
        Formula: H(X) = - sum( P(x) * log2(P(x)) )
        """
        if not text:
            return 0.0

        length = len(text)
        frequencies: dict[str, int] = defaultdict(int)
        for char in text:
            frequencies[char] += 1

        entropy = 0.0
        for count in frequencies.values():
            prob = count / length
            entropy -= prob * math.log2(prob)

        return round(entropy, 4)

    def check_rate_limit(self, user_id: int) -> tuple[bool, int]:
        """
        Check if user is flooding messages faster than the sliding window threshold.
        Demonstrates list comprehension, time arithmetic, and sliding window cleanup.
        Returns: (is_exceeded, current_window_message_count)
        """
        now = datetime.now(timezone.utc).timestamp()
        timestamps = self._user_timestamps[user_id]

        # Prune timestamps older than the sliding window
        cutoff = now - self.rules.rate_limit_window_seconds
        valid_timestamps = [t for t in timestamps if t >= cutoff]
        valid_timestamps.append(now)
        self._user_timestamps[user_id] = valid_timestamps

        count = len(valid_timestamps)
        is_exceeded = count > self.rules.max_messages_per_window
        return is_exceeded, count

    def check_message_repetition(self, user_id: int, message_text: str) -> tuple[bool, int]:
        """
        Check if the user is repeatedly posting the exact same message.
        Demonstrates list operations, queue trimming, and frequency checks.
        """
        clean = message_text.strip().lower()
        recent = self._user_recent_messages[user_id]

        # Keep last 10 messages
        recent.append(clean)
        if len(recent) > 10:
            recent.pop(0)

        # Count occurrences in the recent buffer
        repeat_count = recent.count(clean)
        is_repeated = repeat_count >= 3
        return is_repeated, repeat_count

    def extract_urls(self, text: str) -> list[str]:
        """
        Extract all web links from text using regular expressions.
        Demonstrates regex findall and string processing.
        """
        return self.URL_REGEX.findall(text)

    def evaluate(self, text: str, user_id: int | None = None) -> SpamCheckResult:
        """
        Perform comprehensive multi-factor spam analysis on message text.
        Demonstrates conditionals, score accumulation, regex, and structured result return.
        """
        try:
            if not isinstance(text, str):
                raise SpamDetectionError("Message content must be a string")

            clean_text = text.strip()
            if not clean_text:
                return SpamCheckResult(
                    is_spam=False,
                    score=0.0,
                    reasons=["Empty message"],
                    explanation="Message is empty or whitespace only.",
                    entropy=0.0,
                    caps_ratio=0.0,
                    url_count=0,
                )

            score = 0.0
            reasons: list[str] = []
            text_lower = clean_text.lower()
            total_chars = len(clean_text)

            # -------------------------------------------------------------
            # Factor 1: Repeated Message Frequency & Rate Limiting
            # -------------------------------------------------------------
            frequency_count = 0
            repeat_count = 1
            if user_id is not None:
                rate_exceeded, frequency_count = self.check_rate_limit(user_id)
                if rate_exceeded:
                    score += 0.45
                    reasons.append(
                        f"High message frequency: {frequency_count} messages sent in {self.rules.rate_limit_window_seconds}s"
                    )

                is_repeated, repeat_count = self.check_message_repetition(user_id, clean_text)
                if is_repeated:
                    score += 0.40
                    reasons.append(
                        f"Duplicate message flood: repeated {repeat_count} times recently"
                    )

            # -------------------------------------------------------------
            # Factor 2: Excessive Links
            # -------------------------------------------------------------
            urls = self.extract_urls(clean_text)
            url_count = len(urls)
            if url_count > self.rules.max_links_allowed:
                score += 0.35 + min(0.30, (url_count - self.rules.max_links_allowed) * 0.15)
                reasons.append(
                    f"Excessive hyperlinks: detected {url_count} URLs (max allowed: {self.rules.max_links_allowed})"
                )

            # -------------------------------------------------------------
            # Factor 3: Suspicious Keywords
            # -------------------------------------------------------------
            matched_keywords = [kw for kw in self.keywords if kw in text_lower]
            if matched_keywords:
                weight = min(0.60, len(matched_keywords) * 0.30)
                score += weight
                reasons.append(f"Suspicious spam phrases detected: {', '.join(matched_keywords)}")

            # -------------------------------------------------------------
            # Factor 4: Informational (Shannon) Entropy & Repetitive Patterns
            # -------------------------------------------------------------
            entropy = self.calculate_shannon_entropy(clean_text)
            if total_chars > 20 and entropy < self.rules.min_entropy_threshold:
                score += 0.35
                reasons.append(
                    f"Low informational entropy ({entropy:.2f}): excessive repetitive text"
                )

            # Character flood check (e.g., 'aaaaaa' or '!!!!!!!!')
            if re.search(r"(.)\1{5,}", clean_text):
                score += 0.25
                reasons.append("Character flood pattern detected (consecutive identical characters)")

            # Word repetition check (e.g. 'win win win win')
            words = re.findall(r"\b\w+\b", text_lower)
            if len(words) >= 5:
                word_counts: dict[str, int] = defaultdict(int)
                for w in words:
                    word_counts[w] += 1
                max_repeat = max(word_counts.values())
                repeat_ratio = max_repeat / len(words)
                if repeat_ratio >= 0.70:
                    score += 0.55
                    reasons.append(
                        f"Severe repetitive word flooding detected ('{max(word_counts, key=word_counts.get)}' repeated {max_repeat} times)"
                    )
                elif repeat_ratio > 0.45:
                    score += 0.30
                    reasons.append(
                        f"Repetitive word flooding detected ('{max(word_counts, key=word_counts.get)}' repeated {max_repeat} times)"
                    )

            # -------------------------------------------------------------
            # Factor 5: Excessive Uppercase Characters
            # -------------------------------------------------------------
            alpha_chars = [c for c in clean_text if c.isalpha()]
            caps_ratio = 0.0
            if len(alpha_chars) >= 8:
                caps_count = sum(1 for c in alpha_chars if c.isupper())
                caps_ratio = caps_count / len(alpha_chars)
                if caps_ratio > self.rules.max_caps_ratio:
                    score += 0.30
                    reasons.append(
                        f"Excessive capitalization: {round(caps_ratio * 100)}% uppercase characters"
                    )

            # Normalize final score between 0.0 and 1.0
            final_score = round(min(1.0, score), 2)
            is_spam = final_score >= self.rules.trigger_threshold

            # Construct human-readable explanation
            if is_spam:
                explanation = (
                    f"Flagged as SPAM with confidence score {final_score:.2f} "
                    f"(threshold {self.rules.trigger_threshold:.2f}). Violations: "
                    + "; ".join(reasons)
                    + "."
                )
            elif reasons:
                explanation = (
                    f"Message contains suspicious markers ({', '.join(reasons)}), "
                    f"but score {final_score:.2f} is below spam threshold {self.rules.trigger_threshold:.2f}."
                )
            else:
                explanation = "Message evaluated as clean. No spam markers detected."

            metrics = {
                "entropy": entropy,
                "caps_ratio": round(caps_ratio, 2),
                "url_count": url_count,
                "matched_keywords_count": len(matched_keywords),
                "frequency_count": frequency_count,
                "repeat_count": repeat_count,
            }

            return SpamCheckResult(
                is_spam=is_spam,
                score=final_score,
                reasons=reasons,
                explanation=explanation,
                entropy=entropy,
                caps_ratio=round(caps_ratio, 2),
                url_count=url_count,
                metrics=metrics,
            )

        except Exception as exc:
            if isinstance(exc, SpamDetectionError):
                raise
            raise SpamDetectionError(f"Error during spam evaluation: {str(exc)}") from exc
