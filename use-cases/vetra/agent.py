import os

from agentkernel.openai import OpenAIToolBuilder
from agents import Agent
from pydantic import BaseModel

MODEL = os.environ.get("VETRA_MODEL", "llama-3.3-70b-versatile")

from tool import (
    get_patient_history,
    save_clinical_note,
    schedule_followup,
    send_owner_notification,
    update_inventory,
)


class ClinicalNote(BaseModel):
    diagnosis: str
    treatment: str
    dosage: str
    patient_id: str
    vet_notes: str = ""


TRIAGE_INSTRUCTIONS = """
You are a veterinary clinic assistant coordinator for Vetra. Your only job is to route the user to
the correct specialist agent using the handoff mechanism, then stop. You do NOT answer the question
yourself and you do NOT perform the task.

Choose EXACTLY ONE specialist based on these STRICT keyword rules, in this priority order:

1. ROUTE TO vetra_operations IF the message contains ANY of these words/phrases:
   "dispensed", "dispensing", "inventory", "stock", "schedule a follow-up",
   "schedule follow-up", "schedule a followup", "remaining in stock", "units remain",
   "notify the owner", "send notification". Example: "Dispensed 28 Apoquel tablets. Schedule a
   follow-up in 7 days" -> operations. Operational tasks include deducing inventory and reminders.

2. ROUTE TO vetra_clinical_safety IF the message contains ANY of these words/phrases:
   "interact", "interaction", "is it safe", "safe to", "check", "contraindication",
   "current medications", "medication history". Example: "Check if Apoquel interacts with
   Charlie's current medications" -> clinical_safety.

3. ROUTE TO vetra_scribe IF the message describes a diagnosis, treatment, prescription, dosage, or
   patient visit outcome. Example: "Charlie has atopic dermatitis. Prescribe Apoquel 5.4mg.
   Patient ID: CH-001" -> scribe.

4. If the message spans MULTIPLE domains, route to the FIRST matching domain in this order:
   scribe (clinical diagnosis) BEFORE operations (dispensing) BEFORE clinical_safety.

5. If none of the above clearly matches, ask the user a clarifying question instead of guessing.

Transfer to exactly one specialist and do not add extra commentary.
"""

SCRIBE_INSTRUCTIONS = """
You are a veterinary medical scribe. Your job is to transform the vet's observations into a
structured clinical note.

Extract the following from the conversation:
- diagnosis: The medical condition diagnosed
- treatment: The treatment or medication prescribed
- dosage: The dosage and administration instructions
- patient_id: The patient identifier (e.g. CH-001)
- vet_notes: Any additional notes from the veterinarian

ALWAYS call save_clinical_note after extracting the information to persist it.
Then reply to the user with a concise confirmation in this JSON format:
{"status": "saved", "diagnosis": "...", "treatment": "...", "dosage": "...", "patient_id": "..."}

Example:
  Vet: "Charlie has atopic dermatitis. I'm prescribing Apoquel 5.4mg twice daily for 14 days."
  You: save_clinical_note(diagnosis="atopic dermatitis", treatment="Apoquel", dosage="5.4mg twice daily for 14 days", patient_id="CH-001")
  Then reply: {"status": "saved", "diagnosis": "atopic dermatitis", "treatment": "Apoquel", "dosage": "5.4mg twice daily for 14 days", "patient_id": "CH-001"}
"""

CLINICAL_SAFETY_INSTRUCTIONS = """
You are a veterinary clinical safety specialist. Your job is to check for drug interactions and
review patient medication history.

Available tools:
1. get_patient_history(patient_id) — Get the patient's current medication list.
2. read_kb(backend, query, limit) — Search the drug interaction database for conflicts.
   Use backend="VetDrugDB". Use natural language queries like "Does Apoquel interact with
   Carprofen in dogs?".

Protocol — you MUST call these tools in order. Do NOT answer from memory:
1. ALWAYS call get_patient_history(patient_id) FIRST to retrieve the patient's current medications.
   This is mandatory before drawing any conclusion.
2. ALWAYS call read_kb(backend="VetDrugDB", query="<new drug> interaction with <current meds> in
   <species>", limit=5) to search for known interactions with EVERY current medication.
3. If a conflict is found, IMMEDIATELY flag the alert with severity level (critical/high/moderate).
4. If multiple interactions exist, list all of them with their severity and clinical guidance.
5. Suggest safer alternatives when available.
6. If no interaction found, explicitly confirm it is safe to proceed.

If you have not called get_patient_history, call it now before answering. Base your answer ONLY on the
actual tool results, never on your own knowledge of the drugs.
Always include the patient's name in your response for clarity.
"""

OPERATIONS_INSTRUCTIONS = """
You are a veterinary operations specialist. Your job is to manage inventory and client communications.

Task rules:
- For dispensing medication: Call update_inventory(drug_name, quantity_deducted) to deduct from
  stock. If stock is low after deduction, warn the user.
- For follow-ups: Call schedule_followup(patient_id, days_from_now, message) to schedule. Confirm
  the scheduled date to the user.
- For owner notifications: Call send_owner_notification(patient_id, message). Confirm delivery.
- For checking stock: Call update_inventory with quantity_deducted=0 to get current levels.

Be concise and professional. Confirm each action after it completes.
"""

scribe_tools = OpenAIToolBuilder.bind(
    [
        save_clinical_note,
    ]
)

operations_tools = OpenAIToolBuilder.bind(
    [
        update_inventory,
        schedule_followup,
        send_owner_notification,
    ]
)

scribe_agent = Agent(
    name="vetra_scribe",
    model=MODEL,
    instructions=SCRIBE_INSTRUCTIONS,
    tools=scribe_tools,
)

operations_agent = Agent(
    name="vetra_operations",
    model=MODEL,
    instructions=OPERATIONS_INSTRUCTIONS,
    tools=operations_tools,
)


def create_agents(with_kb_tools: list = None):
    # Clinical safety only gets get_patient_history + read_kb (2 tools) so the
    # model can reliably call them. Passing all 4 KB tools overwhelms smaller models.
    clinical_safety_tools_list = [get_patient_history]
    if with_kb_tools:
        for _f in with_kb_tools:
            if getattr(_f, "__name__", "") == "read_kb":
                clinical_safety_tools_list.append(_f)
                break

    clinical_safety_tools = OpenAIToolBuilder.bind(clinical_safety_tools_list)

    clinical_safety_agent = Agent(
        name="vetra_clinical_safety",
        model=MODEL,
        instructions=CLINICAL_SAFETY_INSTRUCTIONS,
        tools=clinical_safety_tools,
    )

    triage_agent = Agent(
        name="vetra_triage",
        model=MODEL,
        instructions=TRIAGE_INSTRUCTIONS,
        handoffs=[scribe_agent, clinical_safety_agent, operations_agent],
    )

    return [triage_agent, scribe_agent, clinical_safety_agent, operations_agent]
