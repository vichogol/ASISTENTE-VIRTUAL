import httpx

from app.config import settings


async def verify_turnstile(token: str, ip: str | None = None) -> bool:
    if not settings.turnstile_secret_key:
        return True
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": settings.turnstile_secret_key,
                "response": token,
                "remoteip": ip or "",
            },
        )
    return bool(r.json().get("success", False))
