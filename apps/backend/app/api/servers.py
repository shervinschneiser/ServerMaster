from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
