"""
This test module requires Anthropic AI API key passed via env variable WORKFLOWS_TEST_ANTHROPIC_API_KEY.
This is supposed to be used only locally, as that would be too much of a cost in CI
"""

import os

import numpy as np
import pytest

from inference.core.env import WORKFLOWS_MAX_CONCURRENT_STEPS
from inference.core.managers.base import ModelManager
from inference.core.workflows.core_steps.common.entities import StepExecutionMode
from inference.core.workflows.execution_engine.core import ExecutionEngine
from tests.workflows.integration_tests.execution.workflows_gallery_collector.decorators import (
    add_to_workflows_gallery,
)

ANTHROPIC_API_KEY = os.getenv("WORKFLOWS_TEST_ANTHROPIC_API_KEY")

UNCONSTRAINED_WORKFLOW = {
    "version": "1.0",
    "inputs": [
        {"type": "WorkflowImage", "name": "image"},
        {"type": "WorkflowParameter", "name": "api_key"},
    ],
    "steps": [
        {
            "type": "roboflow_core/anthropic_claude@v1",
            "name": "claude",
            "images": "$inputs.image",
            "task_type": "unconstrained",
            "prompt": "Give me dominant color of the image",
            "api_key": "$inputs.api_key",
        },
    ],
    "outputs": [
        {
            "type": "JsonField",
            "name": "result",
            "selector": "$steps.claude.output",
        },
    ],
}


@add_to_workflows_gallery(
    category="Workflows with Visual Language Models",
    use_case_title="Prompting Anthropic Claude with arbitrary prompt",
    use_case_description="""
In this example, Anthropic Claude model is prompted with arbitrary text from user 
    """,
    workflow_definition=UNCONSTRAINED_WORKFLOW,
    workflow_name_in_app="claude-arbitrary-prompt",
)
@pytest.mark.skipif(
    condition=ANTHROPIC_API_KEY is None, reason="Anthropic API key not provided"
)
def test_workflow_with_unconstrained_prompt(
    model_manager: ModelManager,
    dogs_image: np.ndarray,
) -> None:
    # given
    workflow_init_parameters = {
        "workflows_core.model_manager": model_manager,
        "workflows_core.step_execution_mode": StepExecutionMode.LOCAL,
    }
    execution_engine = ExecutionEngine.init(
        workflow_definition=UNCONSTRAINED_WORKFLOW,
        init_parameters=workflow_init_parameters,
        max_concurrent_steps=WORKFLOWS_MAX_CONCURRENT_STEPS,
    )

    # when
    result = execution_engine.run(
        runtime_parameters={
            "image": [dogs_image],
            "api_key": ANTHROPIC_API_KEY,
            "prompt": "What is the topic of the image?",
        }
    )

    # then
    assert len(result) == 1, "Single image given, expected single output"
    assert set(result[0].keys()) == {"result"}, "Expected all outputs to be delivered"
    assert (
        isinstance(result[0]["result"], str) and len(result[0]["result"]) > 0
    ), "Expected non-empty string generated"


OCR_WORKFLOW = {
    "version": "1.0",
    "inputs": [
        {"type": "WorkflowImage", "name": "image"},
        {"type": "WorkflowParameter", "name": "api_key"},
    ],
    "steps": [
        {
            "type": "roboflow_core/anthropic_claude@v1",
            "name": "claude",
            "images": "$inputs.image",
            "task_type": "ocr",
            "api_key": "$inputs.api_key",
        },
    ],
    "outputs": [
        {
            "type": "JsonField",
            "name": "result",
            "selector": "$steps.claude.output",
        },
    ],
}


@add_to_workflows_gallery(
    category="Workflows with Visual Language Models",
    use_case_title="Using Anthropic Claude as OCR model",
    use_case_description="""
In this example, Anthropic Claude model is used as OCR system. User just points task type and do not need to provide
any prompt.
    """,
    workflow_definition=OCR_WORKFLOW,
    workflow_name_in_app="claude-ocr",
)
@pytest.mark.skipif(
    condition=ANTHROPIC_API_KEY is None, reason="Anthropic API key not provided"
)
def test_workflow_with_ocr_prompt(
    model_manager: ModelManager,
    license_plate_image: np.ndarray,
) -> None:
    # given
    workflow_init_parameters = {
        "workflows_core.model_manager": model_manager,
        "workflows_core.step_execution_mode": StepExecutionMode.LOCAL,
    }
    execution_engine = ExecutionEngine.init(
        workflow_definition=OCR_WORKFLOW,
        init_parameters=workflow_init_parameters,
        max_concurrent_steps=WORKFLOWS_MAX_CONCURRENT_STEPS,
    )

    # when
    result = execution_engine.run(
        runtime_parameters={
            "image": [license_plate_image],
            "api_key": ANTHROPIC_API_KEY,
        }
    )

    # then
    assert len(result) == 1, "Single image given, expected single output"
    assert set(result[0].keys()) == {"result"}, "Expected all outputs to be delivered"
    assert (
        isinstance(result[0]["result"], str) and len(result[0]["result"]) > 0
    ), "Expected non-empty string generated"


