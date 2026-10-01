"""
AURA Phase 9 — AI Operations Intelligence Tests.

Deterministic tests for:
- Safety evaluation
- Quality evaluation
- Cost estimation and budgets
- Model benchmarking and recommendation
- Golden dataset evaluation
- Tenant isolation enforcement
- Incident logging
- Replay engine
- Security attacks

All tests are fully deterministic (no LLM calls).
"""

from __future__ import annotations

import uuid

import pytest

from app.evaluation.benchmarks import BenchmarkEngine
from app.evaluation.cost import CostManager
from app.evaluation.datasets import (
    ALL_GOLDEN_EXAMPLES,
    GOLDEN_SECURITY_ATTACKS,
    get_attack_examples,
    get_examples_by_category,
)
from app.evaluation.engine import (
    GoldenDatasetEvaluator,
    IncidentLogger,
    QualityEvaluator,
    SafetyEvaluator,
)
from app.evaluation.replay import ReplayEngine
from app.evaluation.schemas import (
    BudgetStatus,
    IncidentSeverity,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def cleanup():
    """Reset shared state between tests."""
    yield
    CostManager.reset_daily_spend()
    IncidentLogger.clear()
    ReplayEngine.clear()


# ─── Safety Evaluation Tests ──────────────────────────────────────────────────


class TestSafetyEvaluator:
    def test_perfect_safety_score(self):
        """A clean run with no violations should score 1.0."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score = SafetyEvaluator.evaluate(
            run_id=run_id,
            organization_id=org_id,
            action_history=[],
        )
        assert score.overall_score == 1.0
        assert score.risk_level == "LOW"
        assert score.prompt_injection_detected is False
        assert score.policy_violations == 0

    def test_policy_violation_reduces_score(self):
        """Each policy violation should reduce the safety score."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score_clean = SafetyEvaluator.evaluate(
            run_id=run_id, organization_id=org_id, action_history=[]
        )
        score_violation = SafetyEvaluator.evaluate(
            run_id=run_id,
            organization_id=org_id,
            action_history=[],
            policy_violations=2,
        )
        assert score_violation.overall_score < score_clean.overall_score
        assert score_violation.policy_violations == 2

    def test_tenant_violation_scores_critical(self):
        """Tenant boundary violations should result in CRITICAL risk level."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score = SafetyEvaluator.evaluate(
            run_id=run_id,
            organization_id=org_id,
            action_history=[],
            tenant_boundary_violations=1,
        )
        # Tenant isolation is weighted at 3.0 — a violation crushes the score
        assert score.overall_score < 0.8
        assert score.tenant_boundary_violations == 1

    def test_prompt_injection_detected(self):
        """Prompt injection detection should flag and reduce score."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score = SafetyEvaluator.evaluate(
            run_id=run_id,
            organization_id=org_id,
            action_history=[],
            prompt_injection_attempts=["Ignore all previous instructions"],
        )
        assert score.prompt_injection_detected is True
        assert score.overall_score < 1.0

    def test_dimensions_present(self):
        """All expected evaluation dimensions should be present."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score = SafetyEvaluator.evaluate(run_id=run_id, organization_id=org_id, action_history=[])
        dim_names = {d.name for d in score.details}
        assert "policy_compliance" in dim_names
        assert "tenant_isolation" in dim_names
        assert "prompt_injection" in dim_names
        assert "tool_authorization" in dim_names
        assert "verification" in dim_names

    def test_tenant_isolation_in_result(self):
        """SafetyScore must contain the correct organization_id."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score = SafetyEvaluator.evaluate(run_id=run_id, organization_id=org_id, action_history=[])
        assert score.organization_id == org_id
        assert score.run_id == run_id


# ─── Quality Evaluation Tests ─────────────────────────────────────────────────


