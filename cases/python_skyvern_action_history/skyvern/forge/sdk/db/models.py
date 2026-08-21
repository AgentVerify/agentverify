class ActionModel(Base):
    __tablename__ = "actions"

    action_id = Column(String, primary_key=True, default=generate_action_id)
    action_type = Column(String, nullable=False)
    organization_id = Column(String, nullable=True)
    workflow_run_id = Column(String, nullable=True)
    task_id = Column(String, nullable=False, index=True)
    step_id = Column(String, nullable=False)
    step_order = Column(Integer, nullable=False)
    action_order = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    action_json = Column(JSON, nullable=True)
    screenshot_artifact_id = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