VQA_WORKFLOW = {
    "version": "1.0",
    "inputs": [
        {"type": "WorkflowImage", "name": "image"},
        {"type": "WorkflowParameter", "name": "api_key"},
        {"type": "WorkflowParameter", "name": "prompt"},
    ],
    "steps": [
        {
            "type": "roboflow_core/anthropic_claude@v1",
            "name": "claude",
            "images": "$inputs.image",
            "task_type": "visual-question-answering",
            "prompt": "$inputs.prompt",
            "api_key": "$inputs.api_key",
        },
    ],
    "outputs": [
        {
            "type": "JsonField",
            "name": "result",
            "selector": "$steps.claude.output",
        },
    ],
}


@add_to_workflows_gallery(
    category="Workflows with Visual Language Models",
    use_case_title="Using Anthropic Claude as Visual Question Answering system",
    use_case_description="""
In this example, Anthropic Claude model is used as VQA system. User provides question via prompt.
    """,
    workflow_definition=VQA_WORKFLOW,
    workflow_name_in_app="claude-vqa",
)
@pytest.mark.skipif(
    condition=ANTHROPIC_API_KEY is None, reason="Anthropic API key not provided"
)
def test_workflow_with_vqa_prompt(
    model_manager: ModelManager,
    license_plate_image: np.ndarray,
) -> None:
    # given
    workflow_init_parameters = {
        "workflows_core.model_manager": model_manager,
        "workflows_core.step_execution_mode": StepExecutionMode.LOCAL,
    }
    execution_engine = ExecutionEngine.init(
        workflow_definition=VQA_WORKFLOW,
        init_parameters=workflow_init_parameters,
        max_concurrent_steps=WORKFLOWS_MAX_CONCURRENT_STEPS,
    )

    # when
    result = execution_engine.run(
        runtime_parameters={
            "image": [license_plate_image],
            "api_key": ANTHROPIC_API_KEY,
            "prompt": "What are the brands of the cars?",
        }
    )

    # then
    assert len(result) == 1, "Single image given, expected single output"
    assert set(result[0].keys()) == {"result"}, "Expected all outputs to be delivered"
    assert (
        isinstance(result[0]["result"], str) and len(result[0]["result"]) > 0
    ), "Expected non-empty string generated"


CAPTION_WORKFLOW = {
    "version": "1.0",
    "inputs": [
        {"type": "WorkflowImage", "name": "image"},
        {"type": "WorkflowParameter", "name": "api_key"},
    ],
    "steps": [
        {
            "type": "roboflow_core/anthropic_claude@v1",
            "name": "claude",
            "images": "$inputs.image",
            "task_type": "caption",
            "api_key": "$inputs.api_key",
            "temperature": 1.0,
        },
    ],
    "outputs": [
        {
            "type": "JsonField",
            "name": "result",
            "selector": "$steps.claude.output",
        },
    ],
}


@add_to_workflows_gallery(
    category="Workflows with Visual Language Models",
    use_case_title="Using Anthropic Claude as Image Captioning system",
    use_case_description="""
In this example, Anthropic Claude model is used as Image Captioning system.
    """,
    workflow_definition=CAPTION_WORKFLOW,
    workflow_name_in_app="claude-captioning",
)
@pytest.mark.skipif(
    condition=ANTHROPIC_API_KEY is None, reason="Anthropic API key not provided"
)
def test_workflow_with_captioning_prompt(
    model_manager: ModelManager,
    license_plate_image: np.ndarray,
) -> None:
    # given
    workflow_init_parameters = {
        "workflows_core.model_manager": model_manager,
        "workflows_core.step_execution_mode": StepExecutionMode.LOCAL,
    }
    execution_engine = ExecutionEngine.init(
        workflow_definition=CAPTION_WORKFLOW,
        init_parameters=workflow_init_parameters,
        max_concurrent_steps=WORKFLOWS_MAX_CONCURRENT_STEPS,
    )

    # when
    result = execution_engine.run(
        runtime_parameters={
            "image": [license_plate_image],
            "api_key": ANTHROPIC_API_KEY,
        }
    )

    # then
    assert len(result) == 1, "Single image given, expected single output"
    assert set(result[0].keys()) == {"result"}, "Expected all outputs to be delivered"
    assert (
        isinstance(result[0]["result"], str) and len(result[0]["result"]) > 0
    ), "Expected non-empty string generated"


