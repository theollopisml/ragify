import re
import secrets

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.config import settings

router = APIRouter()

_state_dict: dict[str, str] = {}


def _create_state(shop: str) -> str:
    """Génère un state aléatoire pour la protection CSRF et le renvoie."""
    global _state_dict
    state = secrets.token_urlsafe(32)
    _state_dict[state] = shop
    return state


@router.get("/auth")
async def auth(shop: str):
    """Endpoint d'authentification — vérifie que le shop est autorisé."""
    # Validate shop format
    rule = "^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$"
    if not re.match(rule, shop):
        return {"status": "error", "message": "Invalid shop format"}
    state = _create_state(shop)  # Generate a random state for CSRF protection
    return RedirectResponse(
        url=f"https://{shop}/admin/oauth/authorize?client_id={settings.shopify_client_id}&scope=read_products,read_content=redirect_uri=http://localhost:8000/auth/callback&state={state}",
        status_code=302,
    )
