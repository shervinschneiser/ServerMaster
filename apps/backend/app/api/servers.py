from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.server import Server
from app.schemas.server import ServerCreate, ServerResponse, ServerUpdate

router = APIRouter(prefix="/servers", tags=["Servers"])


@router.post(
    "",
    response_model=ServerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_server(
    server_data: ServerCreate,
    session: AsyncSession = Depends(get_db_session),
) -> Server:
    server = Server(**server_data.model_dump())
    session.add(server)
    await session.commit()
    await session.refresh(server)
    return server


@router.get("", response_model=list[ServerResponse])
async def list_servers(
    session: AsyncSession = Depends(get_db_session),
) -> list[Server]:
    result = await session.scalars(select(Server).order_by(Server.id))
    return list(result.all())


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> Server:
    server = await session.get(Server, server_id)

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    return server


@router.patch("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: int,
    server_data: ServerUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> Server:
    server = await session.get(Server, server_id)

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    updates = server_data.model_dump(exclude_unset=True)

    for field in ("name", "hostname"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} cannot be null",
            )

    for field, value in updates.items():
        setattr(server, field, value)

    await session.commit()
    await session.refresh(server)
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
