import json
from unittest.mock import patch

import yaml
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_workflow_yaml():

    fake_workflow = {
        "kind": "Workflow",
        "metadata": {
            "annotations": {
                "dummy/author_names": "Lena Creator",
                "dummy/author_ids": "0000-0001-2345-6789",
                "dummy/keywords": "RO-Crate, test, workflow",
                "dummy/license": "CC-BY-4.0",
                "workflows.argoproj.io/description": "A small workflow used to test RO-Crate generation",
                "workflows.argoproj.io/title": "RO-Crate Test Workflow",
            }
        },
        "spec": {
            "workflowTemplateRef": {
                "name": "dummy-template",
            },
        },
    }

    response = client.get(
        "/workflow-engines/dummy/workflows/test-workflow/workflow.yaml",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/yaml")

    yaml_content = response.text
    workflow = yaml.safe_load(yaml_content)

    assert workflow == fake_workflow


def test_get_template_yaml():

    fake_template = {
        "kind": "WorkflowTemplate",
        "metadata": {
            "name": "dummy-template",
        },
        "spec": {
            "templates": [],
            "entrypoint": "",
            "arguments": {},
            "workflowMetadata": {},
        },
    }

    response = client.get(
        "/workflow-engines/dummy/workflows/test-workflow/template.yaml",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/yaml")

    yaml_content = response.text
    template = yaml.safe_load(yaml_content)

    assert template == fake_template


def test_get_metadata_json():
    with open("tests/fixtures/successful_workflow.json") as f:
        fake_full_workflow = yaml.safe_load(f)

    with open("tests/fixtures/successful_workflow_rocrate.json") as f:
        expected_rocrate_metadata = json.load(f)

    with patch(
        "app.api.workflows.DummyEngine.get_workflow",
        return_value=fake_full_workflow,
    ):
        response = client.get(
            "/workflow-engines/dummy/workflows/test-workflow/metadata.json",
            headers={"Authorization": "Bearer fake-token"},
        )
    print(response.text)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    assert json.loads(response.text) == expected_rocrate_metadata
