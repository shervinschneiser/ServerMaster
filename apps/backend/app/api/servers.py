from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db_session
from app.models.server import Server
from app.schemas.server import ServerCreate, ServerResponse, ServerUpdate
from app.schemas.agent_token import AgentTokenIssuedResponse
from app.services.agent_tokens import create_agent_token
from app.services.agent_auth import authenticate_agent

from datetime import UTC, datetime
from app.models.agent_token import AgentToken

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

    try:
        await session.commit()
        await session.refresh(server)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A server with this hostname already exists",
        ) from exc

    return server


@router.get("", response_model=list[ServerResponse])
async def list_servers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    search: str | None = Query(default=None, min_length=1, max_length=255),
    session: AsyncSession = Depends(get_db_session),
) -> list[Server]:
    statement = select(Server).order_by(Server.id)

    if search and search.strip():
        search_term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Server.name.ilike(search_term),
                Server.hostname.ilike(search_term),
            )
        )

    statement = statement.offset(skip).limit(min(limit, 100))

    result = await session.scalars(statement)
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


@router.post(
    "/{server_id}/tokens",
    response_model=AgentTokenIssuedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_agent_token(
    server_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> AgentTokenIssuedResponse:
    server = await session.get(Server, server_id)

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    agent_token, raw_token = await create_agent_token(
        session=session,
        server_id=server_id,
    )

    await session.commit()
    await session.refresh(agent_token)

    return AgentTokenIssuedResponse(
        id=agent_token.id,
        server_id=agent_token.server_id,
        created_at=agent_token.created_at,
        token=raw_token,
    )


@router.delete(
    "/{server_id}/tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_agent_token(
    server_id: int,
    token_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    server = await session.get(Server, server_id)

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    agent_token = await session.get(AgentToken, token_id)

    if agent_token is None or agent_token.server_id != server_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent token not found",
        )

    if agent_token.revoked_at is None:
        agent_token.revoked_at = datetime.now(UTC)
        await session.commit()


@router.get("/agent/verify")
async def verify_agent_token(
    agent_token: AgentToken = Depends(authenticate_agent),
) -> dict[str, int | str]:
    return {
        "status": "authenticated",
        "server_id": agent_token.server_id,
    }
