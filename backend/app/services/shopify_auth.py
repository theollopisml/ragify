import time

import httpx

from app.config import settings


class ShopifyAuth:
    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expires_at: float = 0

    async def get_access_token(self) -> str:
        """Get a valid Shopify access token, refreshing if expired."""
        current_time = time.time()

        # Return cached token if still valid (with a 5-minute buffer)
        if self._token is not None and current_time < self._token_expires_at - 300:
            return self._token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=f"https://{settings.shopify_store_url}/admin/oauth/access_token",
                data={
                    "client_id": settings.shopify_client_id,
                    "client_secret": settings.shopify_app_secret,
                    "grant_type": "client_credentials",
                },
            )
            response.raise_for_status()  # raises httpx.HTTPStatusError on 4xx/5xx
            data = response.json()

        access_token = data.get("access_token", "")
        expires_in = data.get("expires_in", 86400)  # Default to 24h if not provided

        if not access_token:
            raise ValueError("Empty access token received from Shopify")

        self._token = access_token
        self._token_expires_at = current_time + expires_in
        return access_token


shopify_auth = ShopifyAuth()
