# 💳 Bounded Agentic Checkout

> **Project Track**: Track 01 — Bounded Agentic Checkout

---

## 📌 Project Overview

When autonomous AI agents buy things on behalf of users, they need hard boundaries. Giving an LLM access to a credit card or payment API without limits is risky — a hallucination or prompt injection could drain a bank account or buy the wrong items.

This project implements **Bounded Agentic Checkout**:
An AI buyer agent (powered by OpenAI Chat Completions function-calling) is given a **scoped spending mandate** (e.g., *only groceries, max ₹500 per transaction, max ₹2,000 total, valid for 7 days*). 

Every purchase attempt is evaluated against the mandate rules:
- **Approved purchases** create real test-mode orders on the **Razorpay Orders API** and deduct from the mandate budget.
- **Blocked attempts** (e.g. over-budget, category mismatch, expired, or revoked) are rejected before calling Razorpay.
- **100% of attempts** are written to a SQLite audit trail and displayed live on a Streamlit dashboard.

---

## 🏗️ How It Works

```
                        +---------------------------+
                        |  User gives goal to Agent |
                        | ("Reorder usual groceries")
                        +-------------+-------------+
                                      |
                                      v
                        +---------------------------+
                        |   AI Buyer Agent (OpenAI) |
                        |   - Browses catalog items |
                        |   - Selects cart items    |
                        +-------------+-------------+
                                      |
                                      | calls attempt_checkout()
                                      v
+-------------------------------------------------------------------------------+
| Mandate Guardrail Engine (backend/mandate.py)                                 |
|                                                                               |
| Checks in exact order:                                                        |
|  1. Does mandate exist?                                                       |
|  2. Is mandate revoked?                                                       |
|  3. Is current time before expiry?                                            |
|  4. Does item category match mandate category? (e.g. groceries)               |
|  5. Is amount <= per-transaction cap? (e.g. <= ₹500)                          |
|  6. Is spent + amount <= total cap? (e.g. <= ₹2,000)                          |
+-------------------------------------+-----------------------------------------+
                                      |
                +---------------------+---------------------+
                | (If Approved)                             | (If Blocked)
                v                                           v
+-------------------------------+         +-------------------------------------+
| Razorpay Orders API           |         | Audit Trail (backend/audit.py)      |
| - Creates test order          |         | - Logs attempt, timestamp, agent ID,|
| - Injects mandate notes       |         |   items, approved flag & reason     |
+---------------+---------------+         +-------------------------------------+
                |                                           ^
                | On Order Success                          |
                +-------------------------------------------+
                |
                v
  Increment spent_paise in SQLite
```

---

## 📁 Project Structure

```
razorpay-agentic-checkout/
├── backend/
│   ├── db.py                 # SQLite database setup (mandates, catalog, orders, audit_log)
│   ├── mandate.py            # Mandate check rules (caps, expiry, category, revocation)
│   ├── merchant.py           # Catalog lookup & checkout handler
│   ├── razorpay_client.py    # Razorpay Orders API test-mode client
│   ├── audit.py              # Audit logging for all checkout attempts
│   ├── agent.py              # OpenAI function-calling buyer agent loop
│   ├── demo_scenarios.py     # 5-step test script for demoing pass/fail cases
│   └── seed.py               # Database seeder (sample grocery catalog & mandate)
├── frontend/
│   └── dashboard.py          # Streamlit live dashboard with telemetry & agent studio
├── requirements.txt          # Project dependencies
└── README.md                 # Project documentation
```

---

## ⚡ Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables
Create a `.env` file in the project folder with your test keys:
```env
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
OPENAI_API_KEY=your_openai_api_key
```

### 3. Seed the Database
```bash
python backend/seed.py
```

### 4. Run the 5 Demo Scenarios Script
Runs all 5 key test cases in sequence:
```bash
python backend/demo_scenarios.py
```

### 5. Run the Autonomous Buyer Agent CLI
```bash
python backend/agent.py
```

### 6. Launch the Streamlit Dashboard
```bash
python -m streamlit run frontend/dashboard.py
```

---

## 🧪 The 5 Demo Scenarios

The script `backend/demo_scenarios.py` tests and demonstrates the core mandate flows:

1. **Scenario 1: Normal Purchase** — Atta + Oil (₹420) within the ₹500 cap -> **Approved** (Razorpay order created).
2. **Scenario 2: High Cumulative Spend** — Second purchase bringing total spend close to the ₹2,000 total cap -> **Approved**.
3. **Scenario 3: Exceeds Per-Txn Cap** — Basket worth ₹580 (> ₹500 limit) -> **Blocked** (`exceeds per-transaction cap`, Razorpay skipped).
4. **Scenario 4: Revoked Mandate** — Sets `revoked = 1` -> **Blocked** (`mandate revoked`).
5. **Scenario 5: Expired Mandate** — Sets expiry to past date -> **Blocked** (`mandate expired`).

---

## 📊 Dashboard Features

- **Mandate Status Card**: Shows active/revoked status, category, caps, spend, and a visual progress bar.
- **Live Telemetry**: Counters for total attempts, approved orders, blocked attempts, and total ₹ transacted.
- **AI Buyer Agent Studio**: Type custom shopping prompts or click presets to watch the LLM reason, call tools, and place/adapt orders live.
- **Merchant Catalog Tab**: Browse items and test manual cart checkouts.
- **Live Audit Trail**: Full inspectable history of all attempts with item breakdowns and Razorpay Order IDs.
- **Sidebar Controls**: One-click buttons to revoke/reactivate mandate, reset spend, or replay demo scenarios.

---

## 🔍 Scope, Trade-offs

Since this was built in a 6-day sprint as a working prototype, here is an honest look at current scope and future improvements:

### What it handles well:
- Strict sequential mandate checks (fail-closed design).
- Spent budget only increments **after** a Razorpay order succeeds.
- Every single attempt (pass or fail) is auditable in SQLite.
- Multi-turn tool calling with fallback handling if a requested model is unavailable.

