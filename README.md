# CONNECTX – Python-Based Real-Time Multi-User Chat System
**Degree:** Bachelor of Technology (B.Tech) in Computer Science & Engineering  
**Academic Year:** 2025–2026  

---

## 🚀 Overview

**ConnectX** is an enterprise-grade, real-time multi-user communication and messaging platform architected in pure Python. The system provides low-latency bidirectional communication through WebSockets (Flask-SocketIO), secure session-based authentication (Flask-Login), relational database persistence (Flask-SQLAlchemy on SQLite), and a modern, responsive 3-pane user interface with dark and light themes.

The system incorporates **Pure Python Message Intelligence**—a suite of natural language processing and statistical engines implemented from scratch in pure Python without reliance on external paid AI APIs.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend Language** | Python 3.14+ |
| **Web Framework** | Flask 3.1, Jinja2 |
| **Real-Time WebSockets** | Flask-SocketIO 5.7, simple-websocket |
| **ORM & Database** | Flask-SQLAlchemy 3.1, SQLite 3 |
| **Authentication & Security**| Flask-Login 0.6, Flask-WTF, Werkzeug (PBKDF2-HMAC-SHA256) |
| **Frontend UI/UX** | HTML5, CSS3 Variables (Light/Dark themes), JavaScript (ES6+), Web Audio API |
| **Automated Testing** | Pytest 9.1 (22 automated test suites) |

---

## 💻 Python Virtual Environment Setup Guide

Follow these step-by-step instructions to create an isolated Python virtual environment on your operating system:

### Option A: Windows (PowerShell or Command Prompt)
1. **Open PowerShell as Administrator or standard terminal in the project directory:**
   ```powershell
   cd ConnectX
   ```

2. **Create a clean virtual environment named `venv`:**
   ```powershell
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   * **In PowerShell:**
     ```powershell
     # If script execution is restricted, temporarily enable it for current process:
     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
     .\venv\Scripts\Activate.ps1
     ```
   * **In Command Prompt (cmd.exe):**
     ```cmd
     venv\Scripts\activate.bat
     ```

4. **Verify the active environment:**
   ```powershell
   python -c "import sys; print(sys.executable)"
   # Should point to: ...\ConnectX\venv\Scripts\python.exe
   ```

5. **Upgrade pip and install dependencies:**
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

### Option B: macOS / Linux (bash / zsh)
1. **Navigate to the project root:**
   ```bash
   cd ConnectX
   ```

2. **Create the virtual environment:**
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## ⚡ Running ConnectX

### 1. Environment Variables Configuration
Copy the template configuration into `.env`:
```bash
cp .env.example .env     # On Linux/macOS
copy .env.example .env   # On Windows Command Prompt
```

### 2. Populate Sample Academic Database
Initialize database tables and verified test accounts (Alice, Bob, Charlie, Prof Sharma, Admin):
```bash
python seed_data.py
```
*Pre-configured accounts:*
* **Administrator:** `admin` / `Admin@123456`
* **Faculty:** `prof_sharma` / `Prof@123456`
* **Student 1:** `alice` / `Alice@123456`
* **Student 2:** `bob` / `Bob@123456`
* **Student 3:** `charlie` / `Charlie@123456`

### 3. Launch the Application
```bash
python run.py
```
Open **http://127.0.0.1:5000** in your browser.

### 4. Health-Check Endpoint
Check system responsiveness and database connectivity:
* **URL:** `http://127.0.0.1:5000/health`
* **Sample Response:**
  ```json
  {
    "status": "healthy",
    "service": "ConnectX Real-Time Chat Backend",
    "database": "connected",
    "version": "1.0.0"
  }
  ```

---

## 🧪 Automated Testing

ConnectX includes comprehensive test coverage across models, authentication, real-time sockets, and NLP algorithms:

```bash
python -m pytest -v
```

**Results:**
```
============================= 22 passed in 9.41s ==============================
```

---

## 🧠 Python Message Intelligence Features

| Feature | Implementation | Description |
| :--- | :--- | :--- |
| **Spam Detection** | `SpamDetector` | Computes Shannon informational entropy, capitalization ratios, repetition patterns, and sliding window rate limits. |
| **Sentiment Analysis** | `SentimentAnalyzer` | Pure Python rule-based engine calculating token valences, negation damping, ALL CAPS emphasis, and hyperbolic score normalization. |
| **Categorization** | `MessageCategorizer` | Classifies messages into `question`, `code`, `action_item`, `announcement`, `greeting`, or `general` via regex and linguistic tokens. |
| **Summarization** | `ConversationSummarizer` | Extractive summarizer ranking sentences using stopword-filtered term frequency (TF), decision markers, and recency weights. |
| **Recursive Threading** | `MessageProcessor` | Recursively traverses hierarchical reply trees calculating branch depth and structured nested threads. |
| **Chat Analytics** | `ChatAnalyticsEngine` | Computes 24-hour temporal distributions, mean character lengths, and vocabulary frequency distributions. |

---

## 🎓 Architecture Concept Mapping

Every architectural and algorithmic concept is meaningfully demonstrated in ConnectX:
1. **Variables & Data Types:** `app/services/academic_showcase.py` (lines 18–30)
2. **Operators (Arithmetic, Bitwise, Comparison):** Bitwise permissions (`PERM_ADMIN | PERM_MODERATOR`)
3. **Conditional Statements:** `if-elif-else` branches and ternary expressions
4. **Loops:** `for-else`, `while`, and `enumerate()` across message queues
5. **Functions & Decorators:** Higher-order decorators (`@log_execution`, `@admin_required`)
6. **Recursion:** Nested thread replies (`build_nested_thread_tree`, `count_nested_replies`)
7. **Collections:** Lists, immutable tuples, sets (stopword filtering), dictionary comprehensions
8. **String Operations:** Slicing, regex entity extraction, f-string interpolation
9. **Classes & OOP:** Inheritance (`UserMixin`), encapsulation (`@property`), polymorphism
10. **File Handling:** Text, JSON, and CSV reading/writing using `with open(...)` context managers
11. **Exception Handling:** Custom exception hierarchies (`ProcessingError`, `ChatValidationError`)
12. **Database Connectivity:** SQLAlchemy ORM entities with foreign keys and cascade deletions
13. **Python Standard Libraries:** `math`, `re`, `datetime`, `collections`, `itertools`, `hashlib`

---

## 📄 Academic Deliverables Included
* **System Architecture Specification:** [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md)
* **Database ER Diagram & Dictionary:** [`docs/DATABASE_ER.md`](docs/DATABASE_ER.md)
* **Project Report:** [`docs/PROJECT_REPORT.md`](docs/PROJECT_REPORT.md)
* **Viva Questions & Answers (50+ items):** [`docs/VIVA_QUESTIONS_ANSWERS.md`](docs/VIVA_QUESTIONS_ANSWERS.md)
* **Project Defense Presentation Outline:** [`docs/PRESENTATION_OUTLINE.md`](docs/PRESENTATION_OUTLINE.md)
