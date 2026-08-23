from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any

from agentkernel.core import ToolContext

CLINICAL_NOTES_STORE: dict[str, list[dict[str, Any]]] = {}
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

STORE_FILE = os.path.join(os.path.dirname(__file__), "vetra_store.json")


def _save_store_to_file() -> None:
    try:
        data = {
            "CLINICAL_NOTES_STORE": CLINICAL_NOTES_STORE,
            "INVENTORY_STORE": INVENTORY_STORE,
            "PATIENT_MEDICATIONS": PATIENT_MEDICATIONS,
            "PATIENT_INFO": PATIENT_INFO,
            "FOLLOWUPS": FOLLOWUPS,
        }
        with open(STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _load_store_from_file() -> None:
    global CLINICAL_NOTES_STORE, INVENTORY_STORE, PATIENT_MEDICATIONS, PATIENT_INFO, FOLLOWUPS
    try:
        if os.path.exists(STORE_FILE):
            with open(STORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "CLINICAL_NOTES_STORE" in data:
                CLINICAL_NOTES_STORE.clear()
                CLINICAL_NOTES_STORE.update(data["CLINICAL_NOTES_STORE"])
            if "INVENTORY_STORE" in data:
                INVENTORY_STORE.clear()
                INVENTORY_STORE.update(data["INVENTORY_STORE"])
            if "PATIENT_MEDICATIONS" in data:
                PATIENT_MEDICATIONS.clear()
                PATIENT_MEDICATIONS.update(data["PATIENT_MEDICATIONS"])
            if "PATIENT_INFO" in data:
                PATIENT_INFO.clear()
                PATIENT_INFO.update(data["PATIENT_INFO"])
            if "FOLLOWUPS" in data:
                FOLLOWUPS.clear()
                FOLLOWUPS.extend(data["FOLLOWUPS"])
    except Exception:
        pass


# Initial load from persistent file if it exists
_load_store_from_file()


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

    # Automatically add treatment to patient's active medications list to maintain continuity
    if patient_id not in PATIENT_MEDICATIONS:
        PATIENT_MEDICATIONS[patient_id] = []
    
    exists = False
    for med in PATIENT_MEDICATIONS[patient_id]:
        if med["drug"].lower() in treatment.lower() or treatment.lower() in med["drug"].lower():
            exists = True
            break
    if not exists and treatment:
        PATIENT_MEDICATIONS[patient_id].append({
            "drug": treatment,
            "dosage": dosage,
            "prescribed": datetime.now().strftime("%Y-%m-%d"),
            "condition": diagnosis
        })

    _save_store_to_file()

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
    # Normalize drug name to match case of seeded keys if possible
    normalized_name = drug_name
    for k in INVENTORY_STORE:
        if k.lower() == drug_name.lower():
            normalized_name = k
            break

    current = INVENTORY_STORE.get(normalized_name, 0)
    if quantity_deducted > current:
        return json.dumps(
            {
                "status": "error",
                "message": f"Insufficient stock. Only {current} units of {normalized_name} available.",
                "drug": normalized_name,
                "available": current,
                "requested": quantity_deducted,
            }
        )

    INVENTORY_STORE[normalized_name] = current - quantity_deducted
    remaining = INVENTORY_STORE[normalized_name]

    result = {
        "status": "success",
        "message": f"Deducted {quantity_deducted} units of {normalized_name}. {remaining} units remaining.",
        "drug": normalized_name,
        "deducted": quantity_deducted,
        "remaining": remaining,
    }

    if remaining < 20:
        result["warning"] = f"Low stock alert: Only {remaining} units of {normalized_name} remaining. Please reorder soon."

    _save_store_to_file()

    return json.dumps(result, indent=2)


def get_inventory_status(drug_name: str | None = None) -> str:
    """Retrieve current stock levels and inventory alerts.

    Args:
        drug_name: Optional name of specific medication to check. If omitted, returns low stock alerts and overall summary.

    Returns:
        JSON string with inventory details.
    """
    if drug_name:
        normalized_name = None
        for k in INVENTORY_STORE:
            if k.lower() == drug_name.lower():
                normalized_name = k
                break
        
        if normalized_name:
            qty = INVENTORY_STORE[normalized_name]
            return json.dumps(
                {
                    "status": "success",
                    "drug": normalized_name,
                    "stock": qty,
                    "status_label": "In Stock" if qty >= 20 else "Low Stock" if qty > 0 else "Out of Stock"
                },
                indent=2
            )
        else:
            return json.dumps(
                {
                    "status": "not_found",
                    "message": f"Medication '{drug_name}' not found in inventory.",
                    "available_inventory": list(INVENTORY_STORE.keys())
                },
                indent=2
            )

    low_stock = {k: v for k, v in INVENTORY_STORE.items() if v < 20}
    return json.dumps(
        {
            "status": "success",
            "total_inventory_items": len(INVENTORY_STORE),
            "low_stock_alerts": low_stock,
            "full_inventory": INVENTORY_STORE
        },
        indent=2
    )


def register_patient(
    name: str,
    species: str,
    breed: str,
    age: str,
    owner_contact: str,
    patient_id: str | None = None,
) -> str:
    """Register a new animal patient in the clinic records.

    Args:
        name: Name of the pet.
        species: Species of the animal (e.g. Canine, Feline, Equine).
        breed: Breed of the animal.
        age: Age of the animal (e.g. '3 years', '6 months').
        owner_contact: Phone number or contact of the pet owner.
        patient_id: Optional unique patient identifier (e.g. CH-003). If omitted, it will be automatically generated.

    Returns:
        JSON string confirming registration.
    """
    # Idempotency Check: Return existing patient if name and owner contact match exactly
    for existing_id, info in PATIENT_INFO.items():
        if info.get("name", "").lower() == name.lower() and info.get("owner", "") == owner_contact:
            _set_session_patient_id(existing_id)
            return json.dumps(
                {
                    "status": "already_registered",
                    "message": f"Patient '{name}' is already registered with ID {existing_id}.",
                    "patient": {
                        "name": info.get("name"),
                        "species": info.get("species"),
                        "breed": info.get("breed"),
                        "age": info.get("age"),
                        "owner": info.get("owner")
                    }
                },
                indent=2,
            )

    if not patient_id:
        prefix = "PT"
        species_lower = species.lower()
        if "canine" in species_lower or "dog" in species_lower or "pup" in species_lower:
            prefix = "CH"
        elif "feline" in species_lower or "cat" in species_lower or "kit" in species_lower:
            prefix = "FE"

        existing_nums = []
        for k in PATIENT_INFO.keys():
            if k.startswith(prefix + "-"):
                try:
                    num = int(k.split("-")[1])
                    existing_nums.append(num)
                except ValueError:
                    pass
        next_num = max(existing_nums) + 1 if existing_nums else 1
        patient_id = f"{prefix}-{next_num:03d}"

    PATIENT_INFO[patient_id] = {
        "name": name,
        "species": species,
        "breed": breed,
        "age": age,
        "owner": owner_contact,
    }
    if patient_id not in PATIENT_MEDICATIONS:
        PATIENT_MEDICATIONS[patient_id] = []
    if patient_id not in CLINICAL_NOTES_STORE:
        CLINICAL_NOTES_STORE[patient_id] = []

    _set_session_patient_id(patient_id)
    _save_store_to_file()

    return json.dumps(
        {
            "status": "registered",
            "message": f"Successfully registered new patient {name} with ID {patient_id}.",
            "patient": PATIENT_INFO[patient_id],
        },
        indent=2,
    )


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

    _save_store_to_file()

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

    _save_store_to_file()

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


def get_patient_schedule(patient_id: str | None = None) -> str:
    """Retrieve scheduled follow-up reminders for a patient or the entire clinic.

    Args:
        patient_id: Optional unique patient identifier (e.g. CH-001) to filter reminders. If omitted, returns all scheduled reminders.

    Returns:
        JSON string listing the follow-ups.
    """
    if patient_id:
        matches = [f for f in FOLLOWUPS if f["patient_id"].lower() == patient_id.lower()]
        return json.dumps(
            {
                "status": "success",
                "patient_id": patient_id,
                "patient_name": PATIENT_INFO.get(patient_id, {}).get("name", "Unknown"),
                "scheduled_followups": matches,
            },
            indent=2,
        )

    return json.dumps(
        {
            "status": "success",
            "total_scheduled_followups": len(FOLLOWUPS),
            "all_followups": FOLLOWUPS,
        },
        indent=2,
    )
