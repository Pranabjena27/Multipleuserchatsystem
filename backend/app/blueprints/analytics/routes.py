"""
Academic Analytics Blueprint Module
===================================
Provides interactive laboratories and visual metrics demonstrating
the pure Python NLP, sentiment, spam, categorization, summarization, and moderation engines.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models.chat import Message, Conversation
from app.python_features.sentiment import SentimentAnalyzer
from app.python_features.spam_detector import SpamDetector
from app.python_features.categorizer import MessageCategorizer
from app.python_features.summarizer import ConversationSummarizer
from app.python_features.analytics import ChatAnalyticsEngine
from app.python_features.moderation import ContentModerator
from app.python_features.academic_showcase import run_academic_verification

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")

# Instantiate pure Python engines
sentiment_engine = SentimentAnalyzer()
spam_engine = SpamDetector()
categorizer_engine = MessageCategorizer()
summarizer_engine = ConversationSummarizer()
moderator_engine = ContentModerator()


@analytics_bp.route("/")
@login_required
def dashboard():
    """Main analytics dashboard rendering charts, stats, and interactive labs."""
    # Compute global chat metrics from database
    all_msgs = Message.query.filter_by(is_deleted=False).limit(500).all()
    serialized = [m.to_dict() for m in all_msgs]

    all_convs = Conversation.query.all()
    conv_meta = [
        {
            "id": c.id,
            "type": c.type,
            "title": c.title,
            "participant_count": len(c.participants),
        }
        for c in all_convs
    ]

    global_analytics = ChatAnalyticsEngine.compute_analytics(
        serialized, conversations_metadata=conv_meta
    )

    # Run academic verification suite
    academic_audit = run_academic_verification()

    # User's conversations for dropdown selection in summarizer
    user_conversations = [
        p.conversation
        for p in current_user.participations
    ]

    return render_template(
        "analytics/dashboard.html",
        analytics=global_analytics,
        academic_audit=academic_audit,
        conversations=user_conversations,
    )


@analytics_bp.route("/test-sentiment", methods=["POST"])
@login_required
def test_sentiment():
    """Interactive endpoint to evaluate sentiment on user-submitted text."""
    data = request.get_json() or {}
    text = data.get("text", "")
    result = sentiment_engine.analyze(text)
    return jsonify({
        "score": result.score,
        "label": result.label,
        "positive": result.positive,
        "neutral": result.neutral,
        "negative": result.negative,
        "explanation": result.explanation,
        "details": result.details,
    })


@analytics_bp.route("/test-spam", methods=["POST"])
@login_required
def test_spam():
    """Interactive endpoint to evaluate spam metrics on user-submitted text."""
    data = request.get_json() or {}
    text = data.get("text", "")
    result = spam_engine.evaluate(text, user_id=current_user.id)
    return jsonify({
        "is_spam": result.is_spam,
        "score": result.score,
        "reasons": result.reasons,
        "explanation": result.explanation,
        "entropy": result.entropy,
        "caps_ratio": result.caps_ratio,
        "url_count": result.url_count,
        "metrics": result.metrics,
    })


@analytics_bp.route("/test-categorize", methods=["POST"])
@login_required
def test_categorize():
    """Interactive endpoint to classify user-submitted message text."""
    data = request.get_json() or {}
    text = data.get("text", "")
    detailed = categorizer_engine.classify_detailed(text)
    return jsonify({
        "category": detailed.category,
        "macro_category": detailed.macro_category,
        "confidence": detailed.confidence,
        "explanation": detailed.explanation,
    })


@analytics_bp.route("/test-summarize", methods=["POST"])
@login_required
def test_summarize():
    """Interactive endpoint to run summarization on custom text lines."""
    data = request.get_json() or {}
    raw_text = data.get("text", "")
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # Format lines into synthetic message objects for the summarizer
    synthetic_messages = [
        {
            "sender_name": f"User_{idx % 3 + 1}",
            "content": line,
            "is_deleted": False,
            "message_type": "text",
        }
        for idx, line in enumerate(lines)
    ]

    summary = summarizer_engine.summarize(synthetic_messages)
    return jsonify({"summary": summary})


@analytics_bp.route("/test-moderation", methods=["POST"])
@login_required
def test_moderation():
    """Interactive endpoint to evaluate content moderation policies on user-submitted text."""
    data = request.get_json() or {}
    text = data.get("text", "")
    verdict = moderator_engine.evaluate(text, user_id=current_user.id)
    return jsonify(verdict.to_dict())
