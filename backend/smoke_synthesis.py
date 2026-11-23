import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.erp.models import Plant, Site
from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import RouteAnalysisMode
from app.modules.operational_dashboard.widgets.dispatch_analysis.services import (
    HistoricalRouteEvidenceService,
    GoogleRoutesProvider,
    RouteAnalysisSynthesisEngine,
)


async def main():
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Fetch real plants and sites from database
        plants = (await session.execute(select(Plant).limit(3))).scalars().all()
        sites = (await session.execute(select(Site).limit(1))).scalars().all()

        curr_plant = plants[0]
        alt_plant = plants[1]
        site = sites[0]

        # Use canonical coordinates (with authoritative plant/site coordinates for live test)
        curr_lat, curr_lon = (curr_plant.latitude or 15.3980), (curr_plant.longitude or 73.8120)
        alt_lat, alt_lon = (alt_plant.latitude or 15.2980), (alt_plant.longitude or 73.9880)
        site_lat, site_lon = (site.latitude or 15.504273), (site.longitude or 73.803005)

        print(f"Current Plant: {curr_plant.code} ({curr_lat}, {curr_lon})")
        print(f"Alt Plant: {alt_plant.code} ({alt_lat}, {alt_lon})")
        print(f"Site: {site.code} ({site_lat}, {site_lon})")

        # 2. Query WS-ROUT-1 Historical Operational Evidence from PostgreSQL
        print("\n--- 1. Querying Real Historical ERP Evidence ---")
        analysis_dt = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        hist_evidence = await HistoricalRouteEvidenceService.get_historical_transit_evidence(
            session=session,
            site_id=site.id,
            current_source_plant_id=curr_plant.id,
            candidate_plant_ids=[alt_plant.id],
            analysis_timestamp=analysis_dt,
            historical_window_days=90,
        )
        print(f"Historical Winner: {hist_evidence.overall_historical_winner}")
        print(f"Current Plant Trips: {hist_evidence.plant_metrics.get(str(curr_plant.id)).sample_count if hist_evidence.plant_metrics.get(str(curr_plant.id)) else 0}")
        print(f"Candidate Plant Trips: {hist_evidence.plant_metrics.get(str(alt_plant.id)).sample_count if hist_evidence.plant_metrics.get(str(alt_plant.id)) else 0}")

        # 3. Query WS-ROUT-2 Real Google Routes API v2
        print("\n--- 2. Querying Real Google Routes API v2 ---")
        provider = GoogleRoutesProvider()
        origins = [
            {"plant_id": str(curr_plant.id), "plant_code": curr_plant.code, "plant_name": curr_plant.name, "latitude": curr_lat, "longitude": curr_lon},
            {"plant_id": str(alt_plant.id), "plant_code": alt_plant.code, "plant_name": alt_plant.name, "latitude": alt_lat, "longitude": alt_lon},
        ]
        destination = {
            "site_id": str(site.id), "site_code": site.code, "site_name": site.name, "latitude": site_lat, "longitude": site_lon
        }
        google_evidence = await provider.get_route_evidence(
            origins=origins,
            destination=destination,
            mode=RouteAnalysisMode.NOW,
            fetch_detailed_for_plant_ids=[str(curr_plant.id), str(alt_plant.id)],
            force_refresh=True,
        )
        print(f"Google Provider Status: {google_evidence.status} (is_fresh={google_evidence.is_fresh})")
        for pid, it in google_evidence.matrix_items.items():
            print(f"  Plant {it.plant_code}: duration={it.duration_minutes}m, delay={it.traffic_delay_minutes}m, distance={it.distance_km}km")

        # 4. Synthesize 2D Decision using WS-ROUT-3
        print("\n--- 3. Executing WS-ROUT-3 2D Synthesis Recommendation Engine ---")
        analysis_id = str(uuid.uuid4())
        synthesis_result = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
            analysis_id=analysis_id,
            site_id=str(site.id),
            site_code=site.code,
            site_name=site.name,
            current_plant_id=str(curr_plant.id),
            current_plant_code=curr_plant.code,
            current_plant_name=curr_plant.name,
            candidate_plants=origins,
            historical_summary=hist_evidence,
            google_summary=google_evidence,
            detailed_route=google_evidence.detailed_routes.get(str(curr_plant.id)),
            mode=RouteAnalysisMode.NOW,
            analysis_timestamp=datetime.now(timezone.utc),
        )

        print("\n=======================================================")
        print("2D SYNTHESIS RESULT:")
        print(f"Outcome Status: {synthesis_result.recommendation_status.value}")
        print(f"Primary Category: {synthesis_result.primary_case_category.value}")
        print(f"Recommended Plant: {synthesis_result.recommended_plant_code}")
        print(f"Traffic Override: {synthesis_result.is_traffic_override}")
        print(f"Minutes Saved: {synthesis_result.minutes_saved}")
        print(f"Explanation: {synthesis_result.decision_reason_summary}")
        print(f"Engine/Policy: {synthesis_result.engine_version} / {synthesis_result.policy_version}")
        print("=======================================================\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
