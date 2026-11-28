import re
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = b"x-request-id"
_REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{1,128}$")


class RequestIDMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        incoming_request_id = headers.get(REQUEST_ID_HEADER, b"").decode("latin-1")

        if _REQUEST_ID_PATTERN.fullmatch(incoming_request_id):
            request_id = incoming_request_id
        else:
            request_id = str(uuid.uuid4())

        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.append((REQUEST_ID_HEADER, request_id.encode("ascii")))
                message["headers"] = response_headers

            await send(message)

        await self.app(scope, receive, send_with_request_id)
