import asyncio
import argparse
import logging

from agentkernel.core import AgentService
from agentkernel.openai import OpenAIModule

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("vetra")


def setup():
    from knowledge import create_vetra_knowledge_base
    from agent import create_agents

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
    print('    "Charlie has atopic dermatitis. Prescribe Apoquel 5.4mg. Patient ID: CH-001"')
    print('    "Check if Apoquel interacts with Charlie current medications"')
    print('    "Dispensed 28 Apoquel tablets. Schedule follow-up in 7 days"')
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
