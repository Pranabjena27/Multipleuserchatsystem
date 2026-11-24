"""
Services Package Initialization
===============================
Exposes all business services and pure Python intelligence modules:
Message Processing, Spam Detection, Sentiment Analysis, Summarization,
Categorization, and Academic Demonstrations.
"""

from app.python_features.processor import MessageProcessor, ProcessingError
from app.python_features.spam_detector import SpamDetector, SpamCheckResult
from app.python_features.sentiment import SentimentAnalyzer, SentimentResult
from app.python_features.summarizer import ConversationSummarizer
from app.python_features.categorizer import MessageCategorizer
from app.python_features.analytics import ChatAnalyticsEngine
from app.python_features.academic_showcase import run_academic_verification

__all__ = [
    "MessageProcessor",
    "ProcessingError",
    "SpamDetector",
    "SpamCheckResult",
    "SentimentAnalyzer",
    "SentimentResult",
    "ConversationSummarizer",
    "MessageCategorizer",
    "ChatAnalyticsEngine",
    "run_academic_verification",
]
