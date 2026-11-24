# CONNECTX – COMPREHENSIVE ACADEMIC PROJECT REPORT
**Degree:** Bachelor of Technology in Computer Science & Engineering  
**Project Title:** ConnectX – Python-Based Real-Time Multi-User Chat System  
**Academic Year:** 2025–2026  

---

## 1. Abstract

**ConnectX** is a full-stack, real-time multi-user communication system engineered using pure Python on the server and modern web technologies on the client. Designed to satisfy rigorous software engineering curriculum requirements, the platform implements real-time bidirectional communication using Flask-SocketIO, session-based authentication using Flask-Login, database modeling using Flask-SQLAlchemy on SQLite, and a custom responsive 3-pane user interface with dynamic theme switching (Dark/Light).

A key academic contribution of ConnectX is its **Pure Python Message Intelligence Engine**—a suite of natural language processing and statistical tools developed without third-party paid AI services. The engine performs Shannon Informational Entropy spam detection, rule-based VADER sentiment analysis, extractive TF-IDF summarization, regex-based semantic categorization, and recursive thread hierarchy construction. The system includes 22 automated test cases with 100% pass rate, comprehensive administrative oversight, and complete documentation.

---

## 2. Literature Review & Technical Background

Traditional web applications rely on the HTTP request-response cycle. In chat applications, polling introduces unacceptable latency and HTTP header overhead. WebSockets solve this by establishing a persistent full-duplex TCP connection, enabling the server to push updates instantly.

Many contemporary chat applications rely on third-party commercial AI APIs (e.g. OpenAI, Google Cloud NLP) for sentiment and moderation. However, in academic and self-hosted environments, external dependencies introduce recurring costs, latency, network failure points, and data privacy vulnerabilities. ConnectX demonstrates that classical computer science algorithms—Shannon Entropy, lexicon-based valence scoring, and term-frequency graph ranking—implemented in pure Python can provide responsive, private, and deterministic message intelligence directly on local infrastructure.

---

## 3. System Architecture & Methodology

ConnectX is architected using the **Application Factory Pattern** (`create_app()`) and a **Three-Tier Layered Architecture**:

1. **Presentation Layer (Frontend):**
   - HTML5 semantic structure and Jinja2 templates.
   - CSS3 design system with custom properties (`--bg-primary`, `--bubble-self`) supporting instantaneous Dark/Light theme switching.
   - JavaScript client managing Socket.IO events, DOM updates, optimistic message dispatch, and Web Audio API synthesis for zero-asset audio notifications.

2. **Application & Service Layer (Flask Backend):**
   - Five decoupled Blueprints: `auth` (credentials & profiles), `chat` (channels & view routing), `api` (REST endpoints & file uploads), `admin` (user governance & moderation), and `analytics` (visual reporting & interactive NLP lab).
   - In-memory thread-safe presence management (`SocketStateManager` with `threading.RLock`) managing multi-tab user connections.
   - Pure Python intelligence services: `SpamDetector`, `SentimentAnalyzer`, `MessageCategorizer`, `ConversationSummarizer`, and `MessageProcessor`.

3. **Data Persistence Layer:**
   - SQLite relational database mediated by SQLAlchemy ORM.
   - Fully normalized (3NF) schema with cascading foreign keys and composite indexing on frequently queried columns (`conversation_id`, `created_at`).

---

## 4. Database Schema Design

The relational database consists of 10 tables:
* `users`: Stores usernames, unique email addresses, PBKDF2 password hashes, avatar paths, online status, and roles (`admin`, `moderator`, `user`).
* `conversations`: Stores channel metadata for both 1-to-1 direct chats and multi-user groups.
* `conversation_members`: Stores group participation, roles (`admin`, `member`), mute status, and read message pointers.
* `messages`: Stores message body, sender references, self-referential foreign keys (`parent_id`) for thread replies, sentiment scores, spam metrics, and categories.
* `attachments`: Stores metadata for uploaded files, images, and audio clips.
* `message_status`: Tracks delivery timestamps and recipient read receipts.
* `message_reactions`: Stores emoji reaction associations per user and message.
* `notifications`: Stores system alerts and mention triggers.
* `user_settings`: Stores per-user theme and audio preferences.
* `audit_logs`: Immutable security audit log storing user actions, targets, details, and client IP addresses.

---

## 5. Algorithmic Implementations (Pure Python NLP)

