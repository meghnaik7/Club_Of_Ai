# ClubOps AI 🚀

> **Autonomous AI-Powered Operations & Event Orchestration Platform for College Clubs**

ClubOps AI is a full-stack event and operations management platform designed specifically for collegiate clubs, student societies, and campus organizations. Powered by multi-agent workflows, voice interfaces, retrieval-augmented generation (RAG), and proactive hierarchy-aware scheduling, ClubOps AI eliminates operational chaos and automates everything from task delegation to post-event retrospectives.

---

## 🌟 Key Features

### 🤖 1. Agentic AI & Autonomous Workflows

- **Multi-Agent Task Planning**: Converts high-level club goals (e.g., *"Organize Hackathon 2026"*) into actionable, scheduled sub-tasks with estimated effort.
- **Action Proposal & Approval Loops**: AI suggests logistical assignments, budget allocations, and venue reservations that leads can review and approve with one click.
- **Context-Aware Recommendations**: Intelligently balances volunteer workloads and identifies bottlenecks before deadlines slip.

### 🎙️ 2. Multilingual Voice Assistant

- **Hands-Free Club Management**: Execute commands, log meeting minutes, and check task status via voice.
- **Indic Language Support**: Integrated speech-to-text (STT) and text-to-speech (TTS) powered by Sarvam AI.
- **Live Waveform & Audio Feedback**: Interactive frontend voice modal with real-time waveform visualization.

### 📚 3. Intelligent RAG & Document Hub

- **Club Memory & Knowledge Base**: Upload event guidelines, rules, sponsorship brochures, and past post-mortems (PDF, DOCX, TXT).
- **Contextual Search**: Query past event data to answer queries like *"What was the food budget per head for last year's symposium?"*
- **Automatic Meeting Summarization**: Extracts action items and assigns tasks directly from raw meeting notes.

### ⏰ 4. Smart Scheduling & Hierarchy Escalation Engine

- **Automated Cron Jobs**: Background scheduler monitors active tasks and identifies overdue deliverables.
- **Strict Hierarchy Escalation**:
  - Volunteer missing deadline → Reminder sent to Volunteer.
  - Continued inactivity → Escalated to Team Lead.
  - Critical path blocker → Escalated to Club President / Core Heads.
- **Notification Deduplication**: Prevents alert fatigue with intelligent digest grouping.

### 🛡️ 5. Role-Based Access Control (RBAC) & Team Management

- **Tiered Permissions**: Super Admin, Club Heads, Team Leads, and Volunteers with granular data access.
- **Audit Logging**: Comprehensive audit trail tracking all actions, permission changes, and automated decisions.

### 🧠 6. Long-Term Agent Memory & Guardrails

- **Deduplicated Agent Memory**: Preserves organizational knowledge across academic semesters and executive board transitions.
- **Safety Guardrails**: Validates agent actions against club policies, preventing hallucinated actions or unauthorized privilege escalation.

---

## 🏗️ Architecture & Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Lucide Icons |
| **Backend API** | FastAPI (Python 3.10+), Pydantic v2, Uvicorn |
| **Database & ORM** | PostgreSQL, SQLAlchemy 2.0 (Async), Alembic |
| **Agentic Framework** | LangGraph, LangChain, PostgreSQL Checkpointer |
| **Voice & Speech** | Sarvam AI API (STT & TTS), Web Audio API |
| **Task Queue & Scheduler** | APScheduler, Background Worker Tasks |
| **Containerization** | Docker, Docker Compose |

---

## 📁 Repository Structure

```text
Club_Of_Ai/
├── ai/
│   └── rag/
│       ├── document_loaders/
│       ├── chunking/
│       └── retrieval/
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── guardrails/
│   │   ├── memory/
│   │   ├── models/
│   │   ├── scheduler/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── voice/
│   │
│   ├── tests/
│   │   ├── scheduler/
│   │   ├── agents/
│   │   └── RBAC/
│   │
│   └── requirements.txt
│
├── docker/
│   └── Production and local Docker configurations
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   │
│   ├── package.json
│   └── vite.config.ts
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

Make sure the following are installed:

- **Node.js** v18+
- **Python** 3.10+
- **PostgreSQL** 14+
- **Git**
- **Docker** *(optional, but recommended)*

---

### 1. Clone the Repository

```bash
git clone https://github.com/meghnaik7/Club_Of_Ai.git
cd Club_Of_Ai
```

---

### 2. Environment Setup

Create `.env` files in the root and backend directories.

#### Root `.env`

```bash
cp .env.example .env
```

#### Backend `.env`

```bash
cp backend/.env.example backend/.env
```

Configure the required environment variables:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/clubops
SECRET_KEY=your_super_secret_jwt_key
SARVAM_API_KEY=your_sarvam_ai_key
LLM_API_KEY=your_gemini_or_openai_key
```

> ⚠️ **Never commit `.env` files or API keys to GitHub.**

---

## ⚙️ Backend Setup

Navigate to the backend:

```bash
cd backend
```

### Create Virtual Environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Database Migrations

```bash
alembic upgrade head
```

### Seed Demo Data

```bash
python seed_data.py
```

### Start FastAPI Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend:

```text
http://localhost:8000
```

Swagger API Documentation:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

---

## 💻 Frontend Setup

Open a new terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

## 🐳 Running with Docker

Run the entire application using Docker Compose:

```bash
docker-compose up --build -d
```

This starts:

- PostgreSQL
- FastAPI Backend
- React Frontend

### View Logs

```bash
docker-compose logs -f
```

### Stop Services

```bash
docker-compose down
```

### Rebuild Containers

```bash
docker-compose up --build
```

