import pytest

from agentflow import step, workflow
from agentflow.exceptions import WorkflowDefinitionError


def test_static_method_step() -> None:
    """Steps can be static methods, but they must still declare at least one parameter."""
    @workflow
    class StaticWorkflow:
        @step
        @staticmethod
        def static_step(self):
            return "static"

    result = StaticWorkflow().run({})
    assert result.steps[0].output == "static"

def test_class_method_step() -> None:
    """Steps can be class methods."""
    @workflow
    class ClassMethodWorkflow:
        @step
        @classmethod
        def class_step(cls, self):
            return cls.__name__

    result = ClassMethodWorkflow().run({})
    assert result.steps[0].output == "ClassMethodWorkflow"

def test_step_on_top_of_staticmethod() -> None:
    """The @step decorator can be on top of @staticmethod."""
    @workflow
    class WrappedWorkflow:
        @step
        @staticmethod
        def step1(self):
            return "wrapped"

    result = WrappedWorkflow().run({})
    assert result.steps[0].step_name == "step1"
    assert result.steps[0].output == "wrapped"

def test_step_below_staticmethod() -> None:
    """The @step decorator can be below @staticmethod."""
    @workflow
    class WrappedWorkflow:
        @staticmethod
        @step
        def step1(self):
            return "wrapped_below"

    result = WrappedWorkflow().run({})
    assert result.steps[0].step_name == "step1"
    assert result.steps[0].output == "wrapped_below"

def test_duplicate_step_names_via_aliasing_caught_early() -> None:
    """Aliasing a step method should be caught as a duplicate name at definition time."""
    with pytest.raises(WorkflowDefinitionError, match="Duplicate step name"):
        @workflow
        class AliasWorkflow:
            @step
            def step1(self): pass

            alias = step1

def test_invalid_signature_caught_early() -> None:
    """Invalid step signatures should be caught at definition time."""
    with pytest.raises(WorkflowDefinitionError, match="only the workflow instance"):
        @workflow
        class BadSignatureWorkflow:
            @step
            def bad_step(self, context, too_many): pass