### 5.1 Shannon Informational Entropy Spam Detection
To detect character flooding and gibberish spam, ConnectX calculates Shannon Entropy:
$$H(X) = -\sum_{i=1}^{n} P(x_i) \log_2 P(x_i)$$
Where $P(x_i)$ represents the probability of character $x_i$ appearing in the string. Texts exhibiting low entropy ($< 2.2$) combined with high length indicate repetitive flooding. This is coupled with sliding window rate limiting and uppercase character ratio checks.

### 5.2 Rule-Based Sentiment Analysis
The sentiment analyzer evaluates word tokens against an academic valence dictionary ($-3.0$ to $+3.0$). The algorithm:
1. Detects booster modifiers (`very`, `extremely`) to amplify valence.
2. Tracks a 3-word preceding negation window (`not`, `never`), reversing valence by a factor of $-0.74$.
3. Checks for ALL CAPS emphasis and punctuation markers (`!`).
4. Evaluates emoji polarity (e.g. `🔥`, `🚀`, `😢`).
5. Normalizes raw valence sums into $[-1.0, 1.0]$ using hyperbolic normalization:
$$\text{Compound Score} = \frac{\sum s}{\sqrt{(\sum s)^2 + 15}}$$

### 5.3 Extractive Conversation Summarization
The extractive summarizer generates structured briefing bullets:
1. Filters messages against a set of common English stopwords.
2. Computes normalized term frequencies for all content words.
3. Scores each sentence based on the average weight of its constituent terms.
4. Adds decision boosts for sentences containing agreement markers (`decided`, `confirmed`) or action markers (`todo`, `deadline`).
5. Extracts and chronologically re-orders the highest-scoring sentences.

---

## 6. Architecture & Concept Demonstrations

| Curriculum Concept | ConnectX Implementation Location |
| :--- | :--- |
| **Variables & Primitive Types** | Integer limits, float entropy, binary signatures in `app/services/academic_showcase.py` |
| **Operators (Arithmetic, Bitwise)** | Bitwise role masks (`PERM_ADMIN = 0b100`, `PERM_MODERATOR = 0b010`) |
| **Conditionals & Ternary** | Message tier evaluation and user verification status assignment |
| **Loops & Loop-Else** | `for-else` activity checks, `while` sentinels, `enumerate()` iterations |
| **Functions & Decorators** | Higher-order decorators (`@admin_required`, `@log_execution`), `*args`, `**kwargs` |
| **Recursion** | Depth-first hierarchical message reply tree builder (`build_nested_thread_tree`) |
| **Collections (Sets, Tuples, Dicts)**| Set intersection for channel members, tuple unpacking, dictionary comprehensions |
| **String Operations & Regex** | Regex user mention parsing (`@username`), link auto-hyperlinking, slicing |
| **Classes & OOP** | Encapsulation (`@property`), inheritance (`UserMixin`), polymorphism |
| **File Operations** | Text, JSON, and CSV read/write using `with open(...)` context managers |
| **Custom Exceptions** | `ChatValidationError`, `ProcessingError` with `try-except-else-finally` |
| **Database Integration** | Declarative SQLAlchemy ORM models with cascading relationships |
| **Standard Libraries** | `math`, `re`, `datetime`, `collections`, `itertools`, `hashlib` |

---

## 7. Testing, Results & Verification

ConnectX includes an automated test suite executed via Pytest. The suite tests in-memory SQLite instances (`sqlite:///:memory:`) to guarantee complete test isolation:
* **Authentication Suite (6 tests):** Validates account registration, duplicate checks, password verification, session termination, and suspension enforcement.
* **Chat Channels Suite (4 tests):** Tests 1-to-1 conversation creation, direct chat idempotency, group creation, member management, and keyword/category search.
* **Python Intelligence Suite (6 tests):** Validates the 15-point academic syllabus audit, recursive reply trees, sentiment valence, spam entropy, categorization, and summarization.
* **Admin Suite (4 tests):** Tests role authorization, dashboard access, ban toggles, and announcement broadcasting.
* **SocketIO Suite (2 tests):** Tests multi-tab presence tracking and typing indicator timeouts.

**Final Test Result:** `22 passed in 9.41s` (100% Pass Rate).

---

## 8. Conclusion

ConnectX fulfills all design requirements for a production-grade, real-time messaging application while demonstrating the depth and power of Python for systems engineering, database modeling, and natural language algorithms. Built from scratch without external paid services, the project serves as a comprehensive capstone engineering submission.
