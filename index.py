import asyncio
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
MCP_API_KEY = os.getenv("MCP_API_KEY", "")

mcp = FastMCP("email-mcp")


def _send_html_email(to_email: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)


@mcp.tool
async def send_email(to_email: str, subject: str, body: str) -> str:
    """Send an HTML email to a recipient via Gmail SMTP."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        return "Error: GMAIL_USER or GMAIL_APP_PASSWORD not configured"

    await asyncio.to_thread(_send_html_email, to_email, subject, body)
    return f"Email sent to {to_email}"


class MCPAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        if not MCP_API_KEY:
            return JSONResponse(
                {"error": "MCP_API_KEY not configured"},
                status_code=500,
            )

        if request.headers.get("x-api-key") != MCP_API_KEY:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        return await call_next(request)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "healthy", "service": "email-mcp"})


app = mcp.http_app(
    stateless_http=True,
    middleware=[Middleware(MCPAuthMiddleware)],
)
