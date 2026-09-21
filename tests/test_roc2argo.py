from typing import cast

import pytest
from rocrate.model import Person
from rocrate.rocrate import ROCrate

from app.argo.roc2argo import generate_workflow_from_rocrate


@pytest.fixture
def rocrate_fixture():
    # Path to the RO-Crate metadata file
    rocrate_path = "tests/fixtures/successful_workflow_rocrate.json"

    rocrate_instance = ROCrate(rocrate_path)
    return rocrate_instance


@pytest.fixture
def workflow_fixture():

    return {
        "metadata": {"annotations": {}},
        "spec": {
            "arguments": {
                "parameters": [
                    {
                        "name": "message",
                        "default": "Default message",
                        "description": "Message to be printed",
                    },
                    {
                        "name": "repeat",
                        "default": "3",
                        "description": "How often to repeat the message",
                    },
                ]
            }
        },
    }


def test_generate_workflow_from_rocrate(rocrate_fixture, workflow_fixture):

    converted_workflow = generate_workflow_from_rocrate(
        crate=rocrate_fixture,
        workflow=workflow_fixture,
        workflow_parameters={
            "message": "Hello from test",
            "repeat": "2",
        },
    )

    assert converted_workflow.kind == "Workflow"
    assert converted_workflow.metadata.annotations.title == "RO-Crate Test Workflow"
    assert (
        converted_workflow.metadata.annotations.description
        == "A small workflow used to test RO-Crate generation"
    )
    assert converted_workflow.metadata.annotations.license == "CC-BY-4.0"
    assert converted_workflow.metadata.annotations.keywords == [
        "RO-Crate",
        "test",
        "workflow",
    ]
    assert converted_workflow.metadata.annotations.authors[0].name == "Lena Creator"
    assert (
        converted_workflow.metadata.annotations.authors[0].id
        == "https://orcid.org/0000-0002-1825-0097"
    )

    assert converted_workflow.spec.arguments is not None
    assert converted_workflow.spec.arguments.parameters is not None
    parameters = {
        parameter.name: parameter.value
        for parameter in converted_workflow.spec.arguments.parameters
    }
    assert parameters["message"] == "Hello from test"
    assert parameters["repeat"] == "2"


def test_generate_workflow_with_multiple_authors(rocrate_fixture, workflow_fixture):

    new_author = cast(
        Person,
        rocrate_fixture.add(
            Person(
                rocrate_fixture,
                identifier="https://orcid.org/0000-0001-2345-6789",
                properties={"name": "John Doe"},
            )
        ),
    )
    rocrate_fixture.root_dataset.append_to("author", new_author)
    converted_workflow = generate_workflow_from_rocrate(
        crate=rocrate_fixture,
        workflow=workflow_fixture,
        workflow_parameters={
            "message": "Hello from test",
            "repeat": "2",
        },
    )

    assert converted_workflow.metadata.annotations.authors is not None
    assert len(converted_workflow.metadata.annotations.authors) == 2
    assert converted_workflow.metadata.annotations.authors[1].name == "John Doe"
    assert converted_workflow.metadata.annotations.authors[0].name == "Lena Creator"
