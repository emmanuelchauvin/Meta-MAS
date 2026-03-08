import asyncio
from core.agent import BaseAgent

async def run_generation(agents: list[BaseAgent], task: str) -> dict[str, dict | None]:
    results = {}
    
    async def _safe_run(agent: BaseAgent):
        try:
            result = await agent.run(task)
            results[str(agent.dna.uid)] = result
        except Exception as e:
            print(f"[Sandbox] Agent {agent.dna.uid} a échoué : {e}")
            results[str(agent.dna.uid)] = None

    async with asyncio.TaskGroup() as tg:
        for agent in agents:
            tg.create_task(_safe_run(agent))

    return results
