# 🎓 Razorpay Project Review & Internship Interview Guide

This guide is designed to help you explain every single line, architectural choice, trade-off, and alternative for **Bounded Agentic Checkout** (Track 01) to Razorpay interviewers and code reviewers.

---

## 1. 💡 The 30-Second Elevator Pitch (Layman Analogy)

> **"Imagine giving your child a add-on credit card to buy groceries."**
>
> If you give them an unrestricted card, they might accidentally spend ₹10,000 on video games. But if you give them a **smart mandate card** with rules — *"only groceries, max ₹500 per order, max ₹2,000 total budget, expires in 7 days"* — the card reader automatically blocks video games or over-budget orders before charging your bank.
> 
> **Bounded Agentic Checkout** is that smart mandate card for AI Buyer Agents. When an autonomous LLM shops online, our system acts as a deterministic security guard between the AI and the Razorpay Payment Gateway.

---

## 2. ❓ Why Does This Problem Exist?

- **The Problem with AI Agents**: Modern LLMs (like OpenAI GPT models) can call APIs and buy products autonomously. However, LLMs can hallucinate, misunderstand prices, get prompt-injected, or run wild in loops.
- **The Financial Risk**: You cannot trust an LLM directly with raw payment credentials or uncapped API endpoints.
- **The Solution**: A **Bounded Spending Mandate Layer**. The payment gateway (Razorpay) is **never** invoked unless the transaction passes strict, non-LLM, deterministic code checks.

---

## 3. 🛠️ Tech Stack & Architectural Choices ("Why vs Why Not")

Interviewers love asking **"Why did you choose X instead of Y?"**. Here is the exact breakdown:

### A. Python (Programming Language)
- **Why Python?**
  - Standard language for AI/LLM integrations (OpenAI SDK support is native and updated first).
  - Fast execution for prototype building, clean syntax, easy database connection.
- **Why NOT Node.js / TypeScript or Go?**
  - Node.js/Go are great for high-concurrency microservices, but for a 6-day AI sprint project, Python allowed seamless integration between the LLM tool-calling logic and Streamlit UI without needing separate frontend-backend build steps.

---

### B. SQLite (`app.db`) vs PostgreSQL / MongoDB / Redis
- **Why SQLite?**
  - Zero setup, self-contained single-file database (`backend/app.db`). Perfect for local prototypes, demo evaluation, and single-host execution.
  - Supports SQL ACID transactions and standard `Row` factories.
- **Why NOT PostgreSQL?**
  - Postgres requires running a separate server process, managing environment connection strings, migrations, and database hosting. SQLite keeps the project 100% portable for reviewers running `python backend/seed.py`.
- **Why NOT MongoDB (NoSQL)?**
  - Mandate rules, catalog items, and audit logs are strictly structured tabular data. Relational SQL schemas enforce strict data types (e.g. integer paise amounts) and prevent corrupted records.
- **What would change in Production?**
  - In production, we would upgrade SQLite to **PostgreSQL** with **Redis** for distributed locking (using `SELECT ... FOR UPDATE` or Redlock) to prevent race conditions during high-concurrency checkouts.

---

### C. OpenAI Function Calling (`gpt-4o-mini` / `gpt-5.6-terra`) vs LangChain / AutoGen
- **Why Native OpenAI SDK with Tools (`chat.completions.create`)?**
  - **No abstraction bloat**: Native OpenAI function calling is clean, fast, and gives complete control over message history and tool responses.
  - **Deterministic JSON output**: The LLM outputs structured tool arguments (`get_catalog` or `attempt_checkout`) defined by JSON schemas.
- **Why NOT LangChain or AutoGen?**
  - Frameworks like LangChain add heavy abstractions, hidden prompts, complex debugging, and extra dependencies. Writing native tool-calling loops makes the code easier to explain and review line-by-line.
- **Why `gpt-4o-mini` with `gpt-5.6-terra` fallback?**
  - `gpt-4o-mini` is extremely fast, cost-effective, and highly reliable at JSON tool calling. `gpt-5.6-terra` offers deeper reasoning when available.

