"""WordPress REST API utilities for SEO Agency 2026.

Merged from:
- geo-transformer-skill/scripts/wp_utils.py (fetch/update posts)
- wp-tech-fixer/scripts/wp_tech_utils.py (redirects, orphans, IndexNow)

This is the single source of truth for all WordPress interactions.
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# CREDENTIALS
# =============================================================================

def get_credentials() -> Tuple[str, str, str]:
    """Load WordPress credentials from environment variables.
    
    Expected env vars: WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD
    
    Returns:
        Tuple of (site_url, username, app_password)
    
    Raises:
        ValueError: If required environment variables are missing
    """
    site_url = os.getenv("WP_SITE_URL")
    username = os.getenv("WP_USERNAME")
    app_password = os.getenv("WP_APP_PASSWORD") or os.getenv("WP_APPLICATION_PASSWORD")
    
    missing = []
    if not site_url:
        missing.append("WP_SITE_URL")
    if not username:
        missing.append("WP_USERNAME")
    if not app_password:
        missing.append("WP_APP_PASSWORD")
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    return site_url, username, app_password


def get_auth_headers(username: str, app_password: str) -> Dict[str, str]:
    """Generate authentication headers for WordPress REST API.
    
    Args:
        username: WordPress username
        app_password: WordPress application password
        
    Returns:
        Dict with Authorization header
    """
    credentials = f"{username}:{app_password}"
    token = base64.b64encode(credentials.encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json"
    }


# =============================================================================
# POST OPERATIONS
# =============================================================================

def fetch_post(
    site_url: str, 
    post_id: int, 
    username: str, 
    app_password: str
) -> Dict[str, Any]:
    """Fetch a specific post from WordPress.
    
    Args:
        site_url: WordPress site URL (e.g., https://example.com)
        post_id: The post ID to fetch
        username: WordPress username
        app_password: WordPress application password
    
    Returns:
        Post data as dictionary
    
    Raises:
        requests.HTTPError: If the API request fails
        ValueError: If post not found or access denied
    """
    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    
    response = requests.get(url, auth=(username, app_password), timeout=30)
    
    if response.status_code == 404:
        raise ValueError(f"Post {post_id} not found")
    if response.status_code == 401:
        raise ValueError("Authentication failed - check username and app password")
    if response.status_code == 403:
        raise ValueError("Access denied - insufficient permissions")
    
    response.raise_for_status()
    return response.json()


def update_post(
    site_url: str,
    post_id: int,
    username: str,
    app_password: str,
    updated_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Update a WordPress post with new content.
    
    Args:
        site_url: WordPress site URL
        post_id: The post ID to update
        username: WordPress username
        app_password: WordPress application password
        updated_data: Dictionary with fields to update
    
    Returns:
        Updated post data
    
    Raises:
        requests.HTTPError: If the API request fails
        ValueError: If update fails due to permissions or validation
    """
    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    
    response = requests.post(
        url,
        json=updated_data,
        auth=(username, app_password),
        timeout=30
    )
    
    if response.status_code == 401:
        raise ValueError("Authentication failed - check username and app password")
    if response.status_code == 403:
        raise ValueError("Access denied - insufficient permissions to edit this post")
    
    response.raise_for_status()
    return response.json()


def fetch_post_by_slug(
    site_url: str, 
    slug: str, 
    username: str, 
    app_password: str
) -> Dict[str, Any]:
    """Fetch a post by its URL slug.
    
    Args:
        site_url: WordPress site URL
        slug: Post slug (e.g., "my-blog-post")
        username: WordPress username
        app_password: WordPress application password
    
    Returns:
        Post data as dictionary
    
    Raises:
        ValueError: If no post found with that slug
    """
    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts"
    
    response = requests.get(
        url,
        params={"slug": slug},
        auth=(username, app_password),
        timeout=30
    )
    response.raise_for_status()
    
    posts = response.json()
    if not posts:
        raise ValueError(f"No post found with slug: {slug}")
    
    return posts[0]


def fetch_posts_by_category(
    site_url: str,
    category_id: int,
    username: str,
    app_password: str,
    per_page: int = 10,
    orderby: str = "date"
) -> List[Dict[str, Any]]:
    """Fetch posts in a specific category.
    
    Args:
        site_url: WordPress site URL
        category_id: Category ID to filter by
        username: WordPress username
        app_password: WordPress application password
        per_page: Number of posts to return
        orderby: Order by field (date, title, etc.)
    
    Returns:
        List of post data dictionaries
    """
    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts"
    
    response = requests.get(
        url,
        params={
            "categories": category_id,
            "per_page": per_page,
            "orderby": orderby
        },
        auth=(username, app_password),
        timeout=30
    )
    response.raise_for_status()
    return response.json()


# =============================================================================
# REDIRECT OPERATIONS (Requires Redirection plugin)
# =============================================================================

def create_redirect(
    site_url: str,
    from_url: str,
    to_url: str,
    username: str,
    app_password: str,
    redirect_type: int = 301
) -> Dict[str, Any]:
    """Create a redirect using the Redirection plugin API.
    
    Args:
        site_url: WordPress site URL
        from_url: Source URL path (e.g., /old-page)
        to_url: Destination URL (e.g., /new-page or full URL)
        username: WordPress username
        app_password: WordPress application password
        redirect_type: HTTP status code (301, 302, etc.)
    
    Returns:
        Redirect data from API
        
    Raises:
        ValueError: If Redirection plugin not installed or accessible
    """
    # Redirection plugin REST API endpoint
    url = f"{site_url.rstrip('/')}/wp-json/redirection/v1/redirect"
    
    payload = {
        "url": from_url,
        "action_data": {"url": to_url},
        "action_type": "url",
        "action_code": redirect_type,
        "match_type": "url",
        "group_id": 1  # Default group
    }
    
    response = requests.post(
        url,
        json=payload,
        auth=(username, app_password),
        timeout=30
    )
    
    if response.status_code == 404:
        raise ValueError(
            "Redirection plugin API not found. "
            "Ensure the Redirection plugin is installed and REST API is enabled."
        )
    
    response.raise_for_status()
    return response.json()


def find_redirect_target(
    site_url: str,
    broken_url: str,
    username: str,
    app_password: str
) -> Optional[str]:
    """Find a suitable redirect target for a broken URL using fuzzy matching.
    
    Args:
        site_url: WordPress site URL
        broken_url: The broken URL path
        username: WordPress username
        app_password: WordPress application password
    
    Returns:
        Best matching URL or None if no good match found
    """
    # Extract slug from broken URL
    path = broken_url.strip('/').split('/')[-1]
    
    # Search for posts with similar titles
    search_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts"
    
    response = requests.get(
        search_url,
        params={"search": path.replace('-', ' '), "per_page": 5},
        auth=(username, app_password),
        timeout=30
    )
    
    if response.status_code == 200:
        posts = response.json()
        if posts:
            # Return the most relevant match
            return posts[0].get("link")
    
    return None


# =============================================================================
# INDEXNOW PROTOCOL
# =============================================================================

def submit_indexnow(
    urls: List[str],
    site_url: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Submit URLs to IndexNow protocol for fast search engine indexing.
    
    Args:
        urls: List of URLs to submit
        site_url: Your site URL (for key location)
        api_key: IndexNow API key (auto-generated if not provided)
    
    Returns:
        Response data with submission status
    """
    if not api_key:
        api_key = os.getenv("INDEXNOW_API_KEY", "seo-agency-2026-key")
    
    # IndexNow API endpoint (using Bing's endpoint)
    indexnow_url = "https://api.indexnow.org/IndexNow"
    
    payload = {
        "host": site_url.replace("https://", "").replace("http://", "").rstrip("/"),
        "key": api_key,
        "keyLocation": f"{site_url.rstrip('/')}/{api_key}.txt",
        "urlList": urls
    }
    
    response = requests.post(
        indexnow_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    
    return {
        "status_code": response.status_code,
        "success": response.status_code in [200, 202],
        "urls_submitted": len(urls),
        "message": "URLs submitted to IndexNow" if response.status_code in [200, 202] else response.text
    }


# =============================================================================
# BACKUP UTILITIES
# =============================================================================

def create_backup(
    data: Dict[str, Any],
    backup_dir: str = "backups",
    prefix: str = "backup"
) -> str:
    """Create atomic backup of data before making changes.
    
    Args:
        data: Data to backup (usually post content)
        backup_dir: Directory to store backups
        prefix: Filename prefix
    
    Returns:
        Path to backup file
    """
    backup_path = Path(backup_dir)
    backup_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.json"
    filepath = backup_path / filename
    
    with open(filepath, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "data": data
        }, f, indent=2)
    
    return str(filepath)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def quick_fetch(post_id: int) -> Dict[str, Any]:
    """Fetch a post using environment credentials.
    
    Args:
        post_id: WordPress post ID
        
    Returns:
        Post data dictionary
    """
    site_url, username, app_password = get_credentials()
    return fetch_post(site_url, post_id, username, app_password)


def quick_update(post_id: int, content: str) -> Dict[str, Any]:
    """Update a post's content using environment credentials.
    
    Args:
        post_id: WordPress post ID
        content: New HTML content
        
    Returns:
        Updated post data
    """
    site_url, username, app_password = get_credentials()
    return update_post(
        site_url, post_id, username, app_password,
        {"content": content}
    )
