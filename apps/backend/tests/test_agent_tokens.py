import hashlib

from app.services.agent_tokens import (
    generate_agent_token,
    hash_agent_token,
)


def test_generate_agent_token_returns_unique_tokens() -> None:
    first_token = generate_agent_token()
    second_token = generate_agent_token()

    assert first_token != second_token
    assert len(first_token) >= 40


def test_hash_agent_token_returns_sha256_hex_digest() -> None:
    token = "test-agent-token"

    result = hash_agent_token(token)

    assert result == hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert len(result) == 64
    assert result != token