CLASSIFICATION_WORKFLOW = {
    "version": "1.0",
    "inputs": [
        {"type": "WorkflowImage", "name": "image"},
        {"type": "WorkflowParameter", "name": "api_key"},
        {"type": "WorkflowParameter", "name": "classes"},
    ],
    "steps": [
        {
            "type": "roboflow_core/anthropic_claude@v1",
            "name": "claude",
            "images": "$inputs.image",
            "task_type": "classification",
            "classes": "$inputs.classes",
            "api_key": "$inputs.api_key",
        },
        {
            "type": "roboflow_core/vlm_as_classifier@v1",
            "name": "parser",
            "image": "$inputs.image",
            "vlm_output": "$steps.claude.output",
            "classes": "$steps.claude.classes",
        },
        {
            "type": "roboflow_core/property_definition@v1",
            "name": "top_class",
            "operations": [
                {"type": "ClassificationPropertyExtract", "property_name": "top_class"}
            ],
            "data": "$steps.parser.predictions",
        },
    ],
    "outputs": [
        {
            "type": "JsonField",
            "name": "claude_result",
            "selector": "$steps.claude.output",
        },
        {
            "type": "JsonField",
            "name": "top_class",
            "selector": "$steps.top_class.output",
        },
        {
            "type": "JsonField",
            "name": "parsed_prediction",
            "selector": "$steps.parser.*",
        },
    ],
}


@add_to_workflows_gallery(
    category="Workflows with Visual Language Models",
    use_case_title="Using Anthropic Claude as multi-class classifier",
    use_case_description="""
In this example, Anthropic Claude model is used as classifier. Output from the model is parsed by
special `roboflow_core/vlm_as_classifier@v1` block which turns model output text into
full-blown prediction, which can later be used by other blocks compatible with 
classification predictions - in this case we extract top-class property.
    """,
    workflow_definition=CLASSIFICATION_WORKFLOW,
    workflow_name_in_app="claude-multi-class-classifier",
)
@pytest.mark.skipif(
    condition=ANTHROPIC_API_KEY is None, reason="Anthropic API key not provided"
)
def test_workflow_with_multi_class_classifier_prompt(
    model_manager: ModelManager,
    dogs_image: np.ndarray,
) -> None:
    # given
    workflow_init_parameters = {
        "workflows_core.model_manager": model_manager,
        "workflows_core.step_execution_mode": StepExecutionMode.LOCAL,
    }
    execution_engine = ExecutionEngine.init(
        workflow_definition=CLASSIFICATION_WORKFLOW,
        init_parameters=workflow_init_parameters,
        max_concurrent_steps=WORKFLOWS_MAX_CONCURRENT_STEPS,
    )

    # when
    result = execution_engine.run(
        runtime_parameters={
            "image": [dogs_image],
            "api_key": ANTHROPIC_API_KEY,
            "classes": ["cat", "dog"],
        }
    )

    # then
    assert len(result) == 1, "Single image given, expected single output"
    assert set(result[0].keys()) == {
        "claude_result",
        "top_class",
        "parsed_prediction",
    }, "Expected all outputs to be delivered"
    assert (
        isinstance(result[0]["claude_result"], str)
        and len(result[0]["claude_result"]) > 0
    ), "Expected non-empty string generated"
    assert result[0]["top_class"] == "dog"
    assert result[0]["parsed_prediction"]["error_status"] is False


