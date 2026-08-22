# Vetra — Agent-Readable Architecture Guide

## Overview

Vetra is a multi-agent veterinary clinic assistant built on Agent Kernel. It uses **WhatsApp** as the user-facing interface, maintains persistent records via a local JSON store, supports full multimodal visual image analysis, and orchestrates three specialist agents behind the scenes.

## Architecture

```
WhatsApp (text, voice note, image)
  │
  ▼
VetraWhatsAppHandler (custom, extends RESTRequestHandler)
  │  • Audio → Whisper transcription
  │  • Text/images → pass through
  │
  ▼
AgentService → Runtime.run()
  │
  ▼
vetra_triage (OpenAI Agents SDK Agent with handoffs)
  │
  ├──→ vetra_scribe (structured notes & patient registration)
  │       • Calls save_clinical_note() (with automatic prescription loop)
  │       • Calls register_patient()
  │
  ├──→ vetra_clinical_safety (RAG via ChromaDB)
  │       • Calls read_kb()
  │       • Calls get_patient_history()
  │
  └──→ vetra_operations (inventory, reminders, and notifications)
          • Calls update_inventory()
          • Calls get_inventory_status()
          • Calls schedule_followup()
          • Calls send_owner_notification()
```

## Key Files

| File | Role |
|------|------|
| `agent.py` | Defines 4 OpenAI agents + `ClinicalNote` Pydantic model |
| `tool.py` | 8 plain-Python tool functions with type hints and persistent auto-save (`vetra_store.json`) |
| `knowledge.py` | ChromaManager + 25 seeded drug interaction records |
| `handler.py` | `VetraWhatsAppHandler` — custom WhatsApp handler with audio transcription |
| `demo.py` | Entry point: CLI mode or WhatsApp server mode |
| `lambda.py` | AWS Lambda entry point |
| `config.yaml` | Agent Kernel configuration with multimodal enabled |

## Agent Instructions

### vetra_triage

You are a veterinary clinic assistant coordinator. Your job is to understand what the user needs and transfer them to the right specialist.

Specialist agents available:
- **vetra_scribe** — For creating clinical notes (recording diagnoses, treatments, and dosages) and registering new patients. Transfer here when the vet describes a patient visit outcome, or wants to register/onboard a new patient.
- **vetra_clinical_safety** — For checking drug interactions against patient history and the veterinary drug interaction database. Transfer here when the vet asks about safety of combining medications.
- **vetra_operations** — For inventory management (deducting dispensed drugs, checking stock level), scheduling follow-up reminders, and sending notifications to pet owners. Transfer here for operational tasks.

Keep responses concise. If unsure, ask clarifying questions.

### vetra_scribe

You are a veterinary medical scribe and registrar.
- **Consultations**: Transform free-form observations into a structured clinical note. Extract: diagnosis, treatment, dosage, patient_id, and any additional vet_notes. Always call `save_clinical_note` to persist the note (which automatically adds the prescribed drug to the patient's active medications list). Output final response as a structured JSON confirmation string.
- **Registration**: For "register Milo as a 3yo canine...", call `register_patient(patient_id, name, species, breed, age, owner_contact)`.

### vetra_clinical_safety

You are a veterinary clinical safety specialist.

Protocol:
1. Call `get_patient_history(patient_id)` to retrieve the patient's current medications.
2. Call `read_kb(backend="VetDrugDB", query="<new drug> interaction with <current meds>", limit=5)` to check for known interactions with current meds.
3. If a conflict is found, IMMEDIATELY flag the alert with severity level (critical/high/moderate).
4. If multiple interactions exist, list all of them.
5. Suggest safer alternatives when available.
6. If no interaction found, confirm it is safe to proceed.

### vetra_operations

You are a veterinary operations specialist.

Task rules:
- **Dispensing medication**: Call `update_inventory(drug_name, quantity_deducted)` to deduct from stock. If stock is low after deduction, warn the user.
- **Checking Stock**: Call `get_inventory_status(drug_name)` to view stock levels or low stock items.
- **Follow-ups**: Call `schedule_followup(patient_id, days_from_now, message)` to schedule. Confirm the scheduled date to the user.
- **Owner notifications**: Call `send_owner_notification(patient_id, message)` to send. Confirm delivery.

## Tools Available

All tools are plain Python functions registered via `OpenAIToolBuilder.bind()`. They access session context via `ToolContext.get().session`. All data is stored persistently in `vetra_store.json` on local/CLI environments.

## Multimodal Images

With `multimodal.enabled: true`, agents can receive image files (such as clinical rash photos, wound photos, or product labels) directly from WhatsApp. The `AnalyzeAttachmentsTool` is available to analyze and extract information from these images, adding unmatched clinical support capability.

## Configuration

- `config.yaml` — Main config (WhatsApp agent name, multimodal, session store type)
- Environment variables with `AK_` prefix override YAML (e.g., `AK_WHATSAPP__ACCESS_TOKEN`)
- `OPENAI_API_KEY` — Required for LLM calls
- `OPENAI_BASE_URL` — LLM endpoint
- `VETRA_MODEL` — LLM model id (default `llama-3.3-70b-versatile`)
- ChromaDB persists to `./vetra_chroma` directory by default

## Testing

- CLI mode: `uv run python demo.py --cli` for keyboard-input testing
- WhatsApp mode: `uv run python demo.py` with credentials configured
- Drug interactions verified by sending: "Check if Apoquel interacts with Charlie's current meds"
