class WorkflowParametersRepository:
    @db_operation("create_action")
    async def create_action(self, action: Action):
        async with self.Session() as session:
            raw_action_payload = action.model_dump()
            new_action = ActionModel(
                action_type=action.action_type,
                organization_id=action.organization_id,
                workflow_run_id=action.workflow_run_id,
                task_id=action.task_id,
                step_id=action.step_id,
                status=action.status,
                action_json=raw_action_payload,
            )
            session.add(new_action)
            await session.commit()
            await session.refresh(new_action)
            return hydrate_action(new_action)
