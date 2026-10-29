# Cryptographically Audited Grievance Management System

A robust, real-time grievance submission and dispute tracking platform designed to guarantee administrative transparency. The system features immutable audit trails via cryptographic hash chaining, strict Service Level Agreement (SLA) lifecycle tracking, and an interactive operational dashboard.

---

## 🌟 Key Features

- **Flexible Grievance Submission**: Submit complaints under categorized domains with customizable privacy modes (**Anonymous** token-based or **Identified** user-linked).
- **Cryptographic Audit Chain**: Every state transition generates a SHA-256 hash linked to the previous transaction hash ($curr\_hash = \text{SHA-256}(prev\_hash + payload)$), ensuring tamper-evident history.
- **On-Demand Chain Verification**: Built-in verification endpoints validate database integrity and instantly flag any database tampering or unauthorized record alterations.
- **Automated SLA Lifecycle & Escalation**: Background workers track resolution deadlines and automatically escalate unresolved tickets across hierarchical tiers (e.g., Tier 1 $\rightarrow$ Tier 2 $\rightarrow$ Tier 3).
- **Interactive Single-Page Dashboard**: Fast asynchronous user interface styled with Tailwind CSS, supporting instant audit verification, live table re-rendering, and anonymous receipt generation.

---

## 🛠️ Architecture & Tech Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Database & ORM**: SQLite via [SQLAlchemy](https://www.sqlalchemy.org/) (2.0 declarative mapping)
- **Data Validation**: [Pydantic v2](https://docs.pydantic.dev/)
- **Background Tasks & Scheduling**: [APScheduler](https://apscheduler.readthedocs.io/)
- **Frontend**: Vanilla JavaScript (Async/Await Fetch API), HTML5, Tailwind CSS CDN

---

## 📁 Project Structure

```text
├── hashlogic.py              # SHA-256 cryptographic hashing & chain verification logic
├── index.html                # Single-page frontend dashboard with live data binding
├── initial_class_diagram.txt # Architecture notes & entity relationship reference
├── main.py                   # FastAPI app, API route controllers & server initialization
├── models.py                 # SQLAlchemy ORM database models (User, Greivances, AuditLog)
├── requirements.txt          # Python project dependencies
├── states.py                 # Lifecycle status definitions, state machine & transitions
└── README.md                 # Project documentation
```

🚀 Getting Started
1. Prerequisites
Ensure you have Python 3.10+ installed.

2. Environment Setup
Bash
# Clone the repository
git clone [https://github.com/](https://github.com/)<hp-dev01>/<AuditNode>.git
cd <AuditNode>

# Create and activate a virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
3. Run the Server
Bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
Access the application:

Interactive UI: http://127.0.0.1:8000/

Interactive API Docs (Swagger UI): http://127.0.0.1:8000/docs

🔒 Verification & Lifecycle Engine
State Machine (states.py): Enforces allowable transitions as tickets move from initial creation through SLA tiers to resolution.

Audit Chaining (hashlogic.py): Computes SHA-256 hashes linking each new audit entry to its predecessor (prev_hash).

Tamper Detection: When /audit/verify/{complaint_id} is invoked, the engine recalculates the chain forward from the genesis record; any manual modification to database rows triggers an immediate verification failure.
