"""
Chat Analytics Module
=====================
Academic Concepts Demonstrated:
- Numerical computations and statistical measures (mean, sum, ratios, percentages)
- Dictionary aggregations, collections.defaultdict, and Counter
- Time-series binning (messages per day, hourly distribution)
- List sorting with lambda keys and custom ordering
- Pure Python data processing without heavy external dependencies
- Custom exception handling
"""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any


class AnalyticsError(Exception):
    """Custom exception raised when analytics calculations encounter errors."""
    pass


class ChatAnalyticsEngine:
    """
    Computes statistical metrics and distributions across chat logs:
    - Total messages
    - Messages per day (daily time-series and average)
    - Active users (participation metrics and leaderboard)
    - Most active groups (group ranking by activity)
    - Conversation activity (conversation volume breakdown)
    - Message category distribution (macro and granular)
    - Hourly temporal distribution and sentiment balance
    """

    STOPWORDS: set[str] = {
        "the", "and", "a", "to", "in", "is", "it", "you", "that", "he", "was",
        "for", "on", "are", "as", "with", "his", "they", "i", "at", "be",
        "this", "have", "from", "or", "one", "had", "by", "word", "but", "not",
        "what", "all", "were", "we", "when", "your", "can", "said", "there",
        "use", "an", "each", "which", "she", "do", "how", "their", "if", "will",
        "up", "other", "about", "out", "many", "then", "them", "these", "so",
        "some", "her", "would", "make", "like", "him", "into", "time", "has",
        "look", "two", "more", "write", "go", "see", "number", "no", "way",
        "could", "people", "my", "than", "first", "water", "been", "call", "who",
        "oil", "its", "now", "find", "long", "down", "day", "did", "get", "come",
        "made", "may", "part", "this", "that", "with"
    }

    # Macro category mapping for consistent distribution reporting
    CATEGORY_MAP: dict[str, str] = {
        "general": "general_discussion",
        "greeting": "general_discussion",
        "general_discussion": "general_discussion",
        "question": "questions",
        "questions": "questions",
        "announcement": "announcements",
        "announcements": "announcements",
        "important_update": "important_updates",
        "important_updates": "important_updates",
        "work_related": "work_related",
        "code": "work_related",
        "action_item": "work_related",
    }

    @classmethod
    def compute_analytics(
        cls,
        messages: list[dict[str, Any]],
        conversations_metadata: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Aggregate and calculate analytics for a given list of message dictionaries
        and optional conversation metadata.
        Demonstrates loops, dict operations, lambda sorting, time parsing, and math ratios.
        """
        try:
            if not isinstance(messages, list):
                raise AnalyticsError("Messages must be provided as a list of dictionaries")

            if not messages:
                return {
                    "total_messages": 0,
                    "messages_per_day": {},
                    "avg_messages_per_day": 0.0,
                    "active_users_count": 0,
                    "active_users": [],
                    "most_active_groups": [],
                    "conversation_activity": [],
                    "category_distribution": {
                        "general_discussion": 0,
                        "questions": 0,
                        "announcements": 0,
                        "important_updates": 0,
                        "work_related": 0,
                    },
                    "category_percentages": {
                        "general_discussion": 0.0,
                        "questions": 0.0,
                        "announcements": 0.0,
                        "important_updates": 0.0,
                        "work_related": 0.0,
                    },
                    "avg_message_length": 0.0,
                    "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0},
                    "sentiment_percentages": {"positive": 0.0, "neutral": 0.0, "negative": 0.0},
                    "top_participants": [],
                    "hourly_activity": [0] * 24,
                    "top_keywords": [],
                }

            total_messages = 0
            user_message_counts: dict[str, int] = defaultdict(int)
            daily_message_counts: dict[str, int] = defaultdict(int)
            conversation_message_counts: dict[int, int] = defaultdict(int)
            message_lengths: list[int] = []
            sentiment_counts: dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}

            # Macro category counts
            category_counts: dict[str, int] = {
                "general_discussion": 0,
                "questions": 0,
                "announcements": 0,
                "important_updates": 0,
                "work_related": 0,
            }

            hourly_counts: list[int] = [0] * 24
            all_words: list[str] = []

            for msg in messages:
                if msg.get("is_deleted"):
                    continue

                total_messages += 1
                content = msg.get("content", "")
                sender = msg.get("sender_name") or msg.get("sender_username") or "System"
                conv_id = msg.get("conversation_id", 0)

                # 1. User volume
                user_message_counts[sender] += 1

                # 2. Conversation volume
                if conv_id:
                    conversation_message_counts[conv_id] += 1

                # 3. Message length
                message_lengths.append(len(content))

                # 4. Sentiment counts
                label = msg.get("sentiment_label", "neutral")
                if label in sentiment_counts:
                    sentiment_counts[label] += 1
                else:
                    sentiment_counts["neutral"] += 1

                # 5. Smart Category counts (mapped to macro categories)
                raw_cat = msg.get("category", "general")
                macro_cat = cls.CATEGORY_MAP.get(raw_cat, "general_discussion")
                category_counts[macro_cat] += 1

                # 6. Temporal parsing: Day and Hour
                created_at_str = msg.get("created_at")
                if created_at_str:
                    try:
                        # Extract date string YYYY-MM-DD
                        if "T" in str(created_at_str):
                            date_str = str(created_at_str).split("T")[0]
                        else:
                            date_str = str(created_at_str)[:10]

                        daily_message_counts[date_str] += 1

                        # Hour parsing
                        dt = datetime.fromisoformat(str(created_at_str).replace("Z", "+00:00"))
                        hourly_counts[dt.hour] += 1
                    except (ValueError, TypeError, IndexError):
                        pass

                # 7. Word tokens for vocabulary cloud
                words = [
                    w.lower() for w in content.split()
                    if w.isalpha() and len(w) > 3 and w.lower() not in cls.STOPWORDS
                ]
                all_words.extend(words)

            # Average message length
            avg_len = (
                round(sum(message_lengths) / len(message_lengths), 1)
                if message_lengths
                else 0.0
            )

            # Daily metrics
            days_count = len(daily_message_counts) or 1
            avg_messages_per_day = round(total_messages / days_count, 1)

            # Active users leaderboard
            sorted_users = sorted(
                user_message_counts.items(), key=lambda kv: kv[1], reverse=True
            )
            active_users_list = [
                {
                    "username": name,
                    "count": count,
                    "share_percentage": round((count / total_messages) * 100, 1) if total_messages else 0.0,
                }
                for name, count in sorted_users
            ]

            # Most active groups & conversation activity
            most_active_groups: list[dict[str, Any]] = []
            conversation_activity: list[dict[str, Any]] = []

            # Use metadata lookup if available
            conv_meta_dict: dict[int, dict[str, Any]] = {}
            if conversations_metadata:
                for c in conversations_metadata:
                    conv_meta_dict[c.get("id", 0)] = c

            sorted_convs = sorted(
                conversation_message_counts.items(), key=lambda kv: kv[1], reverse=True
            )

            for cid, count in sorted_convs:
                meta = conv_meta_dict.get(cid, {})
                conv_type = meta.get("type", "direct")
                conv_title = meta.get("title") or f"Conversation #{cid}"

                activity_entry = {
                    "conversation_id": cid,
                    "title": conv_title,
                    "type": conv_type,
                    "message_count": count,
                    "participant_count": meta.get("participant_count", 2),
                }
                conversation_activity.append(activity_entry)

                if conv_type == "group":
                    most_active_groups.append(activity_entry)

            # Top keywords
            word_counter = Counter(all_words)
            top_keywords = [
                {"word": word, "frequency": freq}
                for word, freq in word_counter.most_common(12)
            ]

            # Category percentages
            category_percentages = {
                cat: round((cnt / total_messages) * 100, 1) if total_messages else 0.0
                for cat, cnt in category_counts.items()
            }

            # Sentiment percentages
            total_rated = sum(sentiment_counts.values()) or 1
            sentiment_percentages = {
                k: round((v / total_rated) * 100, 1) for k, v in sentiment_counts.items()
            }

            return {
                "total_messages": total_messages,
                "messages_per_day": dict(sorted(daily_message_counts.items())),
                "avg_messages_per_day": avg_messages_per_day,
                "active_users_count": len(user_message_counts),
                "active_users": active_users_list,
                "top_participants": active_users_list[:5],
                "most_active_groups": most_active_groups[:5],
                "conversation_activity": conversation_activity[:10],
                "category_distribution": category_counts,
                "category_percentages": category_percentages,
                "avg_message_length": avg_len,
                "sentiment_distribution": sentiment_counts,
                "sentiment_percentages": sentiment_percentages,
                "hourly_activity": hourly_counts,
                "top_keywords": top_keywords,
            }

        except Exception as exc:
            if isinstance(exc, AnalyticsError):
                raise
            raise AnalyticsError(f"Error calculating chat analytics: {str(exc)}") from exc
