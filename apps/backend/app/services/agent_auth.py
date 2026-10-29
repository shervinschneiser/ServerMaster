from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.db.session import get_db_session
from app.models.agent_token import AgentToken
from app.services.agent_tokens import hash_agent_token

bearer_scheme = HTTPBearer()


async def authenticate_agent(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> AgentToken:
    token_hash = hash_agent_token(credentials.credentials)

    result = await session.execute(
        select(AgentToken).where(
            AgentToken.token_hash == token_hash,
            AgentToken.revoked_at.is_(None),
        )
    )
    agent_token = result.scalar_one_or_none()

    if agent_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked agent token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return agent_token
