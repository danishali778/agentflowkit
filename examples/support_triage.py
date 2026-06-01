"""Support triage workflow example for Agent Workflow Kit.

This example highlights context-aware step logic and basic result inspection.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from agentflow import step, workflow


@dataclass
class SupportTicketState:
    """State shared across the support triage workflow."""

    ticket_id: str
    customer_tier: str
    issue_summary: str
    priority: str = "normal"
    assigned_queue: str = "general"
    audit_log: list[str] = field(default_factory=list)


@workflow(name="support_triage")
class SupportTriageWorkflow:
    """Route a support ticket into the right queue."""

    @step
    def classify_priority(self, context) -> str:
        if self.state.customer_tier == "enterprise":
            self.state.priority = "high"
        elif "outage" in self.state.issue_summary.lower():
            self.state.priority = "high"
        else:
            self.state.priority = "normal"

        self.state.audit_log.append(
            f"{context.step_name} handled on attempt {context.attempt}"
        )
        return self.state.priority

    @step
    def assign_queue(self, context) -> str:
        if self.state.priority == "high":
            self.state.assigned_queue = "priority-support"
        else:
            self.state.assigned_queue = "general-support"

        self.state.audit_log.append(
            f"{context.step_name} assigned {self.state.assigned_queue}"
        )
        return self.state.assigned_queue


def main() -> None:
    """Run the support triage workflow and print a readable summary."""
    workflow_instance = SupportTriageWorkflow()
    result = workflow_instance.run(
        SupportTicketState(
            ticket_id="ticket_456",
            customer_tier="enterprise",
            issue_summary="Users cannot access the dashboard.",
        )
    )

    print("Support triage result")
    print(f"Status: {result.status.value}")
    print(f"State: {asdict(result.state)}")
    print("Step details:")
    for step_result in result.steps:
        print(
            f"  - {step_result.step_name}: {step_result.status.value} "
            f"(duration_ms={step_result.duration_ms}, output={step_result.output!r})"
        )


if __name__ == "__main__":
    main()
