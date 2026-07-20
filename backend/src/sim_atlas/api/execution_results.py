import datetime as dt
import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from sim_atlas.dependencies import get_storage
from sim_atlas.models import (
    ExecutionResultMetadata,
    ExecutionResultRequest,
    ExecutionResultResponse,
)
from sim_atlas.security import Creator, get_current_user
from sim_atlas.storage_interface import (
    ExecutionResultAlreadyExistsError,
    ExecutionResultDuplicateError,
    StorageInterface,
)

router = APIRouter()


def compose_execution_result(
    request: ExecutionResultRequest, creator: Creator
) -> ExecutionResultMetadata:
    hash_input = (
        request.artifact_id
        + "".join(f"{v.label}={v.value}" for v in request.inputs)
        + request.outputs
    )
    return ExecutionResultMetadata(
        id=str(uuid.uuid4()),
        author_name=request.author_name,
        author_email=request.author_email,
        creator_name=creator.name,
        creator_email=creator.email,
        creation_timestamp=dt.datetime.now(dt.UTC).isoformat(),
        artifact_id=request.artifact_id,
        inputs=request.inputs,
        outputs=request.outputs,
        hash=hashlib.sha256(hash_input.encode()).hexdigest(),
    )


@router.post(
    "/execution_results",
    tags=["execution_results"],
    status_code=status.HTTP_201_CREATED,
)
async def create_execution_result(
    request: ExecutionResultRequest,
    response: Response,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> ExecutionResultResponse:
    result = compose_execution_result(request, creator)
    try:
        response.status_code = status.HTTP_201_CREATED
        return storage.create_execution_result(result)
    except ExecutionResultAlreadyExistsError as e:
        response.status_code = status.HTTP_409_CONFLICT
        return e.execution_result
    except ExecutionResultDuplicateError as e:
        response.status_code = status.HTTP_409_CONFLICT
        return e.execution_result


@router.get(
    "/execution_results/{result_id}",
    tags=["execution_results"],
)
async def read_execution_result(
    result_id: str,
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> ExecutionResultResponse:
    try:
        return storage.read_execution_result(result_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Execution result not found"},
        ) from e


@router.put(
    "/execution_results/{result_id}",
    tags=["execution_results"],
)
async def update_execution_result(
    result_id: str,
    request: ExecutionResultRequest,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> ExecutionResultResponse:
    result = compose_execution_result(request, creator)
    try:
        return storage.update_execution_result(result_id, result)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Execution result not found"},
        ) from e


@router.delete(
    "/execution_results/{result_id}",
    tags=["execution_results"],
)
async def delete_execution_result(
    result_id: str,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> dict[str, str]:
    try:
        storage.delete_execution_result(result_id)
        return {"detail": "Execution result deleted"}
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Execution result not found"},
        ) from e


@router.get(
    "/artifacts/{artifact_id}/execution_results",
    tags=["execution_results"],
)
async def list_execution_results_by_artifact(
    artifact_id: str,
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> list[ExecutionResultMetadata]:
    return storage.read_execution_results_by_artifact(artifact_id)
