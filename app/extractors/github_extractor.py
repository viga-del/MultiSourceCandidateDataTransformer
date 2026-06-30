import httpx
import os
from app.utils.logger import get_logger
from typing import Dict, Any

logger = get_logger(__name__)

GITHUB_API_BASE = "https://api.github.com"


def extract_from_github(username: str) -> Dict[str, Any]:
    """
    Fetch a GitHub user's profile and aggregate programming languages across their repos.
    Uses GITHUB_TOKEN env variable for authentication (optional but raises rate limit from 60 to 5000/hr).
    """
    logger.info(f"Fetching GitHub profile: {username}")

    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    result = {}
    try:
        with httpx.Client(headers=headers, timeout=10.0) as client:
            response = client.get(f"{GITHUB_API_BASE}/users/{username}")
            response.raise_for_status()
            profile = response.json()

            result = {
                "login":     profile.get("login", ""),
                "name":      profile.get("name", ""),
                "bio":       profile.get("bio", ""),
                "location":  profile.get("location", ""),
                "email":     profile.get("email", ""),
                "html_url":  profile.get("html_url", ""),
                "languages": []
            }

            repos_response = client.get(f"{GITHUB_API_BASE}/users/{username}/repos?per_page=100")
            repos_response.raise_for_status()
            repos = repos_response.json()

            # Accumulate byte counts per language across all repos, then sort most-used first
            lang_counts: Dict[str, int] = {}
            for repo in repos[:20]:
                try:
                    langs_resp = client.get(f"{GITHUB_API_BASE}/repos/{username}/{repo.get('name', '')}/languages")
                    if langs_resp.status_code == 200:
                        for lang, count in langs_resp.json().items():
                            lang_counts[lang] = lang_counts.get(lang, 0) + count
                except Exception:
                    continue

            result["languages"] = [lang for lang, _ in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)]
            logger.info(f"GitHub extraction complete. Languages: {result['languages']}")

    except httpx.HTTPStatusError as e:
        logger.error(f"GitHub API error for {username}: {e.response.status_code}")
    except httpx.ConnectError:
        logger.error("Could not connect to GitHub API.")
    except Exception as e:
        logger.error(f"Failed GitHub extraction for {username}: {e}")

    return result
