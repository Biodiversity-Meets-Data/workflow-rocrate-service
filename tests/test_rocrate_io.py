from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import rocrate_io


def test_workflow_yaml_rejects_python_object_constructors(tmp_path, monkeypatch):
    workflow_path = tmp_path / "workflow.yaml"
    workflow_path.write_text(
        '!!python/object/apply:builtins.print ["YAML constructor executed"]',
        encoding="utf-8",
    )
    crate = SimpleNamespace(
        root_dataset={
            "mainEntity": SimpleNamespace(id=workflow_path.name),
            "license": "CC-BY-4.0",
        },
        source=tmp_path,
    )
    monkeypatch.setattr(rocrate_io, "ROCrate", lambda _: crate)

    with pytest.raises(HTTPException) as exc_info:
        rocrate_io._process_crate_sync("unused.zip")

    assert exc_info.value.status_code == 400