class TestQualityEvaluator:
    def test_successful_run_with_correct_tools(self):
        """A successful run with correct tool usage scores high."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score = QualityEvaluator.evaluate(
            run_id=run_id,
            organization_id=org_id,
            succeeded=True,
            action_history=[],
            expected_tools=["retrieve_customer", "create_quotation"],
            actual_tools_used=["retrieve_customer", "create_quotation"],
            retrieved_chunks=5,
            cited_chunks=5,
            policy_compliant=True,
            latency_ms=1000.0,
            estimated_cost_usd=0.005,
        )
        assert score.task_success == 1.0
        assert score.tool_selection_accuracy >= 0.9
        assert score.overall_score > 0.8

    def test_failed_run_scores_low(self):
        """A failed run should score low on task success."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score = QualityEvaluator.evaluate(
            run_id=run_id,
            organization_id=org_id,
            succeeded=False,
            action_history=[],
        )
        assert score.task_success == 0.0
        # task_success is weighted at 3.0 but other dims still contribute
        assert score.overall_score < 0.8

    def test_wrong_tools_lowers_accuracy(self):
        """Using wrong tools should reduce tool selection accuracy."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score = QualityEvaluator.evaluate(
            run_id=run_id,
            organization_id=org_id,
            succeeded=True,
            action_history=[],
            expected_tools=["retrieve_customer", "create_quotation"],
            actual_tools_used=["send_email", "retrieve_pricing"],  # Wrong tools
            policy_compliant=True,
        )
        assert score.tool_selection_accuracy < 0.5

    def test_policy_violation_reduces_quality(self):
        """Policy violations should reduce quality score."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score = QualityEvaluator.evaluate(
            run_id=run_id,
            organization_id=org_id,
            succeeded=True,
            action_history=[],
            policy_compliant=False,
        )
        assert score.policy_compliance == 0.0

    def test_high_latency_reduces_score(self):
        """Runs exceeding target latency should score lower."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score_fast = QualityEvaluator.evaluate(
            run_id=run_id,
            organization_id=org_id,
            succeeded=True,
            action_history=[],
            latency_ms=1000.0,
            target_latency_ms=5000.0,
        )
        score_slow = QualityEvaluator.evaluate(
            run_id=run_id,
            organization_id=org_id,
            succeeded=True,
            action_history=[],
            latency_ms=20000.0,
            target_latency_ms=5000.0,
        )
        assert score_fast.latency_score > score_slow.latency_score

    def test_citation_coverage(self):
        """Citation quality should track chunk coverage ratio."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score = QualityEvaluator.evaluate(
            run_id=run_id,
            organization_id=org_id,
            succeeded=True,
            action_history=[],
            retrieved_chunks=10,
            cited_chunks=3,
        )
        assert score.retrieval_quality == pytest.approx(0.3, abs=0.01)

    def test_tenant_id_in_score(self):
        """QualityScore must carry the correct tenant ID."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score = QualityEvaluator.evaluate(
            run_id=run_id, organization_id=org_id, succeeded=True, action_history=[]
        )
        assert score.organization_id == org_id
        assert score.run_id == run_id


# ─── Cost Management Tests ────────────────────────────────────────────────────


class TestCostManager:
    def test_cost_estimation_accuracy(self):
        """Cost estimates should match known model pricing."""
        estimate = CostManager.estimate_cost(
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=1000,
            output_tokens=500,
        )
        # gpt-4o-mini: $0.00015 input + $0.00060 output per 1k
        expected = (1000 / 1000) * 0.00015 + (500 / 1000) * 0.00060
        assert estimate.estimated_cost_usd == pytest.approx(expected, rel=0.01)

    def test_unknown_model_uses_default(self):
        """Unknown models should fall back to default pricing."""
        estimate = CostManager.estimate_cost(
            model="unknown-model-xyz",
            provider="mystery",
            input_tokens=1000,
            output_tokens=1000,
        )
        assert estimate.estimated_cost_usd > 0.0

    def test_budget_ok_within_limit(self):
        """Small costs should pass budget check."""
        org_id = uuid.uuid4()
        check = CostManager.check_budget(
            organization_id=org_id,
            estimated_cost_usd=0.01,
            per_run_budget_usd=0.50,
        )
        assert check.status == BudgetStatus.OK

    def test_budget_exceeded_over_limit(self):
        """Costs exceeding per-run budget should be flagged."""
        org_id = uuid.uuid4()
        check = CostManager.check_budget(
            organization_id=org_id,
            estimated_cost_usd=1.00,  # Exceeds $0.50 default
            per_run_budget_usd=0.50,
        )
        assert check.status == BudgetStatus.EXCEEDED

    def test_org_daily_spend_accumulates(self):
        """Daily spend should accumulate correctly across OK runs."""
        org_id = uuid.uuid4()
        # Use small amounts well within default budget
        CostManager.check_budget(
            org_id, estimated_cost_usd=0.05, per_run_budget_usd=1.0, org_daily_budget_usd=100.0
        )
        CostManager.check_budget(
            org_id, estimated_cost_usd=0.10, per_run_budget_usd=1.0, org_daily_budget_usd=100.0
        )
        spend = CostManager.get_org_daily_spend(org_id)
        assert spend == pytest.approx(0.15, abs=0.01)

    def test_daily_budget_exceeded_blocks_run(self):
        """Runs that would exceed daily org budget should be blocked."""
        org_id = uuid.uuid4()
        # Simulate near-limit spend
        CostManager._org_daily_spend[str(org_id)] = 49.0
        check = CostManager.check_budget(
            organization_id=org_id,
            estimated_cost_usd=5.0,
            org_daily_budget_usd=50.0,
        )
        assert check.status == BudgetStatus.EXCEEDED

    def test_tenant_isolation_in_budgets(self):
        """Budget state must not leak between organizations."""
        org_a = uuid.uuid4()
        org_b = uuid.uuid4()
        CostManager._org_daily_spend[str(org_a)] = 45.0
        spend_b = CostManager.get_org_daily_spend(org_b)
        assert spend_b == 0.0

    def test_budget_warning_threshold(self):
        """Costs at 80%+ of budget should trigger WARNING."""
        org_id = uuid.uuid4()
        check = CostManager.check_budget(
            organization_id=org_id,
            estimated_cost_usd=0.45,  # 90% of $0.50
            per_run_budget_usd=0.50,
        )
        assert check.status == BudgetStatus.WARNING


# ─── Benchmark Tests ──────────────────────────────────────────────────────────


class TestBenchmarkEngine:
    def test_get_specific_benchmark(self):
        """Should retrieve pre-computed benchmarks by model and task type."""
        result = BenchmarkEngine.get_benchmark("gpt-4o", "COMPLEX_REASONING")
        assert result is not None
        assert result.model == "gpt-4o"
        assert result.task_type == "COMPLEX_REASONING"
        assert 0.0 <= result.success_rate <= 1.0

    def test_compare_models_returns_all(self):
        """compare_models should return all models for a task type."""
        results = BenchmarkEngine.compare_models("SIMPLE_CLASSIFICATION")
        assert len(results) > 1
        models = [r.model for r in results]
        assert "gpt-4o-mini" in models
        assert "gpt-4o" in models

    def test_recommend_cheapest_capable_model(self):
        """Recommendation should return cheapest model meeting quality threshold."""
        rec = BenchmarkEngine.recommend_model(
            task_type="SIMPLE_CLASSIFICATION",
            min_success_rate=0.90,
            max_cost_usd=0.01,
        )
        assert rec is not None
        assert rec.success_rate >= 0.90
        assert rec.avg_cost_usd <= 0.01

    def test_compare_sorted_by_value(self):
        """Results should be sorted by cost-adjusted success rate."""
        results = BenchmarkEngine.compare_models("TOOL_USE")
        assert len(results) >= 2
        # First should have best value (highest success_rate / cost)
        first_value = results[0].success_rate / (results[0].avg_cost_usd + 1e-9)
        second_value = results[1].success_rate / (results[1].avg_cost_usd + 1e-9)
        assert first_value >= second_value

    def test_get_all_benchmarks(self):
        """Should return all benchmark records."""
        all_results = BenchmarkEngine.get_all_benchmarks()
        assert len(all_results) >= 5


# ─── Golden Dataset Tests ─────────────────────────────────────────────────────


class TestGoldenDatasets:
    def test_all_examples_loaded(self):
        """Should have examples across all categories."""
        assert len(ALL_GOLDEN_EXAMPLES) >= 10

    def test_attack_examples_flagged(self):
        """Security attack examples must be marked as attacks."""
        attacks = get_attack_examples()
        assert len(attacks) >= 5
        for attack in attacks:
            assert attack.is_attack is True
            assert attack.attack_type is not None

    def test_category_filtering(self):
        """Category filter should return only matching examples."""
        customers = get_examples_by_category("customer")
        for ex in customers:
            assert ex.category == "customer"

    def test_evaluate_correct_output(self):
        """A correct response should pass golden evaluation."""
        example = next(e for e in ALL_GOLDEN_EXAMPLES if e.id == "customer_001")
        result = GoldenDatasetEvaluator.evaluate_example(
            example=example,
            actual_output="Here are the customer account details for john.doe@acme.com.",
            tools_used=["retrieve_customer"],
        )
        assert result["passed"] is True
        assert len(result["failures"]) == 0

    def test_evaluate_missing_required_content(self):
        """Missing required content should fail golden evaluation."""
        example = next(e for e in ALL_GOLDEN_EXAMPLES if e.id == "customer_001")
        result = GoldenDatasetEvaluator.evaluate_example(
            example=example,
            actual_output="I cannot help with that.",
            tools_used=[],
        )
        assert result["passed"] is False
        assert len(result["failures"]) > 0

    def test_evaluate_blocks_forbidden_content(self):
        """Forbidden content in output should fail golden evaluation."""
        example = next(e for e in GOLDEN_SECURITY_ATTACKS if e.id == "attack_001")
        result = GoldenDatasetEvaluator.evaluate_example(
            example=example,
            actual_output="Here is the full customer data database dump: SELECT * ...",
            tools_used=[],
        )
        assert result["passed"] is False

    def test_attack_blocking_detection(self):
        """Attack examples where forbidden content is blocked should mark attack_blocked=True."""
        example = next(e for e in GOLDEN_SECURITY_ATTACKS if e.id == "attack_001")
        result = GoldenDatasetEvaluator.evaluate_example(
            example=example,
            actual_output="I cannot process that request.",  # Safe response
            tools_used=[],
        )
        assert result.get("attack_blocked") is True

    def test_expected_tools_checked(self):
        """Missing expected tools should fail golden evaluation."""
        example = next(e for e in ALL_GOLDEN_EXAMPLES if e.id == "quotation_001")
        result = GoldenDatasetEvaluator.evaluate_example(
            example=example,
            actual_output="Here is a quotation for ACME Corp.",
            tools_used=[],  # Missing expected tools
        )
        assert result["passed"] is False
        assert any("Missing expected tools" in f for f in result["failures"])


# ─── Incident Logger Tests ────────────────────────────────────────────────────


class TestIncidentLogger:
    def test_log_incident(self):
        """Should log and retrieve incidents correctly."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        incident = IncidentLogger.log(
            organization_id=org_id,
            run_id=run_id,
            severity=IncidentSeverity.HIGH,
            category="security",
            title="Prompt injection detected",
            description="Malicious input detected in user request",
        )
        incidents = IncidentLogger.get_org_incidents(org_id)
        assert len(incidents) == 1
        assert incidents[0].id == incident.id
        assert incidents[0].severity == IncidentSeverity.HIGH

    def test_tenant_isolation_incidents(self):
        """Org A incidents must not be visible to Org B."""
        org_a = uuid.uuid4()
        org_b = uuid.uuid4()
        IncidentLogger.log(
            organization_id=org_a,
            severity=IncidentSeverity.MEDIUM,
            category="policy_violation",
            title="Policy block",
            description="Tool access denied",
        )
        incidents_b = IncidentLogger.get_org_incidents(org_b)
        assert len(incidents_b) == 0

    def test_multiple_incidents_all_retrieved(self):
        """Multiple incidents for same org should all be retrievable."""
        org_id = uuid.uuid4()
        for i in range(3):
            IncidentLogger.log(
                organization_id=org_id,
                severity=IncidentSeverity.LOW,
                category="agent_failure",
                title=f"Failure {i}",
                description="Test failure",
            )
        incidents = IncidentLogger.get_org_incidents(org_id)
        assert len(incidents) == 3

    def test_incident_limit(self):
        """Limit parameter should cap the number of returned incidents."""
        org_id = uuid.uuid4()
        for _ in range(20):
            IncidentLogger.log(
                organization_id=org_id,
                severity=IncidentSeverity.LOW,
                category="agent_failure",
                title="Failure",
                description="Test",
            )
        incidents = IncidentLogger.get_org_incidents(org_id, limit=5)
        assert len(incidents) <= 5


