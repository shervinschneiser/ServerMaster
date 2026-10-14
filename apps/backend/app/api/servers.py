from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.server import Server
from app.schemas.server import ServerCreate, ServerResponse

router = APIRouter(prefix="/servers", tags=["servers"])


@router.post(
    "",
    response_model=ServerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_server(
    data: ServerCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Server:
    server = Server(
        name=data.name,
        hostname=data.hostname,
        description=data.description,
    )

    session.add(server)
    await session.commit()
    await session.refresh(server)

    return server


@router.get(
    "",
    response_model=list[ServerResponse],
)
async def list_servers(
    session: AsyncSession = Depends(get_db_session),
) -> list[Server]:
    result = await session.execute(select(Server).order_by(Server.id))

    return list(result.scalars().all())


@router.get(
    "/{server_id}",
    response_model=ServerResponse,
)
async def get_server(
    server_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> Server:
    server = await session.get(Server, server_id)

    if server is None:
        raise HTTPException(
            status_code=404,
            detail="Server not found",
        )

    return server


@router.delete(
    "/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_server(
    server_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    server = await session.get(Server, server_id)

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    await session.delete(server)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
