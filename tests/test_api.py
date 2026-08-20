import yaml
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_workflow_yaml():

    response = client.get(
        "/workflow-engines/dummy/workflows/test-workflow/workflow.yaml",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/yaml")

    yaml_content = response.text
    workflow = yaml.safe_load(yaml_content)

    assert workflow["kind"] == "Workflow"
    assert "annotations" in workflow["metadata"]
    assert "managedFields" not in workflow["metadata"]
    assert "spec" in workflow
    assert "status" not in workflow


def test_get_template_yaml():

    response = client.get(
        "/workflow-engines/dummy/workflows/test-workflow/template.yaml",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/yaml")

    yaml_content = response.text
    template = yaml.safe_load(yaml_content)

    assert template["kind"] == "WorkflowTemplate"
    assert "name" in template["metadata"]
    for key in ["templates", "entrypoint", "arguments", "workflowMetadata"]:
        assert key in template["spec"]


def test_get_WROC_metadata_json():

    response = client.get(
        "/workflow-engines/dummy/workflows/test-workflow/metadata?profile=WROC",
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    metadata = response.json()["@graph"]
    root_dataset = next(item for item in metadata if item["@id"] == "./")

    assert root_dataset["@type"] == "Dataset"
    for key in ["name", "description", "license", "keywords"]:
        assert key in root_dataset

    workflow = next(
        item for item in metadata if item["@id"] == root_dataset["mainEntity"]["@id"]
    )
    assert workflow["@type"] == ["File", "ComputationalWorkflow", "SoftwareSourceCode"]


def test_get_WRROC_metadata_json():

    response = client.get(
        "/workflow-engines/dummy/workflows/test-workflow/metadata?profile=WRROC",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    metadata = response.json()["@graph"]
    root_dataset = next(item for item in metadata if item["@id"] == "./")

    assert root_dataset["@type"] == "Dataset"
    for key in ["name", "description", "license", "keywords"]:
        assert key in root_dataset

    workflow = next(
        item for item in metadata if item["@id"] == root_dataset["mainEntity"]["@id"]
    )
    assert workflow["@type"] == ["File", "ComputationalWorkflow", "SoftwareSourceCode"]

    createAction = next(
        item for item in metadata if item["@id"] == root_dataset["mentions"]["@id"]
    )
    assert createAction["@type"] == "CreateAction"
