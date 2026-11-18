
from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)
from fastapi.concurrency import run_in_threadpool

from backend.app.services.explorer_service import (
    get_neighborhood,
    search_entities,
)


router = APIRouter(
    prefix="/api/explorer",
    tags=["Graph Explorer"],
)



@router.get("/entities")
async def search_graph_entities(
    q: str = "",
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    origin: str | None = Query(
        default=None,
        pattern="^(SYNTHETIC|DATACO|BENCHMARK)$",
    ),
):
    try:
        return await run_in_threadpool(
            search_entities,
            query=q,
            limit=limit,
            offset=offset,
            data_origin=origin,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Entity search failed: {exc}",
        ) from exc



@router.get("/neighborhood/{node_id}")
async def explore_neighborhood(
    node_id: str,
    depth: int = Query(2, ge=1, le=4),
    max_nodes: int = Query(150, ge=1, le=300),
    max_relationships: int = Query(
        500,
        ge=1,
        le=1000,
    ),
    direction: str = Query(
        "downstream",
        pattern="^(downstream|upstream|both)$",
    ),
):
    try:
        result = await run_in_threadpool(
            get_neighborhood,
            node_id=node_id,
            depth=depth,
            max_nodes=max_nodes,
            max_relationships=max_relationships,
            direction=direction,
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Supply-chain entity not found",
            )

        return result

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Graph exploration failed: {exc}",
        ) from exc
