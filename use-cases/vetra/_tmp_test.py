import os, asyncio
os.environ.setdefault('OPENAI_API_KEY', 'your_api_key_here')
os.environ.setdefault('OPENAI_BASE_URL', 'https://api.groq.com/openai/v1')
os.environ.setdefault('VETRA_MODEL', 'llama-3.3-70b-versatile')
from agents import Runner
from knowledge import create_vetra_knowledge_base
from agent import create_agents


async def main():
    _, kb = create_vetra_knowledge_base()
    kb_tools = kb.build()
    triage, _, _, _ = create_agents(with_kb_tools=kb_tools)
    r = await Runner.run(triage, 'Check if Apoquel interacts with Charlie current medications')
    print('OUT:', str(r.final_output)[:400])


asyncio.run(main())
