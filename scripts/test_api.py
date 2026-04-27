# scripts/test_api.py
import httpx
import asyncio
import json

BASE_URL = "http://localhost:8000/api/v1"

async def test_health():
    """Тест health check"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print("Health check:", response.json())

async def test_years():
    """Тест получения годов"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/data/years")
        print("Available years:", response.json())

async def test_top_cities():
    """Тест топ городов"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/data/top-cities/2024?limit=5")
        print("Top 5 cities in 2024:")
        data = response.json()
        for city in data.get('cities', []):
            print(f"  - {city['name']}: {city['total_population']:,}")

async def test_llama_query():
    """Тест запроса к LLaMA"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/analysis/query",
            json={
                "prompt": "Какой процент населения России живет в городах?",
                "year": 2024,
                "temperature": 0.7
            }
        )
        print("LLaMA response:", response.json()['answer'][:500])

async def main():
    print("=" * 50)
    print("Testing Demography API")
    print("=" * 50)
    
    await test_health()
    print()
    
    await test_years()
    print()
    
    await test_top_cities()
    print()
    
    await test_llama_query()

if __name__ == "__main__":
    asyncio.run(main())