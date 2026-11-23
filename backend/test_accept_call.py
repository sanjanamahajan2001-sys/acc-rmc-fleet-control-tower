import asyncio, httpx

async def main():
    async with httpx.AsyncClient() as client:
        r = await client.post(
            'http://localhost:8010/fleet-api/v1/operational-intelligence/actions/ACT-RIP-3527/accept',
            json={
                "dispatcher_id": "USER-DISPATCHER-1",
                "dispatcher_role": "DISPATCHER",
                "idempotency_key": "EXEC-ACCEPT-TEST-123",
                "version_lock": 1,
                "notes": "Test accept"
            }
        )
        print("STATUS:", r.status_code)
        print("RESPONSE:", r.json())

if __name__ == "__main__":
    asyncio.run(main())
