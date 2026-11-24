"""
Pure Python Intelligence & Academic Showcase Test Suite
=======================================================
Validates all pure Python NLP algorithms, data structures, recursion, and math.
"""

from app.python_features.processor import MessageProcessor
from app.python_features.spam_detector import SpamDetector
from app.python_features.sentiment import SentimentAnalyzer
from app.python_features.categorizer import MessageCategorizer
from app.python_features.summarizer import ConversationSummarizer
from app.python_features.analytics import ChatAnalyticsEngine
from app.python_features.academic_showcase import (
    run_academic_verification,
    count_nested_replies,
    demonstrate_operators,
    evaluate_message_tier,
)


def test_academic_syllabus_verification():
    """Verify that all 15 core curriculum topics in academic showcase execute cleanly."""
    report = run_academic_verification()
    assert report["status"] == "ALL_CONCEPTS_VERIFIED"
    assert len(report["demonstrated_topics"]) == 15
    for concept, passed in report["test_results"].items():
        assert passed is True, f"Academic concept check failed for {concept}"


def test_recursion_nested_thread_depth():
    """Verify academic recursion requirement on hierarchical reply trees."""
    processor = MessageProcessor()

    # Flat messages simulating thread parent-child relationships
    messages = [
        {"id": 1, "parent_id": None, "content": "Root topic"},
        {"id": 2, "parent_id": 1, "content": "Reply to root"},
        {"id": 3, "parent_id": 2, "content": "Reply to reply (depth 3)"},
        {"id": 4, "parent_id": 1, "content": "Second reply to root"},
    ]

    tree = processor.build_nested_thread_tree(messages, parent_id=None)
    assert len(tree) == 1  # 1 root node
    assert len(tree[0]["replies"]) == 2  # nodes 2 and 4

    # Calculate depth recursively
    depth = processor.calculate_tree_depth(tree[0])
    assert depth == 3

    # Academic recursion count
    sample_node = {"id": 1, "replies": [{"id": 2, "replies": []}]}
    assert count_nested_replies(sample_node) == 2


def test_sentiment_analyzer_lexicon_and_negation():
    """Test pure Python VADER sentiment analysis engine."""
    analyzer = SentimentAnalyzer()

    # Positive sentence
    pos_res = analyzer.analyze("ConnectX is an awesome and wonderful chat application!")
    assert pos_res.label == "positive"
    assert pos_res.score > 0.4

    # Negative sentence
    neg_res = analyzer.analyze("This code is broken and terrible.")
    assert neg_res.label == "negative"
    assert neg_res.score < -0.3

    # Negation flip: "not bad" should not be strongly negative
    negation_res = analyzer.analyze("The project performance is not bad at all.")
    assert negation_res.score > -0.1

    # ALL CAPS emphasis check
    loud_res = analyzer.analyze("I LOVE this!")
    normal_res = analyzer.analyze("I love this.")
    assert loud_res.score >= normal_res.score

    # Emoji recognition
    emoji_res = analyzer.analyze("Great job team! 🔥🚀🎉")
    assert emoji_res.label == "positive"
    assert emoji_res.score > 0.5


def test_spam_detector_entropy_and_heuristics():
    """Test Shannon entropy, rate limiting, and spam heuristics."""
    detector = SpamDetector()

    # Clean message
    clean_res = detector.evaluate("Hello everyone, let us meet in the computer lab at 3 PM.")
    assert clean_res.is_spam is False
    assert clean_res.score < 0.4

    # Excessive character repetition (low entropy)
    repeat_res = detector.evaluate("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert repeat_res.entropy < 2.0

    # High caps + spam keyword flag
    flagrant_spam = detector.evaluate("FREE CRYPTO 100% PROFIT CLICK HERE NOW TO WIN LOTTERY!!!")
    assert flagrant_spam.is_spam is True
    assert flagrant_spam.score >= 0.60
    assert len(flagrant_spam.reasons) >= 2


def test_message_categorizer():
    """Test semantic pattern categorization."""
    cat = MessageCategorizer()

    # Question
    q_label, _ = cat.classify("What is the time complexity of binary search?")
    assert q_label == "question"

    # Code block
    code_label, _ = cat.classify("Check out my function:\n```python\ndef solve():\n    return 42\n```")
    assert code_label == "code"

    # Action item
    action_label, _ = cat.classify("Please submit your project assignment by tomorrow.")
    assert action_label == "action_item"

    # Greeting
    greeting_label, _ = cat.classify("Hello team, good morning!")
    assert greeting_label == "greeting"


def test_conversation_summarizer():
    """Test pure Python extractive summarization algorithm."""
    summarizer = ConversationSummarizer()

    dialogue = [
        {"sender_name": "Alice", "content": "Good morning team, let us organize our development tasks today.", "is_deleted": False, "message_type": "text"},
        {"sender_name": "Bob", "content": "I am working on the database indexing and query optimization.", "is_deleted": False, "message_type": "text"},
        {"sender_name": "Charlie", "content": "We need to finish the unit testing suite by tomorrow at 4 PM.", "is_deleted": False, "message_type": "text"},
        {"sender_name": "Alice", "content": "We decided and confirmed the architecture design pattern.", "is_deleted": False, "message_type": "text"},
    ]

    summary = summarizer.summarize(dialogue)
    assert summary["message_count"] == 4
    assert len(summary["bullets"]) > 0
    assert len(summary["action_items"]) > 0
    assert len(summary["key_topics"]) > 0
