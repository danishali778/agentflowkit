"""Content review workflow example for Agent Workflow Kit.

This example demonstrates a retrying step that simulates a flaky moderation
service before a final publishing decision is written into workflow state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from agentflow import step, workflow


@dataclass
class ContentReviewState:
    """State shared across the content review workflow."""

    content_id: str
    body: str
    moderation_attempts: int = 0
    approved: bool = False
    decision_text: str = ""


@workflow(name="content_review")
class ContentReviewWorkflow:
    """Review content with a retrying moderation step."""

    @step(retries=2, retry_on=(TimeoutError,), retry_delay=0.1)
    def moderate_content(self) -> str:
        self.state.moderation_attempts += 1
        if self.state.moderation_attempts < 2:
            raise TimeoutError("Moderation service timed out.")

        self.state.approved = "spam" not in self.state.body.lower()
        return "Moderation check completed."

    @step
    def publish_decision(self) -> str:
        if self.state.approved:
            self.state.decision_text = f"Content {self.state.content_id} approved."
        else:
            self.state.decision_text = f"Content {self.state.content_id} rejected."
        return self.state.decision_text


def main() -> None:
    """Run the content review workflow and print retry-aware results."""
    workflow_instance = ContentReviewWorkflow()
    result = workflow_instance.run(
        ContentReviewState(
            content_id="post_789",
            body="Helpful product feedback with constructive suggestions.",
        )
    )

    print("Content review result")
    print(f"Status: {result.status.value}")
    print(f"State: {asdict(result.state)}")
    print("Step details:")
    for step_result in result.steps:
        print(
            f"  - {step_result.step_name}: {step_result.status.value} "
            f"(attempts={step_result.attempts}, output={step_result.output!r})"
        )


if __name__ == "__main__":
    main()
