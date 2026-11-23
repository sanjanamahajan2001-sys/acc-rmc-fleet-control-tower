import asyncio
import os
import sys

sys.path.append('.')

from app.core.database import AsyncSessionFactory
from sqlalchemy import select
from app.modules.erp.models import Plant, Site, Dispatch

async def check():
    async with AsyncSessionFactory() as session:
        plants = (await session.execute(select(Plant))).scalars().all()
        sites = (await session.execute(select(Site))).scalars().all()
        dispatches = (await session.execute(select(Dispatch).limit(5))).scalars().all()
        
        print("=== PLANTS ===")
        for p in plants:
            lat = getattr(p, 'latitude', None)
            lon = getattr(p, 'longitude', None)
            print(f"Plant ID: {p.id} | Code: {getattr(p, 'code', None)} | Name: {p.name} | Lat: {lat}, Lon: {lon}")
            
        print("\n=== SITES ===")
        for s in sites[:10]:
            lat = getattr(s, 'latitude', None)
            lon = getattr(s, 'longitude', None)
            print(f"Site ID: {s.id} | Name: {s.name} | PlantID: {s.plant_id} | CustID: {getattr(s, 'customer_id', None)} | Lat: {lat}, Lon: {lon}")

if __name__ == "__main__":
    asyncio.run(check())
