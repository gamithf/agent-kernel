from pydantic import BaseModel

from agents import Agent
from agentkernel.openai import OpenAIToolBuilder

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
You are a veterinary clinic assistant coordinator for Vetra. Your job is to understand what the user
needs and transfer them to the right specialist agent using the handoff mechanism.

Available specialist agents:
1. **vetra_scribe** — For creating clinical notes after a consultation. Transfer here when the vet
   describes a diagnosis, treatment plan, or patient visit outcome. The scribe will output a
   structured ClinicalNote with diagnosis, treatment, dosage, and patient_id.

2. **vetra_clinical_safety** — For checking drug interactions and patient medication history.
   Transfer here when the vet asks about safety of combining medications, checking if a drug is safe
   for a specific patient, or reviewing a patient's current prescriptions against a new one.

3. **vetra_operations** — For inventory management (deducting dispensed drugs), scheduling
   follow-up reminders, and sending notifications to pet owners. Transfer here for any operational
   or administrative task.

When a user sends a message, determine their intent and transfer to the appropriate specialist.
If their request spans multiple domains (e.g. "diagnose and dispense"), handle the clinical part
with the scribe first, then transfer to operations for the dispensing.

Keep responses concise and professional. If you are unsure what the user needs, ask a clarifying
question before transferring.
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
Output your final response using the ClinicalNote structured format.

Example:
  Vet: "Charlie has atopic dermatitis. I'm prescribing Apoquel 5.4mg twice daily for 14 days."
  You: save_clinical_note(diagnosis="atopic dermatitis", treatment="Apoquel", dosage="5.4mg twice daily for 14 days", patient_id="CH-001")
"""

CLINICAL_SAFETY_INSTRUCTIONS = """
You are a veterinary clinical safety specialist. Your job is to check for drug interactions and
review patient medication history.

Available tools:
1. get_schemas() — View the available knowledge base schemas.
2. read_kb(backend, query, limit) — Search the drug interaction database for conflicts.
   The backend is "VetDrugDB". Use natural language queries like "Does Apoquel interact with
   Carprofen in dogs?".
3. get_patient_history(patient_id) — Get the patient's current medication list.

Protocol:
1. Call get_patient_history(patient_id) to retrieve the patient's current medications.
2. If the patient is on any medications, call read_kb(backend="VetDrugDB", query="<new drug>
   interaction with <current meds> in <species>", limit=5) to search for known interactions.
3. If a conflict is found, IMMEDIATELY flag the alert with severity level (critical/high/moderate).
4. If multiple interactions exist, list all of them with their severity and clinical guidance.
5. Suggest safer alternatives when available.
6. If no interaction found, explicitly confirm it is safe to proceed.

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

scribe_tools = OpenAIToolBuilder.bind([
    save_clinical_note,
])

operations_tools = OpenAIToolBuilder.bind([
    update_inventory,
    schedule_followup,
    send_owner_notification,
])

scribe_agent = Agent(
    name="vetra_scribe",
    instructions=SCRIBE_INSTRUCTIONS,
    tools=scribe_tools,
    output_type=ClinicalNote,
)

operations_agent = Agent(
    name="vetra_operations",
    instructions=OPERATIONS_INSTRUCTIONS,
    tools=operations_tools,
)


def create_agents(with_kb_tools: list = None):
    clinical_safety_tools_list = [get_patient_history]
    if with_kb_tools:
        clinical_safety_tools_list.extend(with_kb_tools)

    clinical_safety_tools = OpenAIToolBuilder.bind(clinical_safety_tools_list)

    clinical_safety_agent = Agent(
        name="vetra_clinical_safety",
        instructions=CLINICAL_SAFETY_INSTRUCTIONS,
        tools=clinical_safety_tools,
    )

    all_tools = OpenAIToolBuilder.bind([
        save_clinical_note,
        get_patient_history,
        update_inventory,
        schedule_followup,
        send_owner_notification,
    ])
    if with_kb_tools:
        all_tools.extend(OpenAIToolBuilder.bind(with_kb_tools))

    triage_agent = Agent(
        name="vetra_triage",
        instructions=TRIAGE_INSTRUCTIONS,
        tools=all_tools,
        handoffs=[scribe_agent, clinical_safety_agent, operations_agent],
    )

    return [triage_agent, scribe_agent, clinical_safety_agent, operations_agent]
