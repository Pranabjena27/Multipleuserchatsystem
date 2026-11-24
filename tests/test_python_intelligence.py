"""
ConnectX Python Intelligence Modules Unit & Integration Tests
=============================================================
Tests all 6 advanced Python-powered intelligence modules:
1. Spam Detection (repeated content, links, keywords, frequency, rules, explanations)
2. Sentiment Analysis (positive, negative, neutral, negation, boosters, emojis, explanations)
3. Conversation Summarization (empty conversations, long histories, action items, decisions)
4. Smart Categorization (general, questions, announcements, important updates, work-related)
5. Chat Analytics (total messages, messages per day, active users, active groups, activity)
6. Message Moderation (policy enforcement, threat detection, severity, admin explanations)
"""

import pytest
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


# =============================================================================
# FEATURE 1: SPAM DETECTION TESTS
# =============================================================================

def test_spam_clean_message():
    """Verify that legitimate academic conversation is not flagged as spam."""
    detector = SpamDetector()
    result = detector.evaluate("Hello everyone, please review chapter 4 on Python recursion.")
    assert not result.is_spam
    assert result.score < 0.40
    assert "clean" in result.explanation.lower()
    assert isinstance(result.to_dict(), dict)


def test_spam_repeated_content_entropy():
    """Verify that low-entropy character repetitions and repetitive word flooding are flagged."""
    detector = SpamDetector()
    # Severe character repetition
    rep_result = detector.evaluate("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert rep_result.is_spam
    assert rep_result.entropy < 2.0
    assert any("entropy" in r.lower() or "flood" in r.lower() for r in rep_result.reasons)
    assert len(rep_result.explanation) > 10

    # Word flood
    word_flood = detector.evaluate("prize prize prize prize prize prize prize prize prize prize")
    assert word_flood.is_spam
    assert any("word" in r.lower() or "entropy" in r.lower() for r in word_flood.reasons)


def test_spam_excessive_links():
    """Verify that messages with excessive hyperlinks exceed the threshold and get flagged."""
    rules = SpamRules(max_links_allowed=2)
    detector = SpamDetector(rules=rules)

    link_msg = (
        "Check these sites now: http://spam1.xyz and http://spam2.com "
        "also visit https://spam3.org and http://spam4.net immediately!"
    )
    result = detector.evaluate(link_msg)
    assert result.url_count == 4
    assert any("hyperlinks" in r.lower() for r in result.reasons)
    assert result.score >= 0.35


def test_spam_suspicious_keywords():
    """Verify detection of phishing, crypto, and lottery spam phrases."""
    detector = SpamDetector()
    spam_text = "CONGRATULATIONS WINNER! Claim your free crypto prize and wire transfer now!"
    result = detector.evaluate(spam_text)
    assert result.is_spam
    assert any("spam phrases" in r.lower() for r in result.reasons)
    assert "SPAM" in result.explanation


def test_spam_message_frequency_and_sliding_window():
    """Verify user rate limiting and duplicate message flood detection."""
    rules = SpamRules(
        rate_limit_window_seconds=10,
        max_messages_per_window=4,
    )
    detector = SpamDetector(rules=rules)
    user_id = 999

    # Send 4 messages - within quota
    for i in range(4):
        res = detector.evaluate(f"Legitimate update number {i}", user_id=user_id)
        assert not res.is_spam

    # 5th message exceeds sliding window quota
    flood_res = detector.evaluate("Another rapid message!", user_id=user_id)
    assert flood_res.is_spam or flood_res.score >= 0.45
    assert any("rate limit" in r.lower() or "frequency" in r.lower() for r in flood_res.reasons)


def test_spam_configurable_rules():
    """Verify custom keyword injection and custom trigger thresholds."""
    custom_rules = SpamRules(
        trigger_threshold=0.30,
        custom_keywords={"custom_scam_token", "bogus_giveaway"},
    )
    detector = SpamDetector(rules=custom_rules)
    res = detector.evaluate("Here is a special custom_scam_token for you.")
    assert res.is_spam
    assert any("custom_scam_token" in r for r in res.reasons)


def test_spam_error_handling():
    """Verify exception handling when non-string input is provided."""
    detector = SpamDetector()
    with pytest.raises(SpamDetectionError):
        detector.evaluate(12345)  # type: ignore


# =============================================================================
# FEATURE 2: SENTIMENT ANALYSIS TESTS
# =============================================================================

def test_sentiment_positive_with_boosters_and_emojis():
    """Verify classification of highly positive messages with booster words and emojis."""
    analyzer = SentimentAnalyzer()
    text = "The new ConnectX algorithm is super awesome and I am extremely happy! 🚀🎉"
    res = analyzer.analyze(text)
    assert res.label == "positive"
    assert res.score > 0.40
    assert res.positive > 0.50
    assert "POSITIVE" in res.explanation
    assert len(res.details["matched_positive"]) >= 2
    assert len(res.details["emojis"]) >= 2


def test_sentiment_negative_with_negation_handling():
    """Verify that negations flip positive words into negative sentiment."""
    analyzer = SentimentAnalyzer()

    # Direct negative
    bad_res = analyzer.analyze("This code is broken and terrible, it crashed the server.")
    assert bad_res.label == "negative"
    assert bad_res.score < -0.30
    assert "NEGATIVE" in bad_res.explanation

    # Negation flip: "not good" should be negative, not positive
    neg_res = analyzer.analyze("The latency was not good and definitely not clean.")
    assert neg_res.label == "negative"
    assert neg_res.score < 0.0
    neg_details = neg_res.details.get("negations", [])
    assert any("not -> good" in n or "not -> clean" in n for n in neg_details)


def test_sentiment_neutral_and_empty():
    """Verify handling of neutral factual statements and empty text."""
    analyzer = SentimentAnalyzer()

    empty_res = analyzer.analyze("")
    assert empty_res.label == "neutral"
    assert empty_res.score == 0.0

    neutral_res = analyzer.analyze("The lecture will start at 10 AM in classroom 204.")
    assert neutral_res.label == "neutral"
    assert -0.08 < neutral_res.score < 0.08


def test_sentiment_exclamation_emphasis():
    """Verify that exclamation marks amplify the intensity of sentiment."""
    analyzer = SentimentAnalyzer()
    calm = analyzer.analyze("Great job")
    excited = analyzer.analyze("Great job!!!")
    assert excited.score >= calm.score


def test_sentiment_error_handling():
    """Verify exception handling for invalid input types."""
    analyzer = SentimentAnalyzer()
    with pytest.raises(SentimentAnalysisError):
        analyzer.analyze(None)  # type: ignore


# =============================================================================
# FEATURE 3: CONVERSATION SUMMARIZATION TESTS
# =============================================================================

def test_summarizer_empty_and_brief_conversations():
    """Verify graceful handling of empty message lists and deleted messages."""
    summarizer = ConversationSummarizer()

    # Empty list
    empty_res = summarizer.summarize([])
    assert empty_res["message_count"] == 0
    assert "No messages available" in empty_res["summary"]
    assert empty_res["bullets"] == []

    # Only deleted messages
    deleted_res = summarizer.summarize([
        {"sender_name": "Alice", "content": "[Message deleted]", "is_deleted": True},
    ])
    assert deleted_res["message_count"] == 0


def test_summarizer_extraction_of_actions_and_decisions():
    """Verify extraction of key points, action items, decisions, and participants."""
    summarizer = ConversationSummarizer(max_summary_sentences=3)

    dialogue = [
        {"sender_name": "Prof_Sharma", "content": "Good morning class, welcome to the Python chat review.", "is_deleted": False, "message_type": "text"},
        {"sender_name": "Alice", "content": "We need to submit the final project documentation by tomorrow at 5 PM.", "is_deleted": False, "message_type": "text"},
        {"sender_name": "Bob", "content": "I will fix the SocketIO presence connection handler.", "is_deleted": False, "message_type": "text"},
        {"sender_name": "Prof_Sharma", "content": "We decided and confirmed the grading rubric for the final project.", "is_deleted": False, "message_type": "text"},
        {"sender_name": "Alice", "content": "Great, the solution is approved and ready for testing.", "is_deleted": False, "message_type": "text"},
    ]

    res = summarizer.summarize(dialogue)
    assert res["message_count"] == 5
    assert res["participant_count"] == 3
    assert "Prof_Sharma" in res["participants"]
    assert len(res["bullets"]) <= 3
    assert len(res["action_items"]) >= 1
    assert any("by tomorrow" in item.lower() for item in res["action_items"])
    assert len(res["decisions"]) >= 1
    assert any("decided" in d.lower() or "confirmed" in d.lower() for d in res["decisions"])
    assert len(res["key_topics"]) > 0


def test_summarizer_long_conversation_stability():
    """Verify that summarizing 300+ messages runs fast without memory degradation."""
    summarizer = ConversationSummarizer(max_history_limit=200)

    long_dialogue = [
        {
            "sender_name": f"User_{i % 5}",
            "content": f"Message sequence item {i} discussing Python module architecture and testing.",
            "is_deleted": False,
            "message_type": "text",
        }
        for i in range(350)
    ]

    res = summarizer.summarize(long_dialogue)
    assert res["message_count"] == 200  # Truncated by safety limit
    assert len(res["bullets"]) > 0
    assert len(res["summary"]) > 20


def test_summarizer_error_handling():
    """Verify exception handling when parameter is not a list."""
    summarizer = ConversationSummarizer()
    with pytest.raises(SummarizerError):
        summarizer.summarize("Not a list")  # type: ignore


# =============================================================================
# FEATURE 4: SMART CATEGORIZATION TESTS
# =============================================================================

def test_categorizer_all_five_macro_categories():
    """Verify accurate classification into the 5 academic macro categories."""
    cat = MessageCategorizer()

    # 1. Questions
    q_cat, conf_q = cat.classify("How do we implement WebSocket reconnection in Flask-SocketIO?", macro=True)
    assert q_cat == "questions"
    assert conf_q >= 0.70

    # 2. Announcements
    ann_cat, conf_ann = cat.classify("[Announcement] Final semester practical exam schedule released.", macro=True)
    assert ann_cat == "announcements"
    assert conf_ann >= 0.70

    # 3. Important Updates
    upd_cat, conf_upd = cat.classify("Critical update: Database maintenance window scheduled tonight at 11 PM.", macro=True)
    assert upd_cat == "important_updates"
    assert conf_upd >= 0.70

    # 4. Work-Related Discussions (Code snippets, tasks, meetings, PRs)
    work_code, _ = cat.classify("```python\ndef calculate_entropy(s):\n    return 3.14\n```", macro=True)
    assert work_code == "work_related"

    work_task, _ = cat.classify("Please submit the code review and pull request by tomorrow morning.", macro=True)
    assert work_task == "work_related"

    # 5. General Discussion
    gen_cat, _ = cat.classify("Hey everyone, hope you all have a wonderful weekend!", macro=True)
    assert gen_cat == "general_discussion"


def test_categorizer_detailed_result_object():
    """Verify CategoryResult dataclass, explanation, and confidence metrics."""
    cat = MessageCategorizer()
    res = cat.classify_detailed("What is the time complexity of quicksort?")
    assert isinstance(res, CategoryResult)
    assert res.category == "question"
    assert res.macro_category == "questions"
    assert res.confidence > 0.60
    assert "explanation" in res.to_dict()


def test_categorizer_error_handling():
    """Verify exception handling for invalid message input."""
    cat = MessageCategorizer()
    with pytest.raises(CategorizerError):
        cat.classify_detailed(404)  # type: ignore


# =============================================================================
# FEATURE 5: CHAT ANALYTICS TESTS
# =============================================================================

def test_analytics_metrics_calculations():
    """Verify total messages, messages per day, active users, groups, and category distribution."""
    sample_messages = [
        {"sender_name": "Alice", "content": "How do we write unit tests in pytest?", "category": "question", "sentiment_label": "positive", "created_at": "2026-11-10T10:00:00Z", "conversation_id": 1, "is_deleted": False},
        {"sender_name": "Bob", "content": "Here is the test function.", "category": "code", "sentiment_label": "neutral", "created_at": "2026-11-10T10:05:00Z", "conversation_id": 1, "is_deleted": False},
        {"sender_name": "Charlie", "content": "Announcement: Meeting today at 4 PM.", "category": "announcement", "sentiment_label": "positive", "created_at": "2026-11-10T11:00:00Z", "conversation_id": 2, "is_deleted": False},
        {"sender_name": "Alice", "content": "Critical update: Server restarted.", "category": "important_update", "sentiment_label": "negative", "created_at": "2026-11-11T09:00:00Z", "conversation_id": 2, "is_deleted": False},
        {"sender_name": "Alice", "content": "Deleted note", "category": "general", "sentiment_label": "neutral", "created_at": "2026-11-11T09:10:00Z", "conversation_id": 2, "is_deleted": True},
    ]

    conv_meta = [
        {"id": 1, "type": "group", "title": "B.Tech Study Circle", "participant_count": 3},
        {"id": 2, "type": "group", "title": "Python Faculty Room", "participant_count": 2},
    ]

    metrics = ChatAnalyticsEngine.compute_analytics(sample_messages, conversations_metadata=conv_meta)

    # 1. Total Messages (excluding deleted)
    assert metrics["total_messages"] == 4

    # 2. Messages per Day
    assert "2026-11-10" in metrics["messages_per_day"]
    assert metrics["messages_per_day"]["2026-11-10"] == 3
    assert metrics["messages_per_day"]["2026-11-11"] == 1
    assert metrics["avg_messages_per_day"] == 2.0

    # 3. Active Users
    assert metrics["active_users_count"] == 3
    top_user = metrics["active_users"][0]
    assert top_user["username"] == "Alice"
    assert top_user["count"] == 2
    assert top_user["share_percentage"] == 50.0

    # 4. Most Active Groups
    assert len(metrics["most_active_groups"]) == 2
    assert metrics["most_active_groups"][0]["title"] == "B.Tech Study Circle"

    # 5. Conversation Activity
    assert len(metrics["conversation_activity"]) == 2

    # 6. Category Distribution
    cat_dist = metrics["category_distribution"]
    assert cat_dist["questions"] == 1
    assert cat_dist["work_related"] == 1  # "code" mapped to work_related
    assert cat_dist["announcements"] == 1
    assert cat_dist["important_updates"] == 1


def test_analytics_empty_dataset():
    """Verify analytics response on empty dataset."""
    metrics = ChatAnalyticsEngine.compute_analytics([])
    assert metrics["total_messages"] == 0
    assert metrics["active_users_count"] == 0
    assert metrics["avg_messages_per_day"] == 0.0


def test_analytics_error_handling():
    """Verify exception handling when invalid argument is provided."""
    with pytest.raises(AnalyticsError):
        ChatAnalyticsEngine.compute_analytics("Invalid list argument")  # type: ignore


# =============================================================================
# FEATURE 6: CONTENT MODERATION & REVIEW TESTS
# =============================================================================

def test_moderator_clean_message():
    """Verify that compliant messages receive clean verdict with no restrictions."""
    moderator = ContentModerator()
    verdict = moderator.evaluate("Good afternoon, could you please clarify the homework assignment?")
    assert not verdict.flagged
    assert verdict.severity == "clean"
    assert verdict.action == "allow"
    assert "passed" in verdict.explanation.lower()
    assert isinstance(verdict.to_dict(), dict)


def test_moderator_severe_threat_detection():
    """Verify critical severity and blocking action for direct threats and violence."""
    moderator = ContentModerator()
    threat_text = "I will hurt your team members if you do not comply!"
    verdict = moderator.evaluate(threat_text)
    assert verdict.flagged
    assert verdict.severity in ("critical", "high")
    assert verdict.action in ("block", "quarantine")
    assert any("threat" in r.lower() for r in verdict.reasons)
    assert "Direct Threat" in verdict.policy_violations[0]
    assert "flagged under" in verdict.explanation.lower()


def test_moderator_profanity_masking():
    """Verify profanity detection and masking into asterisks."""
    moderator = ContentModerator()
    text_with_abuse = "That was a stupid and vulgar mistake."
    verdict = moderator.evaluate(text_with_abuse)
    assert "s*****" in verdict.cleaned_content or "v*****" in verdict.cleaned_content
    assert any("vulgar" in r.lower() for r in verdict.reasons)


def test_moderator_custom_configuration():
    """Verify custom blocked keywords and threshold tuning."""
    config = ModerationConfig(
        blocked_keywords={"prohibited_academic_token"},
        auto_quarantine_threshold=0.60,
    )
    moderator = ContentModerator(config=config)
    res = moderator.evaluate("This text includes a prohibited_academic_token.")
    assert res.flagged
    assert any("prohibited_academic_token" in r for r in res.reasons)


def test_moderator_error_handling():
    """Verify exception handling for non-string inputs."""
    moderator = ContentModerator()
    with pytest.raises(ModerationError):
        moderator.evaluate(123)  # type: ignore


# =============================================================================
# INTEGRATION TEST: FLASK API ENDPOINTS
# =============================================================================

def test_api_analytics_overview_endpoint(auth_client):
    """Verify GET /api/analytics/overview returns real analytics payload."""
    response = auth_client.get("/api/analytics/overview")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "total_messages" in data["analytics"]
    assert "category_distribution" in data["analytics"]
    assert "active_users" in data["analytics"]


def test_analytics_test_moderation_endpoint(auth_client):
    """Verify POST /analytics/test-moderation returns policy evaluation."""
    response = auth_client.post(
        "/analytics/test-moderation",
        json={"text": "I will hurt you right now!"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["flagged"] is True
    assert "severity" in data
    assert "explanation" in data
