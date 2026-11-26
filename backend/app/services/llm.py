from openai import AsyncOpenAI

from app.config import settings

_client: AsyncOpenAI | None = None


def client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=settings.freellmapi_base_url,
            api_key=settings.freellmapi_api_key or "dummy",
            timeout=4.0,
            max_retries=0,
        )
    return _client


async def chat_completion(system: str, user: str) -> str:
    resp = await client().chat.completions.create(
        model=settings.freellmapi_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()
