import asyncio
import uuid
import dataclasses
from models.dna import AgentDNA
from services.llm_client import LLMService

async def main():
    print("--- Test 1: AgentDNA Immutability (FrozenInstanceError) ---")
    dna = AgentDNA(
        uid=uuid.uuid4(),
        generation=1,
        role_prompt="Initial Prompt",
        temperature=0.7
    )
    print(f"Created DNA with uid={dna.uid}, role_prompt='{dna.role_prompt}'")
    
    try:
        dna.role_prompt = "Hacked Prompt"
        print("FAIL: Managed to mutate DNA!")
    except dataclasses.FrozenInstanceError as e:
        print(f"PASS: Caught Expected FrozenInstanceError -> {e}")
    except Exception as e:
        print(f"FAIL: Caught wrong exception type: {type(e)} - {e}")
        
    print("\n--- Test 2: LLMService Isolation (Dependency Injection) ---")
    # Instancie deux services avec des clés différentes, et des base_url distinctes par acquis de conscience
    service1 = LLMService(api_key="key_1111", base_url="https://api.mock1.com/v1")
    service2 = LLMService(api_key="key_2222", base_url="https://api.mock2.com/v1")
    
    print(f"Service 1 API Key : {service1.client.api_key}")
    print(f"Service 1 Base URL: {service1.client.base_url}")
    print(f"Service 2 API Key : {service2.client.api_key}")
    print(f"Service 2 Base URL: {service2.client.base_url}")
    
    if service1.client.api_key != service2.client.api_key and service1.client.base_url != service2.client.base_url:
        print("PASS: Both LLMServices have isolated dependencies!")
    else:
        print("FAIL: Dependencies are not isolated!")

if __name__ == "__main__":
    asyncio.run(main())
