"""
Sentiment Analyzer Module
=========================
Academic Concepts Demonstrated:
- Dictionaries, sets, and tuples (lexicons, negations, boosters)
- Mathematical functions (square root, normalization, sum, absolute values)
- String manipulations, regular expressions, and tokenization
- Rule-based, explainable Natural Language Processing (NLP) algorithm
- Object-oriented design, custom exception handling, and dataclasses
"""

import math
import re
from dataclasses import dataclass, field
from typing import Any


class SentimentAnalysisError(Exception):
    """Custom exception raised when sentiment analysis encounters invalid input or errors."""
    pass


@dataclass
class SentimentResult:
    """
    Encapsulates the polarity outcome, scores, and explainable details of a sentiment pass.
    """
    score: float       # Normalized compound score between -1.0 and +1.0
    label: str         # 'positive', 'neutral', or 'negative'
    positive: float    # Positive component ratio [0, 1]
    neutral: float     # Neutral component ratio [0, 1]
    negative: float    # Negative component ratio [0, 1]
    explanation: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a serializable dictionary."""
        return {
            "score": self.score,
            "label": self.label,
            "positive": self.positive,
            "neutral": self.neutral,
            "negative": self.negative,
            "explanation": self.explanation,
            "details": self.details,
        }


class SentimentAnalyzer:
    """
    Computes sentiment polarity from text tokens using an explainable academic lexicon,
    negation handling, booster word adjustments, capitalization, and emoji recognition.
    """

    # Lexicon mapping words to intrinsic valence scores (-3.0 to +3.0)
    LEXICON = {
        # Positive terms
        "great": 2.5, "excellent": 2.8, "awesome": 2.7, "good": 1.9, "love": 2.9,
        "like": 1.5, "happy": 2.3, "best": 2.8, "wonderful": 2.7, "fantastic": 2.8,
        "perfect": 2.9, "cool": 1.6, "brilliant": 2.6, "nice": 1.7, "amazing": 2.8,
        "beautiful": 2.4, "super": 2.0, "helpful": 2.1, "thanks": 1.8, "thank": 1.6,
        "excited": 2.2, "enjoy": 2.0, "solved": 1.9, "success": 2.5, "win": 2.2,
        "congratulations": 2.4, "welcome": 1.5, "glad": 1.8, "pleasant": 1.7,
        "impressive": 2.4, "clean": 1.6, "easy": 1.7, "recommend": 2.0, "delight": 2.6,

        # Negative terms
        "bad": -2.0, "terrible": -2.8, "awful": -2.7, "horrible": -2.8, "hate": -2.9,
        "dislike": -1.6, "sad": -2.0, "worst": -2.9, "poor": -1.8, "fail": -2.2,
        "failed": -2.2, "failure": -2.4, "broken": -2.0, "error": -1.8, "bug": -1.5,
        "issue": -1.2, "problem": -1.6, "angry": -2.3, "upset": -2.1, "annoying": -2.0,
        "slow": -1.4, "crash": -2.4, "crashed": -2.4, "useless": -2.5, "garbage": -2.6,
        "disappointed": -2.2, "frustrated": -2.3, "difficult": -1.3, "pain": -2.1,
        "ugly": -2.0, "stupid": -2.4, "horrid": -2.7, "confusing": -1.5,
    }

    # Emojis and their assigned valences
    EMOJI_LEXICON = {
        "😀": 2.0, "😃": 2.2, "😄": 2.4, "😊": 2.1, "😍": 2.8,
        "🥰": 2.7, "🚀": 2.0, "🔥": 2.2, "🎉": 2.4, "👍": 1.8,
        "❤️": 2.8, "💯": 2.5, "👏": 2.0, "✨": 1.7, "🥳": 2.5,
        "😢": -2.2, "😭": -2.4, "😡": -2.6, "🤬": -3.0, "👎": -2.0,
        "💔": -2.6, "🤮": -2.8, "😞": -2.0, "😤": -1.9, "💀": -1.2,
    }

    # Modifiers that amplify or dampen valence
    BOOSTER_WORDS = {
        "very": 0.293, "extremely": 0.35, "super": 0.293, "totally": 0.25,
        "absolutely": 0.32, "really": 0.25, "insanely": 0.33, "so": 0.22,
        "barely": -0.25, "hardly": -0.28, "slightly": -0.20, "somewhat": -0.15,
    }

    # Negation tokens that flip valence sign
    NEGATION_WORDS = {
        "not", "never", "no", "neither", "hardly", "barely",
        "don't", "dont", "wasn't", "wasnt", "isn't", "isnt",
        "aren't", "arent", "won't", "wont", "can't", "cant", "couldn't"
    }

    PUNCTUATION_CHARS = "!?,.;:"

    def __init__(self, positive_threshold: float = 0.08, negative_threshold: float = -0.08) -> None:
        """Initialize sentiment engine with configurable decision boundaries."""
        self.pos_threshold = positive_threshold
        self.neg_threshold = negative_threshold

    @classmethod
    def normalize_score(cls, raw_score: float, alpha: float = 15.0) -> float:
        """
        Normalize an accumulated sum score to range [-1.0, 1.0].
        Standard mathematical normalization function:
        score / sqrt(score^2 + alpha)
        """
        normalized = raw_score / math.sqrt((raw_score * raw_score) + alpha)
        return round(normalized, 4)

    def analyze(self, text: str) -> SentimentResult:
        """
        Execute sentiment analysis pass on given text string with explainable output.
        Demonstrates loops, conditionals, list operations, math formulas, and string formatting.
        """
        try:
            if not isinstance(text, str):
                raise SentimentAnalysisError("Input to SentimentAnalyzer must be a string")

            clean_text = text.strip()
            if not clean_text:
                return SentimentResult(
                    score=0.0,
                    label="neutral",
                    positive=0.0,
                    neutral=1.0,
                    negative=0.0,
                    explanation="Neutral: Empty or whitespace text has zero polarity.",
                    details={
                        "matched_positive": [],
                        "matched_negative": [],
                        "negations": [],
                        "boosters": [],
                        "emojis": [],
                    },
                )

            # 1. Inspect emojis
            emoji_sum = 0.0
            detected_emojis: list[dict[str, Any]] = []
            for char, valence in self.EMOJI_LEXICON.items():
                count = clean_text.count(char)
                if count > 0:
                    val_contribution = valence * count
                    emoji_sum += val_contribution
                    detected_emojis.append({
                        "emoji": char,
                        "count": count,
                        "valence": valence,
                        "contribution": val_contribution,
                    })

            # 2. Tokenize words while preserving case for ALL CAPS emphasis detection
            raw_tokens = re.findall(r"\b\w+(?:'\w+)?\b|[!?]", clean_text)
            if not raw_tokens and emoji_sum == 0.0:
                return SentimentResult(
                    score=0.0,
                    label="neutral",
                    positive=0.0,
                    neutral=1.0,
                    negative=0.0,
                    explanation="Neutral: No recognizable sentiment tokens found.",
                    details={"matched_positive": [], "matched_negative": [], "negations": [], "boosters": [], "emojis": []},
                )

            sentiments: list[float] = []
            matched_positive: list[str] = []
            matched_negative: list[str] = []
            applied_negations: list[str] = []
            applied_boosters: list[str] = []

            for i, token in enumerate(raw_tokens):
                token_lower = token.lower()

                if token_lower in self.LEXICON:
                    base_valence = self.LEXICON[token_lower]
                    valence = base_valence

                    # ALL CAPS multiplier
                    if token.isupper() and len(token) > 1:
                        valence += 0.50 if valence > 0 else -0.50

                    # Check preceding window of up to 3 tokens for boosters and negations
                    window = raw_tokens[max(0, i - 3):i]
                    was_negated = False
                    for distance, prev_token in enumerate(reversed(window)):
                        prev_lower = prev_token.lower()

                        # Negation check
                        if prev_lower in self.NEGATION_WORDS:
                            damping = 0.85 ** distance
                            valence = valence * -0.74 * damping
                            applied_negations.append(f"{prev_token} -> {token}")
                            was_negated = True
                            break

                        # Booster word check
                        if prev_lower in self.BOOSTER_WORDS:
                            boost = self.BOOSTER_WORDS[prev_lower]
                            if valence > 0:
                                valence += boost
                            else:
                                valence -= boost
                            applied_boosters.append(f"{prev_token} -> {token}")

                    sentiments.append(valence)
                    if valence > 0:
                        matched_positive.append(token)
                    elif valence < 0:
                        matched_negative.append(token)

            # 3. Punctuation emphasis check (e.g., '!!!')
            exclamation_count = clean_text.count("!")
            exclamation_boost = 0.0
            if exclamation_count > 0 and sentiments:
                exclamation_boost = min(1.0, exclamation_count * 0.15)
                curr_sum = sum(sentiments)
                if curr_sum > 0:
                    sentiments.append(exclamation_boost)
                elif curr_sum < 0:
                    sentiments.append(-exclamation_boost)

            # 4. Combine word sentiments and emoji sentiments
            total_raw = sum(sentiments) + emoji_sum
            compound = self.normalize_score(total_raw)

            # 5. Label categorization based on configurable boundaries
            if compound >= self.pos_threshold:
                label = "positive"
            elif compound <= self.neg_threshold:
                label = "negative"
            else:
                label = "neutral"

            # Calculate discrete component ratios
            pos_scores = [s for s in sentiments if s > 0]
            neg_scores = [abs(s) for s in sentiments if s < 0]
            pos_sum = sum(pos_scores) + max(0.0, emoji_sum)
            neg_sum = sum(neg_scores) + abs(min(0.0, emoji_sum))
            total_valence = pos_sum + neg_sum + 1e-6

            pos_ratio = round(pos_sum / total_valence, 2)
            neg_ratio = round(neg_sum / total_valence, 2)
            neu_ratio = round(max(0.0, 1.0 - (pos_ratio + neg_ratio)), 2)

            # 6. Generate human-readable academic explanation
            explanation_parts: list[str] = [
                f"Classified as {label.upper()} with normalized compound score {compound:+.2f}."
            ]
            if matched_positive:
                explanation_parts.append(f"Positive tokens detected: {', '.join(matched_positive)}.")
            if matched_negative:
                explanation_parts.append(f"Negative tokens detected: {', '.join(matched_negative)}.")
            if applied_negations:
                explanation_parts.append(f"Valence polarity flipped by negations: {', '.join(applied_negations)}.")
            if applied_boosters:
                explanation_parts.append(f"Intensity amplified by boosters: {', '.join(applied_boosters)}.")
            if detected_emojis:
                em_list = [f"{e['emoji']} ({e['valence']:+})" for e in detected_emojis]
                explanation_parts.append(f"Emoji valence modifiers: {', '.join(em_list)}.")
            if exclamation_boost > 0:
                explanation_parts.append(f"Exclamation emphasis applied ({exclamation_boost:+.2f}).")

            explanation = " ".join(explanation_parts)

            details = {
                "raw_valence_sum": round(total_raw, 3),
                "matched_positive": matched_positive,
                "matched_negative": matched_negative,
                "negations": applied_negations,
                "boosters": applied_boosters,
                "emojis": detected_emojis,
                "exclamation_boost": exclamation_boost,
            }

            return SentimentResult(
                score=compound,
                label=label,
                positive=pos_ratio,
                neutral=neu_ratio,
                negative=neg_ratio,
                explanation=explanation,
                details=details,
            )

        except Exception as exc:
            if isinstance(exc, SentimentAnalysisError):
                raise
            raise SentimentAnalysisError(f"Error during sentiment analysis: {str(exc)}") from exc
