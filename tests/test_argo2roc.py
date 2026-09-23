import json

import pytest

from app.argo.argo2roc import generate_WROC_from_workflow, generate_WRROC_from_workflow
from app.argo.models import Author
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


def test_generate_WROC_from_workflow(successful_workflow):
    wroc = generate_WROC_from_workflow(
        successful_workflow,
        prefix="dummy",
        base_url="https://example.com",
        validate=True,
    )
    assert wroc is not None


def test_generate_WRROC_from_workflow(successful_workflow):
    engine = DummyEngine(
        annotations_prefix=dummy_engine_settings.annotations_prefix,
        labels_prefix=dummy_engine_settings.labels_prefix,
        base_url=dummy_engine_settings.base_url,
    )

    wrroc = generate_WRROC_from_workflow(
        successful_workflow,
        engine=engine,
        validate=True,
    )
    assert wrroc is not None


def test_generate_WROC_from_workflow_multiple_authors(successful_workflow):
    authors = successful_workflow.metadata.annotations.authors
    authors.append(
        Author(name="Another Author", id="https://orcid.org/0000-0012-3456-7890")
    )
    successful_workflow.metadata.annotations.authors = authors

    crate = generate_WROC_from_workflow(
        successful_workflow,
        prefix="dummy",
        base_url="https://example.com",
        validate=True,
    )
    assert crate is not None
    crate_authors = crate.root_dataset.get("author", [])
    assert len(crate_authors) == 2
    assert crate_authors[0]["@id"] == "https://orcid.org/0000-0002-1825-0097"
    assert crate_authors[1]["@id"] == "https://orcid.org/0000-0012-3456-7890"

    author1 = crate.get("https://orcid.org/0000-0002-1825-0097")
    assert author1 is not None
    assert author1["name"] == "Lena Creator"
    assert author1["@type"] == "Person"
