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
    NodeAlreadyExistsError,
    NodeDuplicateError,
    StorageInterface,
)

router = APIRouter()


def compose_node(request: NodeRequest, creator: Creator) -> NodeMetadata:
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


@router.post("/nodes", tags=["nodes"], status_code=status.HTTP_201_CREATED)
async def create_node(
    request: NodeRequest,
    response: Response,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> NodeResponse:
    node = compose_node(request, creator)

    try:
        response.status_code = status.HTTP_201_CREATED
        return storage.create_node(node)
    except NodeAlreadyExistsError as e:
        response.status_code = status.HTTP_409_CONFLICT
        return e.node
    except NodeDuplicateError as e:
        response.status_code = status.HTTP_409_CONFLICT
        return e.node


@router.get("/nodes/{node_id}", tags=["nodes"])
async def read_node(
    node_id: str,
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> NodeResponse:
    try:
        return storage.read_node(node_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Node not found"},
        ) from e


@router.put("/nodes/{node_id}", tags=["nodes"])
async def update_node(
    node_id: str,
    request: NodeRequest,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> NodeResponse:
    node = compose_node(request, creator)

    try:
        result = storage.update_node(node_id, node)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Node not found"},
        ) from e

    return result


@router.delete("/nodes/{node_id}", tags=["nodes"])
async def delete_node(
    node_id: str,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
):
    try:
        storage.delete_node(node_id)
        return {"detail": "Node deleted"}
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Node not found"},
        ) from e
