async def run_task_v3(task, step, app, run_task_v3_agent_loop):
    v3_persisted_actions = []

    async def _on_action_round(round_actions):
        for name, args, succeeded in round_actions:
            try:
                action = Action(
                    action_type=name,
                    status=ActionStatus.completed if succeeded else ActionStatus.failed,
                    organization_id=task.organization_id,
                    workflow_run_id=task.workflow_run_id,
                    task_id=task.task_id,
                    step_id=step.step_id,
                    step_order=0,
                    action_order=len(v3_persisted_actions),
                    description=f"task_v3 {name} {args.get('selector', '')}".strip(),
                    screenshot_artifact_id=None,
                )
                v3_persisted_actions.append(action)
                await app.DATABASE.workflow_params.create_action(action=action)
            except Exception:
                LOG.warning("task_v3 failed to persist action row", exc_info=True)

    outcome = await run_task_v3_agent_loop(on_action_round=_on_action_round)
    return outcome
