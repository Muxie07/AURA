from app.policy.schemas import PolicyContext, PolicyDecision, PolicyRuleResult
from app.tools.schemas import RiskLevel


class PolicyEngine:
    """
    Evaluates tool execution attempts against deterministic rules.
    """

    @staticmethod
    def evaluate(context: PolicyContext) -> PolicyRuleResult:
        # Deterministic Rules based on Tool Risk Level and Permissions

        # 1. External Side Effects always require approval (unless specifically whitelisted, none are for now)
        if context.risk_level == RiskLevel.EXTERNAL_SIDE_EFFECT:
            return PolicyRuleResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                reason="External side effects always require human approval.",
            )

        # 2. Write operations
        if context.risk_level == RiskLevel.WRITE:
            if "tools:write" not in context.permissions:
                return PolicyRuleResult(
                    decision=PolicyDecision.DENY,
                    reason="Missing 'tools:write' permission for a write operation.",
                )
            return PolicyRuleResult(
                decision=PolicyDecision.ALLOW,
                reason="Write operation allowed with sufficient permissions.",
            )

        # 3. Read operations
        if context.risk_level == RiskLevel.READ:
            if "tools:read" not in context.permissions:
                return PolicyRuleResult(
                    decision=PolicyDecision.DENY,
                    reason="Missing 'tools:read' permission for a read operation.",
                )
            return PolicyRuleResult(
                decision=PolicyDecision.ALLOW,
                reason="Read operation allowed with sufficient permissions.",
            )

        # Default Deny
        return PolicyRuleResult(
            decision=PolicyDecision.DENY, reason="Unrecognized risk level. Defaulting to DENY."
        )
