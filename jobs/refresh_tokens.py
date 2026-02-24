"""Scheduled job for refreshing expiring tokens."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import init_db, get_expiring_tokens, save_token
from src.oauth import get_user_pages, refresh_long_lived_token


def run_token_refresh(days_before_expiry: int = 7):
    """
    Refresh tokens that will expire within the specified days.

    Args:
        days_before_expiry: Refresh tokens expiring within this many days
    """
    print(f"Checking for tokens expiring within {days_before_expiry} days...")

    # Ensure database is initialized
    init_db()

    # Get expiring tokens
    expiring = get_expiring_tokens(days_before_expiry)

    if not expiring:
        print("No tokens need refreshing.")
        return {"refreshed": 0, "failed": 0, "errors": []}

    results = {"refreshed": 0, "failed": 0, "errors": []}

    for user, token in expiring:
        print(f"Refreshing token for {user.instagram_username}...")

        try:
            # Refresh the token
            new_token_data = refresh_long_lived_token(token.access_token)

            # Save the new token
            save_token(
                user_id=user.id,
                token_type="user",
                access_token=new_token_data["access_token"],
                expires_at=new_token_data["expires_at"],
            )

            print(f"  ✓ Token refreshed, expires: {new_token_data['expires_at']}")

            # Refresh the page token for the same page currently linked to this user.
            try:
                pages = get_user_pages(new_token_data["access_token"])
                matching_page = next(
                    (
                        page
                        for page in pages
                        if page.get("id") == user.facebook_page_id
                        and isinstance(page.get("access_token"), str)
                    ),
                    None,
                )

                if matching_page and user.id is not None:
                    save_token(
                        user_id=user.id,
                        token_type="page",
                        access_token=matching_page["access_token"],
                        expires_at=None,
                    )
                    print(f"  ✓ Page token synced for page {user.facebook_page_id}")
                else:
                    print(
                        "  ! Page token sync skipped: "
                        f"linked page {user.facebook_page_id} not found."
                    )
            except Exception as page_error:
                print(f"  ! Page token sync failed: {page_error}")

            results["refreshed"] += 1

        except Exception as e:
            error_msg = f"Failed to refresh token for {user.instagram_username}: {e}"
            print(f"  ✗ {error_msg}")
            results["failed"] += 1
            results["errors"].append(error_msg)

    print(f"\n=== Refresh Summary ===")
    print(f"Refreshed: {results['refreshed']}")
    print(f"Failed: {results['failed']}")

    return results


if __name__ == "__main__":
    run_token_refresh()
