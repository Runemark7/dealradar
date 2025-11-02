"""
Blocket API client
Handles HTTP communication and authentication with Blocket's API
"""
import httpx
from typing import Optional

from ..config import settings


# Global token cache
_auth_token: Optional[str] = None


async def get_auth_token() -> Optional[str]:
    """
    Get authentication token from Blocket's public endpoint.
    Token is cached for reuse.

    Returns:
        Bearer token for API authentication, or None if failed
    """
    global _auth_token

    if _auth_token:
        return _auth_token

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SITE_URL}/api/adout-api-route/refresh-token-and-validate-session",
                headers={"User-Agent": settings.USER_AGENT},
                timeout=settings.API_TIMEOUT_SECONDS
            )

            if response.status_code == 200:
                data = response.json()
                _auth_token = data.get('bearerToken')
                if _auth_token:
                    print(f"✓ Retrieved authentication token")
                    return _auth_token
                else:
                    print(f"ERROR: Token not found in response. Response data: {data}")
                    return None
            else:
                print(f"ERROR: Failed to get token (HTTP {response.status_code})")
                return None

    except Exception as e:
        print(f"ERROR: Failed to fetch auth token: {e}")
        return None


def get_api_headers(token: str) -> dict:
    """
    Get standard API headers for Blocket requests

    Args:
        token: Bearer token for authentication

    Returns:
        Dictionary of HTTP headers
    """
    return {
        "User-Agent": settings.USER_AGENT,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
