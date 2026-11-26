from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.agent_token import AgentToken
from app.models.server import Server
from app.schemas.agent_token import AgentTokenIssuedResponse
from app.schemas.heartbeat import HeartbeatResponse
from app.schemas.server import ServerCreate, ServerResponse, ServerUpdate
from app.services.agent_auth import authenticate_agent
from app.services.agent_tokens import create_agent_token

router = APIRouter(prefix="/servers", tags=["Servers"])

HEARTBEAT_TIMEOUT = timedelta(seconds=120)


def get_online_condition(now: datetime):
    cutoff = now - HEARTBEAT_TIMEOUT

    return (
        Server.is_online.is_(True),
        Server.last_seen_at >= cutoff,
    )


def is_server_online(server: Server, now: datetime) -> bool:
    if not server.is_online or server.last_seen_at is None:
        return False

    return server.last_seen_at >= now - HEARTBEAT_TIMEOUT


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


@router.get("/stats")
async def get_server_stats(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, int]:
    now = datetime.now(UTC)
    cutoff = now - HEARTBEAT_TIMEOUT

    online_condition = (
        Server.is_online.is_(True)
        & Server.last_seen_at.is_not(None)
        & (Server.last_seen_at >= cutoff)
    )

    statement = select(
        func.count(Server.id),
        func.count(Server.id).filter(online_condition),
    )

    result = await session.execute(statement)
    total_count, online_count = result.one()

    return {
        "total": total_count,
        "online": online_count,
        "offline": total_count - online_count,
    }


@router.get("", response_model=list[ServerResponse])
async def list_servers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    search: str | None = Query(default=None, min_length=1, max_length=255),
    is_online: bool | None = Query(default=None),
    hostname: str | None = Query(default=None, min_length=1, max_length=255),
    seen_after: datetime | None = Query(default=None),
    seen_before: datetime | None = Query(default=None),
    sort_by: str = Query(
        default="id",
        pattern="^(id|name|created_at|last_seen_at)$",
    ),
    order: str = Query(
        default="asc",
        pattern="^(asc|desc)$",
    ),
    session: AsyncSession = Depends(get_db_session),
) -> list[Server]:
    now = datetime.now(UTC)
    cutoff = now - HEARTBEAT_TIMEOUT

    statement = select(Server)

    if search and search.strip():
        search_term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Server.name.ilike(search_term),
                Server.hostname.ilike(search_term),
            )
        )

    if is_online is True:
        statement = statement.where(
            Server.is_online.is_(True),
            Server.last_seen_at >= cutoff,
        )
    elif is_online is False:
        statement = statement.where(
            or_(
                Server.is_online.is_(False),
                Server.last_seen_at.is_(None),
                Server.last_seen_at < cutoff,
            )
        )

    if hostname:
        statement = statement.where(Server.hostname == hostname.strip())

    if seen_after is not None:
        statement = statement.where(Server.last_seen_at >= seen_after)

    if seen_before is not None:
        statement = statement.where(Server.last_seen_at <= seen_before)

    sort_columns = {
        "id": Server.id,
        "name": Server.name,
        "created_at": Server.created_at,
        "last_seen_at": Server.last_seen_at,
    }
    sort_column = sort_columns[sort_by]

    if order == "desc":
        statement = statement.order_by(
            sort_column.desc().nulls_last(),
            Server.id.desc(),
        )
    else:
        statement = statement.order_by(
            sort_column.asc().nulls_last(),
            Server.id.asc(),
        )

    statement = statement.offset(skip).limit(limit)

    result = await session.scalars(statement)
    servers = list(result.all())

    for server in servers:
        server.is_online = is_server_online(server, now)

    return servers


# Keep this route before /{server_id}
@router.get("/agent/verify")
async def verify_agent_token(
    agent_token: AgentToken = Depends(authenticate_agent),
) -> dict[str, int | str]:
    return {
        "status": "authenticated",
        "server_id": agent_token.server_id,
    }


@router.post(
    "/agent/heartbeat",
    response_model=HeartbeatResponse,
)
async def agent_heartbeat(
    agent_token: AgentToken = Depends(authenticate_agent),
    session: AsyncSession = Depends(get_db_session),
) -> HeartbeatResponse:
    server = await session.get(Server, agent_token.server_id)

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    now = datetime.now(UTC)

    server.is_online = True
    server.last_seen_at = now

    await session.commit()

    return HeartbeatResponse(
        status="ok",
        server_id=server.id,
        last_seen_at=now,
    )


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

    server.is_online = is_server_online(server, datetime.now(UTC))

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

    try:
        await session.commit()
        await session.refresh(server)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A server with this hostname already exists",
        ) from exc

    server.is_online = is_server_online(server, datetime.now(UTC))

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


@router.get("/{server_id}/tokens")
async def list_agent_tokens(
    server_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, int | datetime | None]]:
    server = await session.get(Server, server_id)

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    statement = (
        select(AgentToken)
        .where(AgentToken.server_id == server_id)
        .order_by(AgentToken.created_at.desc())
    )

    result = await session.scalars(statement)
    tokens = result.all()

    return [
        {
            "id": token.id,
            "server_id": token.server_id,
            "created_at": token.created_at,
            "revoked_at": token.revoked_at,
        }
        for token in tokens
    ]


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