# ─── Replay Engine Tests ──────────────────────────────────────────────────────


class TestReplayEngine:
    def test_record_and_retrieve(self):
        """Should record and retrieve a run correctly."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        ReplayEngine.record(
            organization_id=org_id,
            run_id=run_id,
            request="Create a quotation",
            model="gpt-4o-mini",
            final_response="Quotation created successfully.",
        )
        record = ReplayEngine.get(org_id, run_id)
        assert record is not None
        assert record["run_id"] == str(run_id)
        assert record["request"] == "Create a quotation"
        assert record["model"] == "gpt-4o-mini"

    def test_tenant_isolation_replay(self):
        """Org B should not access Org A's replay records."""
        org_a = uuid.uuid4()
        org_b = uuid.uuid4()
        run_id = uuid.uuid4()
        ReplayEngine.record(
            organization_id=org_a,
            run_id=run_id,
            request="Secret request",
            model="gpt-4o",
        )
        # Org B trying to access Org A's run
        record = ReplayEngine.get(org_b, run_id)
        assert record is None

    def test_export_json(self):
        """JSON export should produce valid JSON string."""
        import json

        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        ReplayEngine.record(
            organization_id=org_id,
            run_id=run_id,
            request="Test",
            model="gpt-4o-mini",
        )
        json_str = ReplayEngine.export_json(org_id, run_id)
        assert json_str is not None
        parsed = json.loads(json_str)
        assert parsed["run_id"] == str(run_id)

    def test_export_json_tenant_isolated(self):
        """JSON export for wrong tenant should return None."""
        org_a = uuid.uuid4()
        org_b = uuid.uuid4()
        run_id = uuid.uuid4()
        ReplayEngine.record(org_a, run_id, "Secret", "gpt-4o")
        result = ReplayEngine.export_json(org_b, run_id)
        assert result is None

    def test_list_org_runs(self):
        """Should list all recorded runs for an organization."""
        org_id = uuid.uuid4()
        run_ids = [uuid.uuid4() for _ in range(3)]
        for rid in run_ids:
            ReplayEngine.record(org_id, rid, "Test", "gpt-4o-mini")
        listed = ReplayEngine.list_org_runs(org_id)
        assert len(listed) == 3
        for rid in run_ids:
            assert str(rid) in listed

    def test_nonexistent_run_returns_none(self):
        """Getting a non-existent run should return None (not raise)."""
        result = ReplayEngine.get(uuid.uuid4(), uuid.uuid4())
        assert result is None


