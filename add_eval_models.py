import re

models_path = "backend/app/database/models.py"
with open(models_path, "r", encoding="utf-8") as f:
    content = f.read()

eval_models = """

class EvalDataset(Base):
    __tablename__ = "eval_datasets"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())

    examples: Mapped[list["EvalExample"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")
    runs: Mapped[list["EvalRun"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class EvalExample(Base):
    __tablename__ = "eval_examples"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("eval_datasets.id", ondelete="CASCADE"), index=True)
    
    input_prompt: Mapped[str] = mapped_column(Text)
    expected_tools: Mapped[list[str]] = mapped_column(_JSON_TYPE, default=list)
    expected_output_contains: Mapped[list[str]] = mapped_column(_JSON_TYPE, default=list)
    must_not_contain: Mapped[list[str]] = mapped_column(_JSON_TYPE, default=list)
    
    is_attack: Mapped[bool] = mapped_column(Boolean, default=False)
    attack_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    dataset: Mapped["EvalDataset"] = relationship(back_populates="examples")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("eval_datasets.id", ondelete="CASCADE"), index=True)
    
    model: Mapped[str] = mapped_column(String(100), index=True)
    provider: Mapped[str] = mapped_column(String(100), index=True)
    
    success_rate: Mapped[float] = mapped_column(sa.Float, default=0.0)
    avg_latency_ms: Mapped[float] = mapped_column(sa.Float, default=0.0)
    avg_tokens: Mapped[float] = mapped_column(sa.Float, default=0.0)
    avg_cost_usd: Mapped[float] = mapped_column(sa.Float, default=0.0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    
    completed_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    
    dataset: Mapped["EvalDataset"] = relationship(back_populates="runs")
    results: Mapped[list["EvalResult"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("eval_runs.id", ondelete="CASCADE"), index=True)
    example_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("eval_examples.id", ondelete="CASCADE"), index=True)
    
    actual_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools_used: Mapped[list[str]] = mapped_column(_JSON_TYPE, default=list)
    
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(sa.Float, default=0.0)

    run: Mapped["EvalRun"] = relationship(back_populates="results")

"""

if "EvalDataset" not in content:
    with open(models_path, "w", encoding="utf-8") as f:
        f.write(content + eval_models)
    print("Models added.")
else:
    print("Models already exist.")
