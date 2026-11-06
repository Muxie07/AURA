import uuid

from fastapi import APIRouter
from jose import jwt
from mcp.server.sse import SseServerTransport

from app.config.settings import get_settings
from app.tools.mcp.server import mcp_org_id, mcp_permissions, mcp_server

mcp_router = APIRouter()

transport = SseServerTransport(endpoint="/api/v1/mcp/messages")


async def auth_middleware(app, scope, receive, send):
    headers = dict(scope.get("headers", []))
    auth_header = headers.get(b"authorization", b"").decode("utf-8")

    async def send_error(status: int, detail: bytes):
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": detail})

    if not auth_header.startswith("Bearer "):
        return await send_error(401, b"Unauthorized")

    token = auth_header.split(" ")[1]
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.aura_secret_key.get_secret_value(),
            algorithms=["HS256"],
            options={"verify_aud": False, "verify_iss": False},
        )
        if "org_id" not in payload:
            return await send_error(401, b"Invalid token claims")
        org_id = uuid.UUID(payload["org_id"])
    except Exception:
        return await send_error(401, b"Invalid token")

    org_id_bytes = headers.get(b"x-organization-id")
    if org_id_bytes:
        try:
            header_org_id = uuid.UUID(org_id_bytes.decode("utf-8"))
            if org_id != header_org_id:
                return await send_error(403, b"Spoofed organization header")
        except ValueError:
            pass

    perms = payload.get("permissions", ["tools:read"])
    mcp_org_id.set(org_id)
    mcp_permissions.set(perms)

    await app(scope, receive, send)


async def sse_handler(scope, receive, send):
    async with transport.connect_sse(scope, receive, send) as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())


async def post_handler(scope, receive, send):
    await transport.handle_post_message(scope, receive, send)


async def asgi_sse(scope, receive, send):
    if scope["method"] == "GET":
        await auth_middleware(sse_handler, scope, receive, send)
    elif scope["method"] == "POST":
        await auth_middleware(post_handler, scope, receive, send)
    else:
        await send({"type": "http.response.start", "status": 405})
        await send({"type": "http.response.body", "body": b"Method Not Allowed"})


# Removed Mount from here, now mounted in mcp_main.py


async def start_mcp_server():
    pass