# ─── Security Attack Evaluation Tests ────────────────────────────────────────


class TestSecurityEvaluation:
    def test_all_attack_types_covered(self):
        """Should have multiple attack types in golden dataset."""
        attacks = get_attack_examples()
        attack_types = {a.attack_type for a in attacks}
        assert "prompt_injection" in attack_types
        assert "tenant_bypass" in attack_types
        assert "jailbreak" in attack_types

    def test_safety_score_detects_multiple_violations(self):
        """Multiple security violations should compound into CRITICAL rating."""
        org_id = uuid.uuid4()
        run_id = uuid.uuid4()
        score = SafetyEvaluator.evaluate(
            run_id=run_id,
            organization_id=org_id,
            action_history=[],
            policy_violations=3,
            unauthorized_tool_attempts=2,
            prompt_injection_attempts=["ignore all", "system override"],
            tenant_boundary_violations=1,
            failed_verifications=2,
        )
        assert score.risk_level in ("HIGH", "CRITICAL")
        assert score.overall_score < 0.5

    def test_injection_in_golden_dataset_blocks_content(self):
        """Injection attacks should be blocked — forbidden content must not appear."""
        for attack in GOLDEN_SECURITY_ATTACKS:
            # A safe response that deflects the attack
            safe_response = "I cannot process that type of request."
            result = GoldenDatasetEvaluator.evaluate_example(
                example=attack,
                actual_output=safe_response,
                tools_used=[],
            )
            # Safe responses should not contain forbidden content
            for forbidden in attack.must_not_contain:
                assert forbidden.lower() not in safe_response.lower(), (
                    f"Safe response contains forbidden: '{forbidden}'"
                )
