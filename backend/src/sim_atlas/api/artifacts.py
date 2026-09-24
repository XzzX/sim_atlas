import datetime as dt
import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from sim_atlas.dependencies import get_storage
from sim_atlas.models import (
    AnnotationResponse,
    NodeMetadata,
    NodeRequest,
    NodeResponse,
)
from sim_atlas.security import Creator, get_current_user
from sim_atlas.storage_interface import (
    ArtifactAlreadyExistsError,
    ArtifactDuplicateError,
    StorageInterface,
)

router = APIRouter()


def compose_artifact(request: NodeRequest, creator: Creator) -> NodeMetadata:
    # Content-addressable identity for both functions and workflows (ADR-0005):
    # the source hash doubles as the id when the caller doesn't supply one.
    source_hash = hashlib.sha256(request.source_code.encode()).hexdigest()
    return NodeMetadata(
        id=request.id or source_hash,
        hash=request.hash or source_hash,
        author_name=request.author_name,
        author_email=request.author_email,
        creator_name=creator.name,
        creator_email=creator.email,
        creation_timestamp=dt.datetime.now(dt.UTC).isoformat(),
        name=request.name,
        artifact_type=request.artifact_type,
        category=request.category,
        keywords=request.keywords,
        homepage_url=request.homepage_url,
        documentation_url=request.documentation_url,
        source_url=request.source_url,
        python_import=request.python_import,
        dependencies=request.dependencies,
        packages=request.packages,
        source_code=request.source_code,
        docstring=request.docstring,
        brief_description=request.brief_description or "",
        description=request.description or "",
        inputs=[AnnotationResponse(**a.model_dump()) for a in request.inputs],
        outputs=[AnnotationResponse(**a.model_dump()) for a in request.outputs],
        see_also=request.see_also,
        uses=request.uses,
        wf_definition=request.wf_definition,
    )


@router.post("/artifacts", tags=["artifacts"], status_code=status.HTTP_201_CREATED)
async def create_artifact(
    request: NodeRequest,
    response: Response,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> NodeResponse:
    artifact = compose_artifact(request, creator)

    try:
        response.status_code = status.HTTP_201_CREATED
        return storage.create_artifact(artifact)
    except ArtifactAlreadyExistsError as e:
        response.status_code = status.HTTP_409_CONFLICT
        return e.artifact
    except ArtifactDuplicateError as e:
        response.status_code = status.HTTP_409_CONFLICT
        return e.artifact


@router.get("/artifacts/{artifact_id}", tags=["artifacts"])
async def read_artifact(
    artifact_id: str,
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> NodeResponse:
    try:
        return storage.read_artifact(artifact_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Artifact not found"},
        ) from e


@router.put("/artifacts/{artifact_id}", tags=["artifacts"])
async def update_artifact(
    artifact_id: str,
    request: NodeRequest,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> NodeResponse:
    artifact = compose_artifact(request, creator)

    try:
        result = storage.update_artifact(artifact_id, artifact)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Artifact not found"},
        ) from e

    return result


@router.delete("/artifacts/{artifact_id}", tags=["artifacts"])
async def delete_artifact(
    artifact_id: str,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
):
    try:
        storage.delete_artifact(artifact_id)
        return {"detail": "Artifact deleted"}
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Artifact not found"},
        ) from e