---

## 🧪 Running Tests

The backend contains automated tests covering:

- RBAC
- Agent workflows
- Task management
- Scheduler
- Hierarchy escalation
- Notifications

Run the complete test suite:

```bash
cd backend
pytest
```

### Hierarchy Escalation Tests

```bash
pytest tests/scheduler/test_hierarchy_notification.py
```

### Agentic Workflow Tests

```bash
pytest tests/test_agentic_workflows_and_feedback.py
```

---

## 🔄 Core Workflow

```text
                    Club Goal
                       │
                       ▼
                ┌──────────────┐
                │   AI Agent   │
                │ Task Planner │
                └──────┬───────┘
                       │
                       ▼
               Generate Subtasks
                       │
                       ▼
              Assign Team Members
                       │
                       ▼
               Schedule Deadlines
                       │
                       ▼
              Monitor Progress
                       │
              ┌────────┴────────┐
              │                 │
           On Time           Overdue
              │                 │
              ▼                 ▼
          Continue        Send Reminder
                                │
                                ▼
                           Team Lead
                           Escalation
                                │
                                ▼
                       Club Head / Core
```

---

## 🧠 AI Architecture

```text
                         ┌────────────────────┐
                         │     User Input     │
                         └─────────┬──────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                  │
                ▼                  ▼                  ▼
          Text Interface     Voice Interface      Documents
                │                  │                  │
                │             Sarvam AI              │
                │                  │                  │
                └──────────┬───────┴──────────┬───────┘
                           ▼                  ▼
                     AI Orchestrator       RAG
                           │                  │
                           └────────┬─────────┘
                                    ▼
                              LangGraph
                           Agentic Workflow
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
                 Planning       Memory         Guardrails
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                              Action Proposal
                                    │
                                    ▼
                              Human Approval
                                    │
                                    ▼
                              Task Execution
```

---

## 🔐 Security

ClubOps AI implements multiple security mechanisms:

- JWT-based authentication
- Role-Based Access Control (RBAC)
- Granular permissions
- API validation using Pydantic
- Environment-based secret management
- Audit logging
- AI action guardrails
- Approval-based sensitive actions

---

## 📊 Example Use Case

Imagine a college club wants to organize:

> **TechFest 2026**

Instead of manually creating and assigning dozens of tasks, the club head can provide the goal to ClubOps AI.

The AI can break it down into:

```text
TechFest 2026
│
├── Venue Management
│   ├── Find available venues
│   ├── Contact administration
│   └── Confirm booking
│
├── Sponsorship
│   ├── Prepare sponsorship deck
│   ├── Identify companies
│   ├── Send proposals
│   └── Track responses
│
├── Marketing
│   ├── Design poster
│   ├── Create social media campaign
│   ├── Publish announcement
│   └── Track registrations
│
├── Technical
│   ├── Registration system
│   ├── Website
│   ├── Event infrastructure
│   └── Technical support
│
└── Operations
    ├── Volunteer allocation
    ├── Food arrangements
    ├── Certificates
    └── Event-day coordination
```

The system then assigns tasks, schedules deadlines, monitors progress, and escalates blockers automatically.

---

## 🎯 Why ClubOps AI?

College clubs often manage their operations through a combination of:

- WhatsApp groups
- Google Sheets
- Spreadsheets
- Notion pages
- Manual reminders
- Scattered documents
- Human follow-ups

This can lead to:

- Information fragmentation
- Missed deadlines
- Poor task visibility
- Repetitive administrative work
- Knowledge loss after leadership transitions
- Difficulties coordinating large volunteer teams

**ClubOps AI brings these workflows together into one intelligent operational platform.**

---

## 🛣️ Roadmap

### Phase 1 — Core Platform

- [x] Authentication
- [x] RBAC
- [x] User management
- [x] Task management
- [x] Event management
- [x] Team management

### Phase 2 — AI Layer

- [x] Agentic task planning
- [x] Action proposals
- [x] AI recommendations
- [x] Agent memory
- [x] Guardrails

### Phase 3 — Knowledge & Voice

- [x] Document ingestion
- [x] RAG pipeline
- [x] Knowledge search
- [x] Voice assistant
- [x] Multilingual voice support

### Phase 4 — Automation

- [x] Background scheduler
- [x] Deadline monitoring
- [x] Hierarchy escalation
- [x] Notification deduplication

### Phase 5 — Future Enhancements

- [ ] Advanced analytics
- [ ] Mobile application
- [ ] Calendar integrations
- [ ] WhatsApp integration
- [ ] Advanced event forecasting
- [ ] Cross-club knowledge sharing
- [ ] AI-generated event retrospectives

---

## 🤝 Contributing

Contributions are welcome!

### 1. Fork the Project

Create your own fork of the repository.

### 2. Create a Feature Branch

```bash
git checkout -b feature/AmazingFeature
```

### 3. Commit Your Changes

```bash
git add .
git commit -m "Add AmazingFeature"
```

### 4. Push the Branch

```bash
git push origin feature/AmazingFeature
```

### 5. Open a Pull Request

Create a Pull Request from your feature branch to the main repository.

---

## 👥 Team

**ClubOps AI**

Built for college clubs, student organizations, and campus communities.

---

## 📄 License

This project is currently intended for educational, experimental, and hackathon purposes.

---

## ⭐ Support the Project

If you find **ClubOps AI** useful, consider giving the repository a ⭐ on GitHub!

**Repository:**  
https://github.com/meghnaik7/Club_Of_Ai

---

## 🚀 ClubOps AI

> **Plan smarter. Delegate faster. Remember everything. Operate autonomously.**
