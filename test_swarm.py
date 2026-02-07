import asyncio
import json
from pathlib import Path
from swarm.orchestrator import run_swarm

async def main():
    # Load providers
    providers_path = Path("data/providers.json")
    with open(providers_path, "r") as f:
        providers = json.load(f)["providers"][:3] # Test with first 3

    # Mock Payload
    payload = {
        "service": "dentist",
        "time_window": {
            "date": "2026-02-08",
            "start": "13:00",
            "end": "17:00"
        },
        "preferences": {
            "time_weight": 0.6,
            "rating_weight": 0.2,
            "distance_weight": 0.2
        }
    }

    print("🚀 Starting Swarm Test...")
    print(f"🎯 Calling {len(providers)} providers...")
    
    # Run Swarm
    result = await run_swarm(payload, providers)

    print("\n✅ Swarm Finished!")
    print(f"🏆 Best Option: {result['best']['provider']['name']} (Score: {result['best']['score']})")
    print(f"📅 Slot: {result['best']['slot']}")
    
    print("\n📊 Full Rankings:")
    for rank, item in enumerate(result['ranked'], 1):
        print(f"{rank}. {item['provider']['name']} - Score: {item['score']} (Slot: {item['slot']})")
        print(f"   Details: {item['components']}")

if __name__ == "__main__":
    asyncio.run(main())
