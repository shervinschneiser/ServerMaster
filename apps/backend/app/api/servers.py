from fastapi import APIRouter, Depends, status
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
