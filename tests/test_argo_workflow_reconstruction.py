import json

import pytest

from app.argo.reconstruction import reconstruct_template, reconstruct_workflow
from app.settings import get_dummy_deployment
from app.workflow_engines.dummy_engine import DummyEngine

dummy_engine_settings = get_dummy_deployment()


@pytest.fixture
def successful_workflow():
    with open("tests/fixtures/successful_workflow.json") as f:
        wfl = json.load(f)

    engine = DummyEngine(
        annotations_prefix=dummy_engine_settings.annotations_prefix,
        labels_prefix=dummy_engine_settings.labels_prefix,
        base_url=dummy_engine_settings.base_url,
    )
    return engine.parse_workflow(wfl)


def test_argo_workflow_reconstruction(successful_workflow):
    reconstructed_workflow = reconstruct_workflow(
        successful_workflow,
        engine=DummyEngine(
            annotations_prefix=dummy_engine_settings.annotations_prefix,
            labels_prefix=dummy_engine_settings.labels_prefix,
            base_url=dummy_engine_settings.base_url,
        ),
    )

    assert reconstructed_workflow.keys() == {"kind", "metadata", "spec"}

    assert reconstructed_workflow["kind"] == "Workflow"

    metadata = reconstructed_workflow["metadata"]

    assert metadata == {
        "generateName": "rocrate-test-",
        "annotations": {
            "dummy/author_names": "Lena Creator",
            "dummy/author_ids": "https://orcid.org/0000-0002-1825-0097",
            "dummy/keywords": "RO-Crate, test, workflow",
            "dummy/license": "CC-BY-4.0",
            "workflows.argoproj.io/description": "A small workflow used to test RO-Crate generation",
            "workflows.argoproj.io/title": "RO-Crate Test Workflow",
        },
    }

    assert reconstructed_workflow["spec"] == successful_workflow.spec.model_dump(
        by_alias=False, exclude_unset=True
    )


def test_argo_template_reconstruction(successful_workflow):

    reconstructed_template = reconstruct_template(successful_workflow)

    assert reconstructed_template.keys() == {"kind", "metadata", "spec"}

    assert reconstructed_template["kind"] == "WorkflowTemplate"
    assert reconstructed_template["metadata"]["name"] == "rocrate-test-template"
    assert reconstructed_template["spec"].keys() == {
        "templates",
        "entrypoint",
        "arguments",
        "workflowMetadata",
    }


def test_argo_template_reconstruction_no_template(successful_workflow):
    # Remove the workflowTemplateRef from the spec to simulate a workflow without a template
    successful_workflow.spec.workflowTemplateRef = None

    reconstructed_template = reconstruct_template(successful_workflow)

    assert reconstructed_template == {}
