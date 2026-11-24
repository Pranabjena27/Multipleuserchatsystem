"""
Content Moderation Module
=========================
Academic Concepts Demonstrated:
- Object-oriented architecture with classes, objects, and dataclasses
- Set operations for O(1) keyword filtering
- Regular expressions for harassment, threat, and toxic pattern matching
- Conditional logic, threshold branching, and severity classification
- Configurable rules engine for administrative governance
- Custom exception hierarchy and detailed explanation generation
"""

import re
from dataclasses import dataclass, field
from typing import Any
from app.python_features.spam_detector import SpamDetector, SpamRules


class ModerationError(Exception):
    """Custom exception raised when moderation evaluation fails."""
    pass


@dataclass
class ModerationConfig:
    """
    Configurable rules and thresholds for automated message moderation.
    Demonstrates default parameters, sets, and type hints.
    """
    blocked_keywords: set[str] = field(default_factory=lambda: {
        "harass", "kill", "suicide", "threaten", "terrorist", "bomb",
        "doxx", "blackmail", "extortion", "assault"
    })
    profanity_keywords: set[str] = field(default_factory=lambda: {
        "abuse", "idiot", "stupid", "hate", "scam", "fool", "vulgar"
    })
    auto_quarantine_threshold: float = 0.80
    flag_review_threshold: float = 0.50
    mask_profanity: bool = True


@dataclass
class ModerationVerdict:
    """
    Encapsulates the outcome of content moderation, including severity,
    recommended action, policy violations, and administrative explanation.
    """
    flagged: bool
    action: str        # 'allow', 'flag_for_review', 'quarantine', 'block'
    severity: str      # 'clean', 'low', 'medium', 'high', 'critical'
    reasons: list[str] = field(default_factory=list)
    explanation: str = ""
    cleaned_content: str = ""
    policy_violations: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert moderation verdict to serializable dictionary."""
        return {
            "flagged": self.flagged,
            "action": self.action,
            "severity": self.severity,
            "reasons": self.reasons,
            "explanation": self.explanation,
            "cleaned_content": self.cleaned_content,
            "policy_violations": self.policy_violations,
            "metrics": self.metrics,
        }


class ContentModerator:
    """
    Automated content moderator inspecting incoming messages for:
    - Policy violations (threats, harassment, abuse)
    - Profanity and offensive vocabulary
    - Integrated spam indicators
    - Administrator review queuing and explanations
    """

    # Threat and severe harassment patterns
    THREAT_PATTERNS = [
        re.compile(r"\b(i will hurt|i will kill|i will destroy|die in a)\b", re.IGNORECASE),
        re.compile(r"\b(i know where you live|doxxing you|leaking your info)\b", re.IGNORECASE),
    ]

    def __init__(self, config: ModerationConfig | None = None) -> None:
        """Initialize content moderator with optional custom configuration."""
        self.config = config or ModerationConfig()
        self.spam_detector = SpamDetector()

    def mask_text(self, text: str) -> tuple[str, list[str]]:
        """
        Mask profanity terms replacing interior characters with asterisks.
        Demonstrates loops, word boundaries, regex substitution, and string slicing.
        Returns: (masked_text, list_of_detected_profanities)
        """
        detected: list[str] = []
        result = text

        for word in self.config.profanity_keywords:
            pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            if pattern.search(result):
                detected.append(word)
                if self.config.mask_profanity:
                    replacement = word[0] + ("*" * (len(word) - 1))
                    result = pattern.sub(replacement, result)

        return result, detected

    def evaluate(self, text: str, user_id: int | None = None) -> ModerationVerdict:
        """
        Perform complete multi-stage moderation pass on message text.
        Demonstrates:
        - Input validation and exception handling
        - Severity scoring
        - Threat pattern matching
        - Keyword inspection using set lookups
        - Spam integration
        - Human-readable explanation generation
        """
        try:
            if not isinstance(text, str):
                raise ModerationError("Message content must be a string")

            clean = text.strip()
            if not clean:
                return ModerationVerdict(
                    flagged=False,
                    action="allow",
                    severity="clean",
                    reasons=[],
                    explanation="Empty message cleared without restrictions.",
                    cleaned_content="",
                )

            reasons: list[str] = []
            violations: list[str] = []
            severity_score = 0.0
            lower = clean.lower()

            # 1. Threat & Harassment Pattern Matching (Critical severity)
            threat_matches = [p.pattern for p in self.THREAT_PATTERNS if p.search(clean)]
            if threat_matches:
                severity_score += 0.90
                violations.append("Direct Threat / Harassment Policy")
                reasons.append("Severe threat pattern detected")

            # 2. Blocked Policy Keywords (High severity)
            matched_blocked = [w for w in self.config.blocked_keywords if w in lower]
            if matched_blocked:
                severity_score += 0.50 + min(0.35, len(matched_blocked) * 0.15)
                violations.append("Prohibited Content Policy")
                reasons.append(f"Prohibited terms identified: {', '.join(matched_blocked)}")

            # 3. Profanity & Abusive Language (Medium/Low severity)
            masked_text, detected_profanities = self.mask_text(clean)
            if detected_profanities:
                severity_score += min(0.40, len(detected_profanities) * 0.15)
                violations.append("Community Civility Guidelines")
                reasons.append(f"Vulgar terms detected: {', '.join(detected_profanities)}")

            # 4. Integrated Spam Inspection
            spam_res = self.spam_detector.evaluate(clean, user_id=user_id)
            if spam_res.is_spam:
                severity_score += 0.40
                violations.append("Anti-Spam & Flooding Policy")
                reasons.append(f"Spam indicators flagged (score: {spam_res.score:.2f})")

            # Determine severity level
            if severity_score >= 0.85:
                severity = "critical"
                action = "block"
                flagged = True
            elif severity_score >= self.config.auto_quarantine_threshold:
                severity = "high"
                action = "quarantine"
                flagged = True
            elif severity_score >= self.config.flag_review_threshold:
                severity = "medium"
                action = "flag_for_review"
                flagged = True
            elif detected_profanities:
                severity = "low"
                action = "allow"  # Allowed with masked text
                flagged = False
            else:
                severity = "clean"
                action = "allow"
                flagged = False

            # Generate Administrator Explanation
            if flagged:
                explanation = (
                    f"Message flagged under [{severity.upper()}] severity (Score: {severity_score:.2f}). "
                    f"Recommended Administrator Action: [{action.upper()}]. "
                    f"Violations: {'; '.join(reasons)}. "
                    f"Policies violated: {', '.join(violations)}."
                )
            elif detected_profanities:
                explanation = (
                    f"Message allowed with profanity masking. Offensive terms sanitized: "
                    f"{', '.join(detected_profanities)}."
                )
            else:
                explanation = "Content passed automated moderation. No policy violations detected."

            metrics = {
                "severity_score": round(severity_score, 2),
                "threat_matches": len(threat_matches),
                "prohibited_matches": len(matched_blocked),
                "profanity_matches": len(detected_profanities),
                "spam_score": spam_res.score,
            }

            return ModerationVerdict(
                flagged=flagged,
                action=action,
                severity=severity,
                reasons=reasons,
                explanation=explanation,
                cleaned_content=masked_text,
                policy_violations=violations,
                metrics=metrics,
            )

        except Exception as exc:
            if isinstance(exc, ModerationError):
                raise
            raise ModerationError(f"Error evaluating message moderation: {str(exc)}") from exc
