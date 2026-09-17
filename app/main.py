from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.workflows import router as workflows_router
from app.exceptions import WorkflowNotFoundError, WorkflowParsingError

app = FastAPI()


@app.exception_handler(WorkflowNotFoundError)
def workflow_not_found_exception_handler(request: Request, exc: WorkflowNotFoundError):

    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


@app.exception_handler(WorkflowParsingError)
def workflow_parsing_exception_handler(request: Request, exc: WorkflowParsingError):

    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


app.include_router(workflows_router)
