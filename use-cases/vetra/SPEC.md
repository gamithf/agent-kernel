# Vetra — Veterinary Clinic AI Assistant Specification

## Agent Description

A multi-agent veterinary clinic assistant that uses WhatsApp as the user-facing interface. Vets and clinic staff send text messages, voice notes, and images to a WhatsApp number, and the Vetra system processes them through three specialist AI agents: Scribe (clinical note generation + patient registration), Clinical Safety (drug interaction checking via RAG on ChromaDB), and Operations (inventory management, reminders, and client notifications). Uses the OpenAI Agents SDK framework adapter, ChromaDB knowledge base, and the WhatsApp messaging integration.

## SDG Alignment

- **SDG 3** (Good Health and Well-being) — Target 3.8 (quality health services), Target 3.d (early warning for health risks)
- **SDG 12** (Responsible Consumption and Production) — Target 12.4 (environmentally sound management of pharmaceuticals and chemical wastes)

## Functional Requirements

### Agent Architecture

Build four OpenAI Agents SDK agents registered via a single `OpenAIModule`:

1. **`vetra_triage`** — Orchestrator agent that receives all incoming messages and hands off to the appropriate specialist agent using OpenAI handoffs. Instructions describe when to transfer to each specialist.

2. **`vetra_scribe`** — Generates structured clinical notes from free-form text or registers new patients. Calls `save_clinical_note` or `register_patient` tools. Returns confirmation as structured JSON text.

3. **`vetra_clinical_safety`** — Checks drug interactions by querying ChromaDB (via `read_kb` RAG tool) and retrieving patient history. Calls `get_patient_history` and `read_kb` tools. If a conflict is found, flags an alert with severity.

4. **`vetra_operations`** — Manages inventory and client communications. Calls `update_inventory`, `get_inventory_status`, `schedule_followup`, and `send_owner_notification` tools.

### Tools

Each tool is a plain Python function with type hints and docstrings, bound via `OpenAIToolBuilder.bind()`:

| Tool | Agent | Purpose |
|------|-------|---------|
| `save_clinical_note` | Scribe | Persist structured clinical note and automatically link to patient active medications |
| `register_patient` | Scribe | Register a new pet patient with detailed physical traits and owner contact |
| `read_kb` | Clinical Safety | Query ChromaDB vector store for drug interactions |
| `get_patient_history` | Clinical Safety | Retrieve patient's medical and medication history |
| `update_inventory` | Operations | Deduct medication from clinic stock |
| `get_inventory_status` | Operations | Check stock levels or list low stock items |
| `schedule_followup` | Operations | Schedule a follow-up reminder |
| `send_owner_notification` | Operations | Send a notification to the pet owner |

### Knowledge Base

- Use `ChromaManager` (ChromaDB) as a persistent vector store for veterinary drug interaction data.
- Seed ~25 drug interaction records covering common canine, feline, and equine medications.
- Store interaction text + metadata (severity, source).
- Clinical Safety agent queries via `read_kb` KnowledgeBuilder tool.

### WhatsApp Integration

- Custom `VetraWhatsAppHandler` extending `RESTRequestHandler`.
- Override message handling to support audio/voice note transcription via OpenAI Whisper API.
- Download audio from WhatsApp, transcribe, inject transcript as text message.
- Route all messages to `vetra_triage` agent.

### Session & Memory & Persistence

- Session keyed by WhatsApp phone number (`from_number`).
- Persistent local JSON store (`vetra_store.json`) for clinical notes, inventory, and patient details across runs.
- Use Agent Kernel's non-volatile session cache for patient context persistence across turns.
- In-memory session store for local development; DynamoDB for AWS Lambda deployment.
- Multimodal support enabled for direct visual image analysis (e.g. skin conditions, packaging).

## Local Development

- Provide a CLI entry point (`demo.py`) for testing without WhatsApp.
- CLI mode uses `AgentService` directly with typed prompts.
- WhatsApp mode uses `RESTAPI.run()` with the custom handler.
- Use `uv` for dependency management.
- Keep `.venv/` and generated lockfiles out of Git.

## Deployment

- Follow the waste-sorting-assistant deployment structure.
- Provide `lambda.py` for AWS Lambda deployment with DynamoDB session storage.
- Define deployment packaging commands in `deploy/deploy.sh`.
- Config driven by environment variables (`AK_` prefix) for secrets.

## File Structure

```
use-cases/vetra/
├── README.md             # Competition submission doc (4 required points)
├── SPEC.md               # This file — machine-readable spec
├── AGENTS.md             # Agent-readable architecture docs
├── config.yaml           # Agent Kernel YAML configuration
├── build.sh              # One-command setup script
├── .gitignore
├── .python-version
├── pyproject.toml        # Dependencies
├── knowledge.py          # ChromaManager + drug interaction seeding
├── tool.py               # All agent tool functions
├── agent.py              # 4 OpenAI Agents SDK agents + ClinicalNote model
├── handler.py            # VetraWhatsAppHandler (audio transcription)
├── demo.py               # CLI + WhatsApp server entry point
├── lambda.py             # AWS Lambda adapter
├── test-config.yaml      # Overrides for testing
└── deploy/
    ├── deploy.sh         # Deployment packaging script
    ├── Dockerfile        # Lambda container image
    └── terraform.tfvars.example
```
