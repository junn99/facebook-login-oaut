"""Facebook OAuth flow for Instagram Business API."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import requests

from .config import config
from .models import InstagramAccount


_STATE_TTL_SECONDS = 600
_STATE_FUTURE_SKEW_SECONDS = 60


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign_state_payload(payload_bytes: bytes) -> bytes:
    secret = config.FB_APP_SECRET.encode("utf-8")
    return hmac.new(secret, payload_bytes, hashlib.sha256).digest()


def generate_state() -> str:
    """Generate a signed stateless CSRF state token."""
    payload = {
        "iat": int(time.time()),
        "nonce": secrets.token_urlsafe(16),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = _sign_state_payload(payload_bytes)
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"


def validate_state(state: str) -> bool:
    """Validate a signed stateless CSRF state token."""
    try:
        if not state or "." not in state:
            return False

        payload_part, signature_part = state.split(".", 1)
        payload_bytes = _b64url_decode(payload_part)
        received_signature = _b64url_decode(signature_part)
        expected_signature = _sign_state_payload(payload_bytes)

        if not hmac.compare_digest(received_signature, expected_signature):
            return False

        payload = json.loads(payload_bytes.decode("utf-8"))
        iat = payload.get("iat")
        if not isinstance(iat, int):
            return False

        now = int(time.time())
        if now - iat > _STATE_TTL_SECONDS:
            return False
        if iat - now > _STATE_FUTURE_SKEW_SECONDS:
            return False

        return True
    except Exception:
        return False


def get_oauth_url(state: Optional[str] = None) -> str:
    """Generate Facebook OAuth authorization URL."""
    if state is None:
        state = generate_state()

    params = {
        "client_id": config.FB_APP_ID,
        "redirect_uri": config.OAUTH_REDIRECT_URI,
        "state": state,
        "scope": "instagram_basic,instagram_manage_insights,pages_show_list,pages_read_engagement",
        "response_type": "code",
    }
    return f"https://www.facebook.com/{config.GRAPH_API_VERSION}/dialog/oauth?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    """Exchange authorization code for short-lived access token."""
    url = f"{config.GRAPH_API_BASE_URL}/oauth/access_token"
    params = {
        "client_id": config.FB_APP_ID,
        "client_secret": config.FB_APP_SECRET,
        "redirect_uri": config.OAUTH_REDIRECT_URI,
        "code": code,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def get_long_lived_token(short_lived_token: str) -> dict:
    """Exchange short-lived token for long-lived user token (60 days)."""
    url = f"{config.GRAPH_API_BASE_URL}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": config.FB_APP_ID,
        "client_secret": config.FB_APP_SECRET,
        "fb_exchange_token": short_lived_token,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    # Calculate expiration (typically 60 days)
    expires_in = data.get("expires_in", 5184000)  # Default 60 days
    data["expires_at"] = datetime.utcnow() + timedelta(seconds=expires_in)

    return data


def refresh_long_lived_token(token: str) -> dict:
    """Refresh a long-lived token (extends expiration)."""
    url = f"{config.GRAPH_API_BASE_URL}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": config.FB_APP_ID,
        "client_secret": config.FB_APP_SECRET,
        "fb_exchange_token": token,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    expires_in = data.get("expires_in", 5184000)
    data["expires_at"] = datetime.utcnow() + timedelta(seconds=expires_in)

    return data


def get_user_pages(user_token: str) -> list[dict]:
    """Get Facebook Pages the user manages."""
    url = f"{config.GRAPH_API_BASE_URL}/me/accounts"
    params = {
        "access_token": user_token,
        "fields": "id,name,access_token,instagram_business_account",
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json().get("data", [])


def get_instagram_business_account(
    page_token: str, page_id: str
) -> Optional[InstagramAccount]:
    """Get Instagram Business Account linked to a Facebook Page."""
    url = f"{config.GRAPH_API_BASE_URL}/{page_id}"
    params = {
        "access_token": page_token,
        "fields": "instagram_business_account{id,username,name,profile_picture_url,followers_count,media_count}",
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    ig_account = data.get("instagram_business_account")
    if ig_account:
        return InstagramAccount(
            id=ig_account["id"],
            username=ig_account.get("username", ""),
            name=ig_account.get("name"),
            profile_picture_url=ig_account.get("profile_picture_url"),
            followers_count=ig_account.get("followers_count"),
            media_count=ig_account.get("media_count"),
        )
    return None


def complete_oauth_flow(code: str) -> dict:
    """Complete the full OAuth flow and return all necessary data."""
    # Step 1: Exchange code for short-lived token
    short_token_data = exchange_code_for_token(code)
    short_token = short_token_data["access_token"]

    # Step 2: Exchange for long-lived user token
    long_token_data = get_long_lived_token(short_token)
    user_token = long_token_data["access_token"]
    user_token_expires = long_token_data["expires_at"]

    # Step 3: Get user's Facebook Pages
    pages = get_user_pages(user_token)

    # Step 4: Find page with Instagram Business Account
    for page in pages:
        print(f"Page: {page.get('name')}, Keys: {list(page.keys())}, IG: {page.get('instagram_business_account')}")
        if "instagram_business_account" in page:
            page_id = page["id"]
            page_token = page["access_token"]

            # Step 5: Get Instagram account details
            ig_account = get_instagram_business_account(page_token, page_id)

            if ig_account:
                return {
                    "success": True,
                    "user_token": user_token,
                    "user_token_expires": user_token_expires,
                    "page_id": page_id,
                    "page_token": page_token,
                    "instagram_account": ig_account,
                }

    return {
    "success": False,
    "error": "No Instagram Business Account found...",
    "pages_debug": [{"name": p.get("name"), "has_ig": "instagram_business_account" in p} for p in pages],  # 추가
}