MULTI_LABEL_CLASSIFICATION_WORKFLOW = {
    "version": "1.0",
    "inputs": [
        {"type": "WorkflowImage", "name": "image"},
        {"type": "WorkflowParameter", "name": "api_key"},
        {"type": "WorkflowParameter", "name": "classes"},
    ],
    "steps": [
        {
            "type": "roboflow_core/anthropic_claude@v1",
            "name": "claude",
            "images": "$inputs.image",
            "task_type": "multi-label-classification",
            "classes": "$inputs.classes",
            "api_key": "$inputs.api_key",
        },
        {
            "type": "roboflow_core/vlm_as_classifier@v1",
            "name": "parser",
            "image": "$inputs.image",  # requires image input to construct valid output compatible with "inference"
            "vlm_output": "$steps.claude.output",
            "classes": "$steps.claude.classes",
        },
        {
            "type": "roboflow_core/property_definition@v1",
            "name": "top_class",
            "operations": [
                {"type": "ClassificationPropertyExtract", "property_name": "top_class"}
            ],
            "data": "$steps.parser.predictions",
        },
    ],
    "outputs": [
        {
            "type": "JsonField",
            "name": "result",
            "selector": "$steps.top_class.output",
        },
        {
            "type": "JsonField",
            "name": "parsed_prediction",
            "selector": "$steps.parser.*",
        },
    ],
}


@add_to_workflows_gallery(
    category="Workflows with Visual Language Models",
    use_case_title="Using Anthropic Claude as multi-label classifier",
    use_case_description="""
In this example, Anthropic Claude model is used as multi-label classifier. Output from the model is parsed by
special `roboflow_core/vlm_as_classifier@v1` block which turns model output text into
full-blown prediction, which can later be used by other blocks compatible with 
classification predictions - in this case we extract top-class property.
    """,
    workflow_definition=MULTI_LABEL_CLASSIFICATION_WORKFLOW,
    workflow_name_in_app="claude-multi-label-classifier",
)
@pytest.mark.skipif(
    condition=ANTHROPIC_API_KEY is None, reason="Anthropic API key not provided"
)
def test_workflow_with_multi_label_classifier_prompt(
    model_manager: ModelManager,
    dogs_image: np.ndarray,
) -> None:
    # given
    workflow_init_parameters = {
        "workflows_core.model_manager": model_manager,
        "workflows_core.step_execution_mode": StepExecutionMode.LOCAL,
    }
    execution_engine = ExecutionEngine.init(
        workflow_definition=MULTI_LABEL_CLASSIFICATION_WORKFLOW,
        init_parameters=workflow_init_parameters,
        max_concurrent_steps=WORKFLOWS_MAX_CONCURRENT_STEPS,
    )

    # when
    result = execution_engine.run(
        runtime_parameters={
            "image": [dogs_image],
            "api_key": ANTHROPIC_API_KEY,
            "classes": ["cat", "dog"],
        }
    )

    # then
    assert len(result) == 1, "Single image given, expected single output"
    assert set(result[0].keys()) == {
        "result",
        "parsed_prediction",
    }, "Expected all outputs to be delivered"
    assert result[0]["result"] == ["dog"]
    assert result[0]["parsed_prediction"]["error_status"] is False


STRUCTURED_PROMPTING_WORKFLOW = {
    "version": "1.0",
    "inputs": [
        {"type": "WorkflowImage", "name": "image"},
        {"type": "WorkflowParameter", "name": "api_key"},
    ],
    "steps": [
        {
            "type": "roboflow_core/anthropic_claude@v1",
            "name": "claude",
            "images": "$inputs.image",
            "task_type": "structured-answering",
            "output_structure": {
                "dogs_count": "count of dogs instances in the image",
                "cats_count": "count of cats instances in the image",
            },
            "api_key": "$inputs.api_key",
        },
        {
            "type": "roboflow_core/json_parser@v1",
            "name": "parser",
            "raw_json": "$steps.claude.output",
            "expected_fields": ["dogs_count", "cats_count"],
        },
        {
            "type": "roboflow_core/property_definition@v1",
            "name": "property_definition",
            "operations": [{"type": "ToString"}],
            "data": "$steps.parser.dogs_count",
        },
    ],
    "outputs": [
        {
            "type": "JsonField",
            "name": "result",
            "selector": "$steps.property_definition.output",
        }
    ],
}


