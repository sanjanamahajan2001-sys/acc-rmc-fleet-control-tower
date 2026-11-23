import asyncio, traceback
from app.core.database import AsyncSessionFactory
from sqlalchemy import select
from app.modules.operational_intelligence.models.planner_action import PlannerActionLog
from app.modules.operational_intelligence.services.action_execution_service import ActionExecutionService
from app.modules.operational_intelligence.schemas.action_execution_dtos import DispatcherRoleEnum

async def test():
    async with AsyncSessionFactory() as session:
        try:
            res_actions = await session.execute(select(PlannerActionLog).limit(10))
            actions = res_actions.scalars().all()
            for action in actions:
                try:
                    res = await ActionExecutionService.accept_recommendation(
                        session=session,
                        action_id=action.action_id,
                        dispatcher_id='USER-1',
                        role=DispatcherRoleEnum.DISPATCHER,
                        idempotency_key=f'KEY-ACCEPT-{action.action_id}',
                        version_lock=action.version_lock,
                        notes='Operational intent approved by dispatcher'
                    )
                    print(f"✅ ACCEPT SUCCESS for action {action.action_id} (Status: {res.action.action_status})")
                    break
                except Exception as ex:
                    print(f"Skipping {action.action_id}: {ex}")
        except Exception as e:
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
