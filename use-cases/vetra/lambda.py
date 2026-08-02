from agentkernel.aws import Lambda
from agentkernel.openai import OpenAIModule

from agent import create_agents
from knowledge import create_vetra_knowledge_base

_, kb = create_vetra_knowledge_base()
kb_tools = kb.build()
AGENTS = create_agents(with_kb_tools=kb_tools)

OpenAIModule(AGENTS)

handler = Lambda.handler
