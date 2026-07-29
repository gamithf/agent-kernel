# 🐾 Vetra — Veterinary Clinic AI Assistant

**Built with Agent Kernel | Multi-Agent Orchestration | WhatsApp Integration | RAG-Powered Drug Safety**

---

## 1. Problem Statement

Veterinary clinics face three critical challenges daily:

- **Clinical documentation burden**: Vets spend 30-40% of their workday on paperwork. Voice-dictated observations must be manually transcribed into structured medical records, taking time away from patient care.
- **Drug interaction risks**: With hundreds of veterinary pharmaceuticals available, manually cross-referencing a patient's current medications against a new prescription is error-prone. Missed interactions can lead to severe adverse events in animals.
- **Operational overhead**: Tracking inventory, scheduling follow-ups, and notifying pet owners requires manual coordination across multiple systems, creating friction and potential for missed communications.

Small and mid-size clinics lack the budget for enterprise practice management software. They need an affordable, voice-first AI assistant that works on a platform they already use: **WhatsApp**.

**SDG Alignment**: This solution addresses **SDG 3** (Good Health and Well-being) — specifically Target 3.8 (access to quality essential health services) and Target 3.d (early warning and risk reduction for health emergencies). By reducing medication errors and automating clinical documentation, Vetra directly improves the quality and safety of veterinary care.

---

## 2. Solution Overview

Vetra is a **multi-agent AI system** that transforms how veterinary clinics operate, accessible entirely through WhatsApp.

### Architecture

```
                   ┌─────────────────────────────┐
                   │    WhatsApp (Vet sends       │
                   │    text, voice note, image)  │
                   └──────────┬──────────────────┘
                              │
                   ┌──────────▼──────────────────┐
                   │  VetraWhatsAppHandler        │
                   │  (custom audio transcription)│
                   └──────────┬──────────────────┘
                              │
                   ┌──────────▼──────────────────┐
                   │       Agent Kernel           │
                   │   ┌──────────────────────┐  │
                   │   │    vetra_triage       │  │
                   │   │  (orchestrator —      │  │
                   │   │   OpenAI handoffs)    │  │
                   │   └────┬──────┬──────┬───┘  │
                   │        │      │      │      │
                   │  ┌─────▼┐ ┌──▼───┐ ┌▼────┐ │
                   │  │Scribe│ │Safety│ │Ops  │ │
                   │  │Agent │ │Agent │ │Agent│ │
                   │  └──┬───┘ └──┬───┘ └──┬──┘ │
                   │     │        │        │     │
                   └─────┼────────┼────────┼─────┘
                         │        │        │
              ┌──────────▼──┐ ┌──▼──────┐ ┌▼──────────┐
              │  Clinical   │ │ChromaDB │ │In-Memory  │
              │  Notes DB   │ │Vector DB│ │Inventory  │
              │ (in-memory) │ │(RAG)    │ │Store      │
              └─────────────┘ └─────────┘ └───────────┘
```

### Agent Roles

| Agent | Role | Key Capability |
|-------|------|----------------|
| **Scribe Agent** | Clinical documentation | Transforms free-form dictation into structured JSON (diagnosis, treatment, dosage) using OpenAI structured outputs |
| **Clinical Safety Agent** | Drug interaction checking | Queries a ChromaDB vector store via RAG to detect conflicts between prescribed and existing medications |
| **Operations Agent** | Practice management | Manages inventory deductions, schedules follow-ups, and sends owner notifications |
| **Triage Agent** | Orchestrator | Routes incoming requests to the right specialist using OpenAI agent handoffs |

### Key Features

- **Voice note support**: Vets send WhatsApp voice notes → transcribed via Whisper API → processed by agents
- **Structured clinical notes**: Chaotic spoken language → perfect JSON schema (diagnosis, treatment, dosage)
- **RAG-powered drug safety**: ChromaDB vector database of veterinary drug interactions → semantic conflict detection
- **Multi-agent handoffs**: Seamless transfer between specialist agents via OpenAI Agents SDK native handoff mechanism
- **WhatsApp-native**: No app to install — works on the platform already on every vet's phone

### Technologies Used

| Component | Technology |
|-----------|-----------|
| Framework | Agent Kernel (OpenAI Agents SDK adapter) |
| Agent orchestration | OpenAI handoffs via `OpenAIModule` |
| Vector database | ChromaDB (via `ChromaManager` + `KnowledgeBuilder`) |
| Messaging | WhatsApp Cloud API (via Agent Kernel WhatsApp integration) |
| Speech-to-text | OpenAI Whisper API (custom handler) |
| Structured output | Pydantic `ClinicalNote` model → `AgentReplyAny` |
| Session management | Agent Kernel session store (in-memory / DynamoDB) |
| Deployment | AWS Lambda (serverless) |

---

## 3. Setup Instructions

### Prerequisites

