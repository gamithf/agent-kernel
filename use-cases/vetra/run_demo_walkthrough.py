import asyncio
import os
import sys
import json
from datetime import datetime

# Load environment variables from .env if present
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k, _v = _k.strip(), _v.strip().strip("\"'")
                if _k not in os.environ:
                    os.environ[_k] = _v

from agentkernel.core import AgentService
from agentkernel.openai import OpenAIModule
from agent import create_agents
from knowledge import create_vetra_knowledge_base

def clear_existing_store():
    store_file = os.path.join(os.path.dirname(__file__), "vetra_store.json")
    if os.path.exists(store_file):
        try:
            os.remove(store_file)
            print("--- Cleaned up existing vetra_store.json to start a fresh demo...")
        except Exception:
            pass

async def run_step(service, step_num, title, user_input):
    print("\n" + "="*80)
    print(f"STEP {step_num}: {title}")
    print(f"Vet (Input): \"{user_input}\"")
    print("="*80)
    print("Vetra is thinking...", end="", flush=True)
    
    try:
        result = await service.run(user_input)
        print("\r" + " "*20 + "\r", end="") # Clear thinking message
        # Ensure we encode/decode safely to prevent Windows console charmap crash
        safe_response = str(result).encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
        print(f"Vetra (Response):\n{safe_response}")
    except Exception as e:
        print(f"\rError running step: {e}")

async def main():
    clear_existing_store()
    
    # Check if API Key is configured
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or "your_api_key_here" in api_key:
        print("\nWARNING: OPENAI_API_KEY is not set or is set to a placeholder.")
        print("Please configure your Gemini/OpenAI API Key in use-cases/vetra/.env before running this demo.\n")
        sys.exit(1)

    print("\nInitializing Vetra multi-agent workspace with Knowledge Base (ChromaDB RAG)...")
    from agents import set_default_openai_api
    set_default_openai_api("chat_completions")

    _, kb = create_vetra_knowledge_base()
    kb_tools = kb.build()
    agents = create_agents(with_kb_tools=kb_tools)
    OpenAIModule(agents)

    service = AgentService()
    service.select(session_id="vetra_demo_session", name="vetra_triage")

    print("\nReady! Starting the 5-Minute Competition Walkthrough...")

    # Step 1: Register a new patient (Scribe Agent)
    await run_step(
        service,
        1,
        "Register a New Patient (Scribe & Registrar Agent)",
        "Register a new patient named Buster, Canine, German Shepherd, age 3 years. Owner contact is +1987654321."
    )

    # Step 2: Save clinical consultation and prescribe Carprofen (Scribe Agent -> Auto-Prescription Loop)
    await run_step(
        service,
        2,
        "Scribe Consultation & Auto-Add Medication",
        "Finished examining Buster (CH-003). Diagnosed with osteoarthritis. Prescribing Carprofen 50mg once daily."
    )

    # Step 3: Clinical Safety Check (Clinical Safety Agent -> RAG Interaction Check)
    await run_step(
        service,
        3,
        "Drug-Interaction Safety Check (Clinical Safety Agent via ChromaDB RAG)",
        "Is it safe to prescribe Prednisone for Buster (CH-003)?"
    )

    # Step 4: Check current stock of Carprofen (Operations Agent)
    await run_step(
        service,
        4,
        "Inventory Check (Operations Agent)",
        "What is the current stock level of Carprofen?"
    )

    # Step 5: Dispense medication and schedule follow-up (Operations Agent)
    await run_step(
        service,
        5,
        "Deduct Stock & Schedule Follow-Up Reminder (Operations Agent)",
        "Deduct 14 units of Carprofen for Buster (CH-003). Also schedule a follow-up check in 14 days."
    )

    # Step 6: View Patient Schedule (Operations Agent -> New Schedule Tracker tool)
    await run_step(
        service,
        6,
        "Retrieve Patient Schedule & Follow-ups (Operations Agent)",
        "Give me the schedules of patient CH-003."
    )

    print("\n" + "="*80)
    print("DEMO SEQUENCE COMPLETED SUCCESSFULLY!")
    print("All records have been saved persistently in use-cases/vetra/vetra_store.json.")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
