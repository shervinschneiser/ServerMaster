import hashlib
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_token import AgentToken


def generate_agent_token() -> str:
    return secrets.token_urlsafe(32)


def hash_agent_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def create_agent_token(
    session: AsyncSession,
    server_id: int,
) -> tuple[AgentToken, str]:
    raw_token = generate_agent_token()

    agent_token = AgentToken(
        server_id=server_id,
        token_hash=hash_agent_token(raw_token),
    )

    session.add(agent_token)
    await session.flush()

    return agent_token, raw_token
