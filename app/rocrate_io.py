import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, cast

import yaml
from fastapi import HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from rocrate.model import ContextEntity
from rocrate.rocrate import ROCrate


def _copy_and_validate_zip(
    source_file,
    destination_path: str,
) -> None:
    """
    Synchronously copy the uploaded file to disk and validate it as a ZIP.

    This function performs blocking filesystem/ZIP operations, so it is
    executed in a worker thread.
    """
    source_file.seek(0)

    with open(destination_path, "wb") as destination:
        shutil.copyfileobj(source_file, destination)

    # Validate the copied file.
    with zipfile.ZipFile(destination_path):
        pass


def _process_crate_sync(
    tmp_file_path: str,
) -> tuple[ROCrate, dict[str, Any]]:
    """
    Parse and validate the RO-Crate.

    All operations here are synchronous/blocking by design.
    The caller runs this function in a worker thread.
    """
    crate = ROCrate(tmp_file_path)

    try:
        main_entity_id = cast(
            ContextEntity,
            crate.root_dataset["mainEntity"],
        ).id

        crate_source = cast(Path, crate.source)
        workflow_path = crate_source / main_entity_id

    except (KeyError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid RO-Crate: Missing mainEntity",
        )

    if not workflow_path.exists():
        raise HTTPException(
            status_code=400,
            detail="Workflow file not found in RO-Crate",
        )

    try:
        with open(workflow_path, "r") as f:
            workflow = yaml.load(
                f,
                Loader=yaml.CSafeLoader,
            )

    except yaml.YAMLError:
        raise HTTPException(
            status_code=400,
            detail="Workflow file contains invalid or unsupported YAML",
        )

    if "license" not in crate.root_dataset:
        raise HTTPException(
            status_code=400,
            detail="License not defined in RO-Crate",
        )

    return crate, workflow


async def get_crate_workflow_from_zip(
    file: UploadFile,
) -> tuple[ROCrate, dict[str, Any]]:

    if file.content_type not in [
        "application/zip",
        "application/octet-stream",
    ]:
        raise HTTPException(
            status_code=400,
            detail="File is not a zip file",
        )

    try:
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            await run_in_threadpool(
                _copy_and_validate_zip,
                file.file,
                tmp.name,
            )

            crate, workflow = await run_in_threadpool(
                _process_crate_sync,
                tmp.name,
            )

            return crate, workflow

    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="File is not a valid zip file",
        )

    finally:
        await file.close()
