"""
Python Features Package
=======================
Exposes pure Python natural language processing, spam filtering, sentiment analysis,
extractive summarization, smart categorization, chat analytics, content moderation,
and academic syllabus demonstrations.
"""

from app.python_features.processor import MessageProcessor, ProcessingError
from app.python_features.spam_detector import (
    SpamDetector,
    SpamRules,
    SpamCheckResult,
    SpamDetectionError,
)
from app.python_features.sentiment import (
    SentimentAnalyzer,
    SentimentResult,
    SentimentAnalysisError,
)
from app.python_features.summarizer import (
    ConversationSummarizer,
    SummaryResult,
    SummarizerError,
)
from app.python_features.categorizer import (
    MessageCategorizer,
    CategoryResult,
    CategorizerError,
)
from app.python_features.analytics import (
    ChatAnalyticsEngine,
    AnalyticsError,
)
from app.python_features.moderation import (
    ContentModerator,
    ModerationConfig,
    ModerationVerdict,
    ModerationError,
)
from app.python_features.academic_showcase import run_academic_verification

__all__ = [
    "MessageProcessor",
    "ProcessingError",
    "SpamDetector",
    "SpamRules",
    "SpamCheckResult",
    "SpamDetectionError",
    "SentimentAnalyzer",
    "SentimentResult",
    "SentimentAnalysisError",
    "ConversationSummarizer",
    "SummaryResult",
    "SummarizerError",
    "MessageCategorizer",
    "CategoryResult",
    "CategorizerError",
    "ChatAnalyticsEngine",
    "AnalyticsError",
    "ContentModerator",
    "ModerationConfig",
    "ModerationVerdict",
    "ModerationError",
    "run_academic_verification",
]