---

### D. Razorpay Test-Mode Orders API (`razorpay` Python SDK)
- **Why Razorpay Orders API (`client.order.create`)?**
  - In Razorpay's server-side architecture, creating an **Order** (`order_...`) is the fundamental first step before payment capture.
  - It allows attaching custom metadata `notes` (e.g. `mandate_id`, `agent_id`, `reason`), creating an immutable order record on Razorpay's test servers.
- **Why NOT Web Payment Links / Standard Checkout UI?**
  - This project focuses on **agentic (server-to-server)** autonomous checkout where an AI agent initiates the transaction programmatically without manual browser clicks.

---

### E. Streamlit (`frontend/dashboard.py`) vs React / Next.js
- **Why Streamlit?**
  - Allows building a full interactive live telemetry UI directly in Python using standard data structures (`pandas` dataframes, `st.metric`, `st.progress`).
  - Native Python rerun loop (`st.rerun()`) instantly updates UI whenever SQLite database state changes.
- **Why NOT React / Next.js?**
  - Building a React frontend requires a REST API layer (FastAPI/Flask), CORS handling, npm packages, and state management. Streamlit unified the backend logic and dashboard into a single runnable codebase for reviewers.

---

## 4. 📂 File-by-File Technical Deep Dive

Here is how each file works under the hood:

### 1. `backend/db.py` (Data Access Layer)
- **Purpose**: Creates the 4 core SQLite tables and provides CRUD functions.
- **Key Tables**:
  - `mandates`: Stores spending limits (`per_txn_cap_paise`, `total_cap_paise`, `spent_paise`, `expiry`, `revoked`).
  - `catalog`: Merchant items with prices in **paise** (1 INR = 100 paise) to avoid floating-point rounding errors.
  - `orders`: Successfully placed Razorpay orders.
  - `audit_log`: Every single attempt (approved or blocked) with UTC timestamp and item JSON.

### 2. `backend/mandate.py` (Guardrail Rules Engine)
- **Purpose**: Evaluates transactions against spending rules.
- **The 6-Step Rule Order**:
  ```python
  1. Mandate exists?                -> "mandate not found"
  2. Is revoked == 1?               -> "mandate revoked"
  3. Current UTC > expiry?          -> "mandate expired"
  4. Category mismatch?             -> "category not covered by mandate"
  5. Amount > per-txn cap?         -> "exceeds per-transaction cap"
  6. Spent + Amount > total cap?    -> "exceeds remaining total cap"
  ```
- **Why this order matters**: Checking revocation and expiry first prevents wasting CPU/DB lookups on invalid mandates.

### 3. `backend/merchant.py` (Checkout Orchestrator)
- **Purpose**: Coordinates item price calculation, mandate checking, Razorpay order creation, and audit logging.
- **Key Design Decision**:
  - **Pre-check**: Calls `mandate.check_mandate(...)` **before** touching Razorpay.
  - **Razorpay Call**: If approved, calls `razorpay_client.create_order(...)`.
  - **Post-Order Spent Increment**: Calls `mandate.increment_spent(...)` **only after** Razorpay succeeds. (If Razorpay fails, budget is NOT burned!).
  - **Audit Logging**: Always calls `audit.log_attempt(...)` regardless of pass/fail.

