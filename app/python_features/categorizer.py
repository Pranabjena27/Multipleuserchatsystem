"""
Message Categorizer Module
==========================
Academic Concepts Demonstrated:
- Pattern matching with regular expressions (re.compile, search, findall)
- Dictionary-based classification scoring and argmax selection
- Sets for O(1) membership testing (question words, keywords)
- Conditional logic, string processing, and exception handling
- Configurable categorization supporting both granular tags and academic macro categories
"""

import re
from dataclasses import dataclass
from typing import Any


class CategorizerError(Exception):
    """Custom exception raised when message categorization encounters errors."""
    pass


@dataclass
class CategoryResult:
    """Encapsulates the classification outcome with confidence and explanation."""
    category: str
    macro_category: str
    confidence: float
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a serializable dictionary."""
        return {
            "category": self.category,
            "macro_category": self.macro_category,
            "confidence": self.confidence,
            "explanation": self.explanation,
        }


class MessageCategorizer:
    """
    Classifies incoming messages into semantic categories:
    Granular tags:
    - question
    - code
    - action_item
    - announcement
    - important_update
    - greeting
    - general

    Academic Macro Categories (Prompt 6 requirement):
    1. General discussion (general_discussion)
    2. Questions (questions)
    3. Announcements (announcements)
    4. Important updates (important_updates)
    5. Work-related discussions (work_related)
    """

    CATEGORIES = (
        "question",
        "code",
        "action_item",
        "announcement",
        "important_update",
        "greeting",
        "general",
    )

    MACRO_CATEGORIES = {
        "general_discussion": "General discussion",
        "questions": "Questions",
        "announcements": "Announcements",
        "important_updates": "Important updates",
        "work_related": "Work-related discussions",
    }

    # Granular to Macro category mapping
    CATEGORY_TO_MACRO: dict[str, str] = {
        "general": "general_discussion",
        "greeting": "general_discussion",
        "question": "questions",
        "announcement": "announcements",
        "important_update": "important_updates",
        "code": "work_related",
        "action_item": "work_related",
    }

    # Regular expression signatures for category scoring
    CODE_PATTERNS = [
        re.compile(r"```"),
        re.compile(r"`[^`]+`"),
        re.compile(r"\b(def|class|import|return|function|const|let|var|SELECT|FROM|WHERE)\b"),
        re.compile(r"[{}\[\];()<>]"),
        re.compile(r"\b(print\(|console\.log\(|System\.out)\b"),
    ]

    QUESTION_WORDS: set[str] = {
        "who", "what", "where", "when", "why", "how", "can", "could", "would",
        "should", "is", "are", "do", "does", "did", "has", "have", "will", "whom"
    }

    ACTION_PATTERNS = [
        re.compile(r"\b(todo|to-do|action item|task|assigned to)\b", re.IGNORECASE),
        re.compile(r"\b(please|kindly|make sure to|need to|must)\b", re.IGNORECASE),
        re.compile(r"\b(by tomorrow|by eod|deadline|due date|submit by)\b", re.IGNORECASE),
    ]

    ANNOUNCEMENT_PATTERNS = [
        re.compile(r"\b(announcement|fyi|notice|attention|all hands|release notes)\b", re.IGNORECASE),
        re.compile(r"^\[?(announcement|notice)\]?:?", re.IGNORECASE),
    ]

    IMPORTANT_UPDATE_PATTERNS = [
        re.compile(r"\b(important update|critical update|security alert|urgent update|system downtime|maintenance window)\b", re.IGNORECASE),
        re.compile(r"^\[?(urgent|critical|update)\]?:?", re.IGNORECASE),
    ]

    GREETING_PATTERNS = [
        re.compile(r"\b(hello|hi|hey|good morning|good afternoon|good evening|welcome|greetings|howdy)\b", re.IGNORECASE),
    ]

    WORK_RELATED_PATTERNS = [
        re.compile(r"\b(meeting|sprint|jira|pull request|pr|code review|bug fix|deploy|staging|production|deliverable|milestone)\b", re.IGNORECASE),
    ]

    def classify_detailed(self, text: str) -> CategoryResult:
        """
        Comprehensive message classification returning granular tag, academic macro category,
        confidence score, and a human-readable explanation.
        """
        try:
            if not isinstance(text, str):
                raise CategorizerError("Input text must be a valid string")

            clean = text.strip()
            if not clean:
                return CategoryResult(
                    category="general",
                    macro_category="general_discussion",
                    confidence=1.0,
                    explanation="Empty message classified as general discussion by default.",
                )

            lower = clean.lower()
            scores: dict[str, float] = {cat: 0.0 for cat in self.CATEGORIES}

            # 1. Code Detection
            code_hits = sum(1 for pat in self.CODE_PATTERNS if pat.search(clean))
            if "```" in clean:
                scores["code"] += 0.95
            elif code_hits >= 2:
                scores["code"] += 0.35 * code_hits

            # 2. Question Detection
            if clean.endswith("?"):
                scores["question"] += 0.55
            first_word = lower.split()[0] if lower.split() else ""
            if first_word in self.QUESTION_WORDS:
                scores["question"] += 0.45
            if any(w in lower.split() for w in self.QUESTION_WORDS) and "?" in clean:
                scores["question"] += 0.30

            # 3. Action Item Detection
            action_hits = sum(1 for pat in self.ACTION_PATTERNS if pat.search(clean))
            if action_hits > 0:
                scores["action_item"] += 0.50 * action_hits

            # 4. Important Update Detection
            update_hits = sum(1 for pat in self.IMPORTANT_UPDATE_PATTERNS if pat.search(clean))
            if update_hits > 0:
                scores["important_update"] += 0.70 * update_hits

            # 5. Announcement Detection
            announcement_hits = sum(1 for pat in self.ANNOUNCEMENT_PATTERNS if pat.search(clean))
            if announcement_hits > 0:
                scores["announcement"] += 0.60 * announcement_hits

            # 6. Greeting Detection
            greeting_hits = sum(1 for pat in self.GREETING_PATTERNS if pat.search(clean))
            if greeting_hits > 0 and len(clean.split()) <= 6:
                scores["greeting"] += 0.85

            # 7. Work-related keywords boost action_item or code if matched
            work_hits = sum(1 for pat in self.WORK_RELATED_PATTERNS if pat.search(clean))
            if work_hits > 0:
                scores["action_item"] += 0.35 * work_hits

            # Determine category with highest heuristic score
            best_category = "general"
            max_score = 0.0

            for cat, sc in scores.items():
                if sc > max_score:
                    max_score = sc
                    best_category = cat

            # Confidence normalization
            if max_score > 0.0:
                confidence = round(min(1.0, 0.40 + (max_score * 0.40)), 2)
            else:
                confidence = 0.50

            macro = self.CATEGORY_TO_MACRO.get(best_category, "general_discussion")
            explanation = (
                f"Classified as '{best_category}' (Macro: '{self.MACRO_CATEGORIES.get(macro, macro)}') "
                f"with {int(confidence * 100)}% confidence based on linguistic marker scoring."
            )

            return CategoryResult(
                category=best_category,
                macro_category=macro,
                confidence=confidence,
                explanation=explanation,
            )

        except Exception as exc:
            if isinstance(exc, CategorizerError):
                raise
            raise CategorizerError(f"Error during message categorization: {str(exc)}") from exc

    def classify(self, text: str, macro: bool = False) -> tuple[str, float]:
        """
        Classify message text into designated category name and confidence float.
        If macro=True, returns one of the 5 academic macro categories:
        ('general_discussion', 'questions', 'announcements', 'important_updates', 'work_related').
        If macro=False (default), returns the granular tag for backward compatibility.
        """
        res = self.classify_detailed(text)
        if macro:
            return res.macro_category, res.confidence
        return res.category, res.confidence