- Python 3.12 or higher
- `uv` package manager ([install guide](https://github.com/astral-sh/uv))
- OpenAI API key (`OPENAI_API_KEY`)
- WhatsApp Business Account + Meta Developer Portal app (for WhatsApp mode)
- ngrok or pinggy (for WhatsApp webhook tunnel in local dev)

### Quick Start (Local CLI Mode — no WhatsApp needed)

```bash
# 1. Navigate to the vetra directory
cd use-cases/vetra

# 2. Run the build script
chmod +x build.sh
./build.sh

# 3. Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# 4. Run in CLI mode
uv run python demo.py --cli
```

You'll see a prompt. Try these example interactions in the CLI:

```
User: Just finished examining Charlie, a 5-year-old Golden Retriever. Diagnosed with atopic dermatitis. 
       Prescribing Apoquel 5.4mg twice daily for 14 days. Patient ID: CH-001.

User: Check if Apoquel has any interactions with Charlie's current medications.

User: Dispensed 28 tablets of Apoquel for Charlie. Also schedule a follow-up in 7 days to check progress.
```

### WhatsApp Setup (for full integration)

```bash
# 1. Set WhatsApp credentials
export AK_WHATSAPP__VERIFY_TOKEN="your_random_verify_token"
export AK_WHATSAPP__ACCESS_TOKEN="EAAR..."  # From Meta Developer Portal
export AK_WHATSAPP__PHONE_NUMBER_ID="123456789012345"

# 2. Start the server (auto-exposes via ngrok if installed)
uv run python demo.py

# 3. Configure webhook in Meta Developer Portal:
#    - Callback URL: https://your-ngrok-url/whatsapp/webhook
#    - Verify Token: your_random_verify_token
#    - Subscribe to: messages
```

### Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for LLM + Whisper |
| `AK_WHATSAPP__VERIFY_TOKEN` | For WhatsApp | Webhook verification token |
| `AK_WHATSAPP__ACCESS_TOKEN` | For WhatsApp | WhatsApp Cloud API access token |
| `AK_WHATSAPP__PHONE_NUMBER_ID` | For WhatsApp | WhatsApp Business phone number ID |
| `AK_WHATSAPP__APP_SECRET` | Optional | For HMAC webhook signature verification |
| `AK_SESSION__TYPE` | No | Session store type (`in_memory`, `dynamodb`) |

---

## 4. How to Run the Solution

### Option A: CLI Demo (recommended for testing)

```bash
cd use-cases/vetra
export OPENAI_API_KEY="sk-..."
uv run python demo.py --cli
```

The CLI demonstrates the full multi-agent flow:
1. **Scribe flow**: Describe a patient visit → structured note is saved
2. **Safety check**: Ask about drug interactions → ChromaDB RAG lookup
3. **Operations**: Dispense medication → inventory deducted + follow-up scheduled

### Option B: WhatsApp Server (full integration)

```bash
cd use-cases/vetra
export OPENAI_API_KEY="sk-..."
export AK_WHATSAPP__VERIFY_TOKEN="..."
export AK_WHATSAPP__ACCESS_TOKEN="..."
export AK_WHATSAPP__PHONE_NUMBER_ID="..."
uv run python demo.py
```

Send a WhatsApp message to your test number. Try:
- *"Charlie was just diagnosed with atopic dermatitis. Prescribe Apoquel 5.4mg twice daily."*
- *"Check if Apoquel interacts with Charlie's current medications."*
- Send a **voice note** describing a case → it gets transcribed and processed
- Send a **photo** of a skin condition → agents can reference it

### Option C: AWS Lambda (deployment)

```bash
cd use-cases/vetra/deploy
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your OpenAI key and WhatsApp credentials
chmod +x deploy.sh
./deploy.sh
```

---

## Scoring Summary for Judges

| Criterion | How Vetra Addresses It |
|-----------|----------------------|
| **Idea / Use Case Value (40%)** | Solves real veterinary pain points: documentation burden, drug safety risks, operational overhead. Aligned with SDG 3. Niche, creative, and practical. |
| **Agent Kernel Usage (30%)** | Uses WhatsApp integration, ChromaDB knowledge base (RAG), OpenAI framework adapter with handoffs, OpenAIModule/OpenAIRunner/OpenAIToolBuilder, ToolContext session memory, structured outputs via AgentReplyAny. Custom handler extends AgentWhatsAppRequestHandler. |
| **End Product (20%)** | Fully functional CLI + WhatsApp modes. Complete user flow: voice/text in → structured notes out with safety checks. Ready to demo. |
| **Documentation (10%)** | README with all 4 required points, AGENTS.md for agent guidance, SPEC.md for coding agents, demo video. |

---

## Project Structure

```
use-cases/vetra/
├── README.md          # This file
├── SPEC.md            # Machine-readable specification
├── AGENTS.md          # Agent-readable architecture guide
├── config.yaml        # Agent Kernel configuration
├── build.sh           # One-command setup
├── .gitignore
├── .python-version
├── pyproject.toml
├── knowledge.py       # ChromaDB drug interaction data
├── tool.py            # Agent tool functions
├── agent.py           # Agent definitions + ClinicalNote model
├── handler.py         # Custom WhatsApp handler (audio support)
├── demo.py            # CLI + Server entry point
├── lambda.py          # AWS Lambda handler
└── deploy/            # Deployment scripts
    ├── deploy.sh
    ├── Dockerfile
    └── terraform.tfvars.example
```
