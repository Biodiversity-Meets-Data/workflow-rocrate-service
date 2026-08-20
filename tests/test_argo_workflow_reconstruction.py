import json
from typing import cast

import pytest

from app.argo.models import Workflow
from app.argo.reconstruction import reconstruct_template, reconstruct_workflow


@pytest.fixture
def successful_workflow():
    with open("tests/fixtures/successful_workflow.json") as f:
        wfl = json.load(f)

    return cast(Workflow, wfl)


def test_argo_workflow_reconstruction(successful_workflow):

    print(successful_workflow)
    reconstructed_workflow = reconstruct_workflow(
        successful_workflow, annotations_prefix="dummy"
    )

    assert reconstructed_workflow.keys() == {"kind", "metadata", "spec"}

    assert reconstructed_workflow["kind"] == "Workflow"

    metadata = reconstructed_workflow["metadata"]

    assert metadata == {
        "generateName": "rocrate-test-",
        "annotations": {
            "dummy/author_names": "Lena Creator",
            "dummy/author_ids": "0000-0002-1825-0097",
            "dummy/keywords": "RO-Crate, test, workflow",
            "dummy/license": "CC-BY-4.0",
            "workflows.argoproj.io/description": "A small workflow used to test RO-Crate generation",
            "workflows.argoproj.io/title": "RO-Crate Test Workflow",
        },
    }

    assert reconstructed_workflow["spec"] == successful_workflow["spec"]


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
    successful_workflow["spec"].pop("workflowTemplateRef", None)

    reconstructed_template = reconstruct_template(successful_workflow)

    assert reconstructed_template == {}
