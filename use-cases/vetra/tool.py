from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from agentkernel.core import ToolContext

CLINICAL_NOTES_STORE: dict[str, dict[str, Any]] = {}
INVENTORY_STORE: dict[str, int] = {
    "Apoquel": 120,
    "Carprofen": 200,
    "Meloxicam": 150,
    "Clavamox": 80,
    "Prednisone": 100,
    "Enalapril": 60,
    "Metronidazole": 90,
    "Gabapentin": 50,
    "Fluoxetine": 40,
    "Cyclosporine": 30,
}
PATIENT_MEDICATIONS: dict[str, list[dict[str, Any]]] = {
    "CH-001": [
        {"drug": "Carprofen", "dosage": "50mg once daily", "prescribed": "2026-06-15", "condition": "osteoarthritis"},
        {"drug": "Prednisone", "dosage": "0.5mg/kg once daily", "prescribed": "2026-07-20", "condition": "autoimmune dermatitis"},
    ],
    "CH-002": [
        {"drug": "Enalapril", "dosage": "0.5mg/kg twice daily", "prescribed": "2026-05-01", "condition": "heart murmur"},
        {"drug": "Furosemide", "dosage": "2mg/kg twice daily", "prescribed": "2026-05-01", "condition": "CHF"},
    ],
    "FE-001": [
        {"drug": "Methimazole", "dosage": "2.5mg twice daily", "prescribed": "2026-04-10", "condition": "hyperthyroidism"},
    ],
}
PATIENT_INFO: dict[str, dict[str, str]] = {
    "CH-001": {"name": "Charlie", "species": "Canine", "breed": "Golden Retriever", "age": "5 years", "owner": "+1234567890"},
    "CH-002": {"name": "Max", "species": "Canine", "breed": "Labrador", "age": "10 years", "owner": "+1234567891"},
    "FE-001": {"name": "Luna", "species": "Feline", "breed": "Domestic Shorthair", "age": "12 years", "owner": "+1234567892"},
}
FOLLOWUPS: list[dict[str, Any]] = []


def _get_session_patient_id() -> str | None:
    try:
        cache = ToolContext.get().session.get_non_volatile_cache()
        return cache.get("vetra.patient_id")
    except RuntimeError:
        return None


def _set_session_patient_id(patient_id: str) -> None:
    try:
        cache = ToolContext.get().session.get_non_volatile_cache()
        cache.set("vetra.patient_id", patient_id)
    except RuntimeError:
        pass


def save_clinical_note(
    diagnosis: str,
    treatment: str,
    dosage: str,
    patient_id: str,
    vet_notes: str = "",
) -> str:
    """Save a structured clinical note after a veterinary consultation.

    Args:
        diagnosis: The medical condition diagnosed.
        treatment: The treatment or medication prescribed.
        dosage: The dosage and administration instructions.
        patient_id: The patient identifier (e.g. CH-001).
        vet_notes: Any additional notes from the veterinarian.

    Returns:
        A confirmation message with the saved note summary.
    """
    note = {
        "diagnosis": diagnosis,
        "treatment": treatment,
        "dosage": dosage,
        "patient_id": patient_id,
        "vet_notes": vet_notes,
        "timestamp": datetime.now().isoformat(),
    }
    if patient_id not in CLINICAL_NOTES_STORE:
        CLINICAL_NOTES_STORE[patient_id] = []
    CLINICAL_NOTES_STORE[patient_id].append(note)

    _set_session_patient_id(patient_id)

    return json.dumps(
        {
            "status": "saved",
            "message": f"Clinical note saved for patient {patient_id}.",
            "patient_name": PATIENT_INFO.get(patient_id, {}).get("name", "Unknown"),
            "diagnosis": diagnosis,
            "treatment": treatment,
            "dosage": dosage,
        },
        indent=2,
    )


def get_patient_history(patient_id: str) -> str:
    """Retrieve a patient's current medication history and profile.

    Args:
        patient_id: The patient identifier (e.g. CH-001).

    Returns:
        JSON string with patient info and current medications.
    """
    _set_session_patient_id(patient_id)

    info = PATIENT_INFO.get(patient_id, {})
    meds = PATIENT_MEDICATIONS.get(patient_id, [])
    notes = CLINICAL_NOTES_STORE.get(patient_id, [])

    return json.dumps(
        {
            "patient_id": patient_id,
            "patient_info": info,
            "current_medications": meds,
            "visit_history_count": len(notes),
        },
        indent=2,
    )


def update_inventory(drug_name: str, quantity_deducted: int) -> str:
    """Deduct medication from the clinic inventory.

    Args:
        drug_name: Name of the medication to deduct.
        quantity_deducted: Number of tablets or units to deduct.

    Returns:
        JSON string with updated stock levels or low-stock warning.
    """
    current = INVENTORY_STORE.get(drug_name, 0)
    if quantity_deducted > current:
        return json.dumps(
            {
                "status": "error",
                "message": f"Insufficient stock. Only {current} units of {drug_name} available.",
                "drug": drug_name,
                "available": current,
                "requested": quantity_deducted,
            }
        )

    INVENTORY_STORE[drug_name] = current - quantity_deducted
    remaining = INVENTORY_STORE[drug_name]

    result = {
        "status": "success",
        "message": f"Deducted {quantity_deducted} units of {drug_name}. {remaining} units remaining.",
        "drug": drug_name,
        "deducted": quantity_deducted,
        "remaining": remaining,
    }

    if remaining < 20:
        result["warning"] = f"Low stock alert: Only {remaining} units of {drug_name} remaining. Please reorder soon."

    return json.dumps(result, indent=2)


def schedule_followup(patient_id: str, days_from_now: int, message: str) -> str:
    """Schedule a follow-up reminder for a patient.

    Args:
        patient_id: The patient identifier (e.g. CH-001).
        days_from_now: Number of days from now for the follow-up.
        message: The reminder message content.

    Returns:
        JSON string confirming the scheduled follow-up.
    """
    scheduled_date = (datetime.now() + timedelta(days=days_from_now)).strftime("%Y-%m-%d")
    patient_name = PATIENT_INFO.get(patient_id, {}).get("name", patient_id)

    followup = {
        "patient_id": patient_id,
        "patient_name": patient_name,
        "scheduled_date": scheduled_date,
        "days_from_now": days_from_now,
        "message": message,
        "created": datetime.now().isoformat(),
    }
    FOLLOWUPS.append(followup)

    return json.dumps(
        {
            "status": "scheduled",
            "message": f"Follow-up scheduled for {patient_name} on {scheduled_date}.",
            "patient_name": patient_name,
            "scheduled_date": scheduled_date,
            "reminder": message,
        },
        indent=2,
    )


def send_owner_notification(patient_id: str, message: str) -> str:
    """Send a notification message to the pet owner.

    Args:
        patient_id: The patient identifier (e.g. CH-001).
        message: The notification message content.

    Returns:
        JSON string confirming the notification was sent.
    """
    owner = PATIENT_INFO.get(patient_id, {}).get("owner", "Unknown")
    patient_name = PATIENT_INFO.get(patient_id, {}).get("name", patient_id)

    return json.dumps(
        {
            "status": "sent",
            "message": f"Notification sent to owner of {patient_name}.",
            "patient_name": patient_name,
            "owner_contact": owner,
            "notification": message,
        },
        indent=2,
    )
