import argparse
import asyncio
import logging
import os

# Load .env file into os.environ so OpenAI/Groq SDK picks it up
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

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("vetra")

logger.info(
    "LLM config -> base_url=%s model=%s key=%s...",
    os.environ.get("OPENAI_BASE_URL"),
    os.environ.get("VETRA_MODEL"),
    os.environ.get("OPENAI_API_KEY", "")[:6],
)


def setup():
    from agents import set_default_openai_api
    set_default_openai_api("chat_completions")

    from agent import create_agents
    from knowledge import create_vetra_knowledge_base

    _, kb = create_vetra_knowledge_base()
    kb_tools = kb.build()
    AGENTS = create_agents(with_kb_tools=kb_tools)

    OpenAIModule(AGENTS)
    return AGENTS


async def run_cli():
    setup()
    service = AgentService()
    service.select(session_id="vetra_cli_demo", name="vetra_triage")

    print("=" * 60)
    print("  Vetra -- Veterinary Clinic AI Assistant")
    print("  Type your message below (or 'quit' to exit)")
    print("=" * 60)
    print("  Examples:")
    print('    "Register a new patient named Buster, Canine, German Shepherd, age 3. Owner contact is +94771234567"')
    print('    "Buster has osteoarthritis. Prescribe Carprofen 50mg. ID: CH-003"')
    print('    "Check if it is safe to prescribe Prednisone for Buster (CH-003)"')
    print('    "Dispensed 14 Carprofen tablets. Schedule follow-up in 14 days"')
    print('    "Give me the schedules of patient CH-003"')
    print("=" * 60)

    while True:
        try:
            prompt = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not prompt:
            continue
        if prompt.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        print("Vetra: ", end="", flush=True)
        try:
            result = await service.run(prompt)
            print(result)
        except Exception as e:
            logger.exception("CLI error")
            print(f"Error: {e}")


def run_server():
    setup()

    from agentkernel.api.http import RESTAPI

    from handler import VetraWhatsAppHandler

    handler = VetraWhatsAppHandler()

    print("=" * 60)
    print("  Vetra -- WhatsApp Server")
    print("=" * 60)
    print("  Required env vars:")
    print("    AK_WHATSAPP__VERIFY_TOKEN")
    print("    AK_WHATSAPP__ACCESS_TOKEN")
    print("    AK_WHATSAPP__PHONE_NUMBER_ID")
    print("    OPENAI_API_KEY")
    print("=" * 60)
    print("  Webhook URL: https://<your-tunnel>/whatsapp/webhook")
    print("  Server:      http://localhost:8000")
    print("=" * 60)

    RESTAPI.run([handler])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vetra -- Veterinary Clinic AI Assistant")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    args = parser.parse_args()

    if args.cli:
        asyncio.run(run_cli())
    else:
        run_server()
