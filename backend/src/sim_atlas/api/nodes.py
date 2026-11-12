import datetime as dt
import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sim_atlas_models import (
    NODE_EXISTS_MAX_IDS,
    NodeExistsRequest,
    NodeExistsResponse,
    NodeRequest,
    NodeResponse,
)

from sim_atlas.dependencies import get_storage
from sim_atlas.models import NodeMetadata
from sim_atlas.security import Creator, get_current_user
from sim_atlas.storage.storage_interface import (
    NodeAlreadyExistsError,
    NodeDuplicateError,
    StorageInterface,
)

router = APIRouter()


def compose_node(request: NodeRequest, creator: Creator) -> NodeMetadata:
    """The stored node: every client-owned field of *request*, plus server fields.

    Built from the request's dump, so a field added to ``NodeRequest`` reaches
    storage without touching this function (ADR-0024).
    """
    # Content-addressable identity for both functions and workflows (ADR-0005):
    # the source hash doubles as the id when the caller doesn't supply one.
    source_hash = hashlib.sha256(request.source_code.encode()).hexdigest()
    return NodeMetadata.model_validate(
        request.model_dump()
        | {
            "id": request.id or source_hash,
            "hash": request.hash or source_hash,
            "creator_name": creator.name,
            "creator_email": creator.email,
            "creation_timestamp": dt.datetime.now(dt.UTC).isoformat(),
            "brief_description": request.brief_description or "",
            "description": request.description or "",
        }
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


# Declared before the ``/nodes/{node_id}`` routes: should one ever take POST, the
# first match wins and ``exists`` must not be read as a node id.
@router.post(
    "/nodes/exists",
    tags=["nodes"],
    summary="Check which node ids are stored",
    description=(
        "Return the subset of `ids` that are stored, matched on node id exactly "
        "like `GET /nodes/{node_id}`. The result keeps request order and drops "
        f"duplicates. At most {NODE_EXISTS_MAX_IDS} ids per request (422 above). "
        "Public, like every read route. Lets a client check a whole batch in "
        "one request instead of one `GET /nodes/{node_id}` per id."
    ),
)
async def nodes_exist(
    request: NodeExistsRequest,
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> NodeExistsResponse:
    stored = storage.existing_ids(request.ids)
    return NodeExistsResponse(
        existing=[i for i in dict.fromkeys(request.ids) if i in stored]
    )


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
    try:
        existing = storage.read_node(node_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Node not found"},
        ) from e

    # Updates only change metadata. A different id or different content is a
    # different node and has to be uploaded with POST, so links to this id survive.
    if request.id is not None and request.id != node_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"id": node_id, "message": "The id of a node cannot be changed"},
        )
    node = compose_node(request, creator)
    if node.source_code != existing.source_code or node.hash != existing.hash:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "id": node_id,
                "message": "The source code differs from the stored node. "
                "Updates can only change metadata; upload a new node with POST /nodes.",
            },
        )

    node = node.model_copy(
        update={
            "id": existing.id,
            "creator_name": existing.creator_name,
            "creator_email": existing.creator_email,
            "creation_timestamp": existing.creation_timestamp,
        }
    )
    return storage.update_node(node_id, node)


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