@add_to_workflows_gallery(
    category="Workflows with Visual Language Models",
    use_case_title="Using Anthropic Claude to provide structured JSON",
    use_case_description="""
In this example, Anthropic Claude model is expected to provide structured output in JSON, which can later be
parsed by dedicated `roboflow_core/json_parser@v1` block which transforms string into dictionary 
and expose it's keys to other blocks for further processing. In this case, parsed output is
transformed using `roboflow_core/property_definition@v1` block.
    """,
    workflow_definition=STRUCTURED_PROMPTING_WORKFLOW,
    workflow_name_in_app="claude-structured-prompting",
)
@pytest.mark.skipif(
    condition=ANTHROPIC_API_KEY is None, reason="Anthropic API key not provided"
)
def test_workflow_with_structured_prompt(
    model_manager: ModelManager,
    dogs_image: np.ndarray,
) -> None:
    # given
    workflow_init_parameters = {
        "workflows_core.model_manager": model_manager,
        "workflows_core.step_execution_mode": StepExecutionMode.LOCAL,
    }
    execution_engine = ExecutionEngine.init(
        workflow_definition=STRUCTURED_PROMPTING_WORKFLOW,
        init_parameters=workflow_init_parameters,
        max_concurrent_steps=WORKFLOWS_MAX_CONCURRENT_STEPS,
    )

    # when
    result = execution_engine.run(
        runtime_parameters={
            "image": [dogs_image],
            "api_key": ANTHROPIC_API_KEY,
        }
    )

    # then
    assert len(result) == 1, "Single image given, expected single output"
    assert set(result[0].keys()) == {"result"}, "Expected all outputs to be delivered"
    assert result[0]["result"] == "2"


OBJECT_DETECTION_WORKFLOW = {
    "version": "1.0",
    "inputs": [
        {"type": "WorkflowImage", "name": "image"},
        {"type": "WorkflowParameter", "name": "api_key"},
        {"type": "WorkflowParameter", "name": "classes"},
    ],
    "steps": [
        {
            "type": "roboflow_core/anthropic_claude@v1",
            "name": "claude",
            "images": "$inputs.image",
            "task_type": "object-detection",
            "classes": "$inputs.classes",
            "api_key": "$inputs.api_key",
        },
        {
            "type": "roboflow_core/vlm_as_detector@v1",
            "name": "parser",
            "vlm_output": "$steps.claude.output",
            "image": "$inputs.image",
            "classes": "$steps.claude.classes",
            "model_type": "anthropic-claude",
            "task_type": "object-detection",
        },
    ],
    "outputs": [
        {
            "type": "JsonField",
            "name": "claude_result",
            "selector": "$steps.claude.output",
        },
        {
            "type": "JsonField",
            "name": "parsed_prediction",
            "selector": "$steps.parser.predictions",
        },
    ],
}


@add_to_workflows_gallery(
    category="Workflows with Visual Language Models",
    use_case_title="Using Anthropic Claude as object-detection model",
    use_case_description="""
In this example, Anthropic Claude model is expected to provide output, which can later be
parsed by dedicated `roboflow_core/vlm_as_detector@v1` block which transforms string into `sv.Detections`, 
which can later be used by other blocks processing object-detection predictions.
    """,
    workflow_definition=OBJECT_DETECTION_WORKFLOW,
    workflow_name_in_app="claude-object-detection",
)
@pytest.mark.skipif(
    condition=ANTHROPIC_API_KEY is None, reason="Anthropic API key not provided"
)
def test_workflow_with_object_detection_prompt(
    model_manager: ModelManager,
    dogs_image: np.ndarray,
) -> None:
    # given
    workflow_init_parameters = {
        "workflows_core.model_manager": model_manager,
        "workflows_core.step_execution_mode": StepExecutionMode.LOCAL,
    }
    execution_engine = ExecutionEngine.init(
        workflow_definition=OBJECT_DETECTION_WORKFLOW,
        init_parameters=workflow_init_parameters,
        max_concurrent_steps=WORKFLOWS_MAX_CONCURRENT_STEPS,
    )

    # when
    result = execution_engine.run(
        runtime_parameters={
            "image": [dogs_image],
            "api_key": ANTHROPIC_API_KEY,
            "classes": ["cat", "dog"],
        }
    )

    # then
    assert len(result) == 1, "Single image given, expected single output"
    assert set(result[0].keys()) == {
        "claude_result",
        "parsed_prediction",
    }, "Expected all outputs to be delivered"
    assert result[0]["parsed_prediction"].data["class_name"].tolist() == [
        "dog",
        "dog",
    ], "Expected 2 dogs to be detected"