### 4. `backend/razorpay_client.py` (Gateway Integration)
- **Purpose**: Initializes `razorpay.Client` using environment keys (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`) and creates test orders.
- **Metadata Handling**: Injects `notes` containing `mandate_id`, `agent_id`, and `reason` (safely truncated to ≤ 250 chars as required by Razorpay API specs).

### 5. `backend/agent.py` (AI Buyer Agent)
- **Purpose**: Multi-turn LLM agent loop using OpenAI tool calling.
- **Tools Exposed**: `get_catalog` and `attempt_checkout`.
- **Adaptive Reasoning**: If an attempt is blocked (e.g. per-txn cap exceeded), the system prompt instructs the agent **not to blindly retry**, but to reduce items or explain why it failed.

### 6. `backend/demo_scenarios.py` (Test Scenario Runner)
- **Purpose**: Resets the database and executes 5 test scenarios:
  1. *Normal Approved Purchase* (Atta + Oil = ₹420)
  2. *High Cumulative Spend Purchase* (Brings spend to ₹1,970 / ₹2,000)
  3. *Per-Txn Cap Exceeded* (₹580 > ₹500 cap -> Blocked)
  4. *Revoked Mandate* (`revoked = 1` -> Blocked)
  5. *Expired Mandate* (Past date -> Blocked)

### 7. `frontend/dashboard.py` (Streamlit Observability Dashboard)
- **Purpose**: Provides real-time visual telemetry:
  - Top Mandate Card with budget utilization bar (`st.progress`).
  - Session counters (Attempts, Approved, Blocked, Total Transacted).
  - Live AI Agent Studio (test custom prompts live).
  - Inspectable Audit Log table with raw JSON viewer.
  - Interactive sidebar controls (Revoke, Reactivate, Reset Spend, Run Scenarios).

---

## 5. 🎯 Tricky Interview Questions & Winner Answers

### Q1: Why do you store money in paise instead of rupees?
> **Answer**:  
> "In financial software, using floating-point numbers (like `420.50`) introduces IEEE 754 binary floating-point rounding errors (e.g., `0.1 + 0.2 = 0.30000000000000004`). To ensure 100% precision, all monetary amounts are stored as integers in **paise** (1 INR = 100 paise), matching standard fintech practices like Razorpay and Stripe APIs."

---

### Q2: What happens if the Razorpay API goes down mid-checkout?
> **Answer**:  
> "Our merchant flow enforces **fail-closed idempotency**. The mandate budget (`spent_paise`) is **only** updated after Razorpay responds with a successful order ID (`order_...`). If Razorpay returns an error or times out, the purchase is marked blocked in our audit trail, but the user's spending limit remains untouched."

---

### Q3: How does the AI agent know what items to buy within budget?
> **Answer**:  
> "The agent uses OpenAI Chat Completions function calling with a system prompt that explicitly provides its `mandate_id` and budget constraints. First, it calls `get_catalog()` to check prices. Then, it calculates a valid item combination before calling `attempt_checkout()`. If a request is blocked, it receives the exact failure reason in the tool response and can adjust its basket."

---

### Q4: How would you handle race conditions / high concurrency in production?
> **Answer**:  
> "In this 6-day prototype, we used SQLite for simplicity. In a high-concurrency production environment with multiple parallel agent checkouts:
> 1. We would migrate to **PostgreSQL**.
> 2. We would use **Redis-based distributed locking** or SQL row locks (`SELECT spent_paise FROM mandates WHERE id = ... FOR UPDATE`) to ensure atomic balance checks and updates.
> 3. We would implement **request idempotency keys** to prevent duplicate order charges on network retries."

---

### Q5: Did you use AI / Antigravity to build this project?
> **Answer**:  
> "Yes! I used **Google Antigravity IDE** as an AI-native pair programming tool. I designed the core mandate architecture, state flow, and financial guardrails, and leveraged Antigravity to rapidly implement code, run database test scripts, and build the Streamlit telemetry dashboard during a 6-day sprint. It allowed me to focus heavily on system architecture and safety invariants."

---

## 💡 Quick Cheat Sheet for the Reviewer

| Concept | File | Implementation |
| :--- | :--- | :--- |
| **Mandate Verification** | `backend/mandate.py` | `check_mandate(mandate_id, amount_paise, category)` |
| **Spent Increment** | `backend/mandate.py` | `increment_spent(mandate_id, amount_paise)` |
| **Razorpay Integration** | `backend/razorpay_client.py` | `create_order(amount_paise, mandate_id, agent_id, reason)` |
| **Audit Log Entry** | `backend/audit.py` | `log_attempt(...)` |
| **AI Tool Calling** | `backend/agent.py` | `run_agent(mandate_id, goal)` |
| **5 Test Scenarios** | `backend/demo_scenarios.py` | `run_all_scenarios()` |
