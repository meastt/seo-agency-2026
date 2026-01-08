"""Technical SEO Link Fixer - Real implementations for 404s, orphans, and redirect chains.

Adapted from wp-tech-fixer/scripts/wp_tech_utils.py with proper integration
to core/wp_api.py and validation layer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.wp_api import (
    get_credentials,
    fetch_post,
    update_post,
    fetch_posts_by_category,
    create_backup,
    submit_indexnow
)


@dataclass
class FixResult:
    """Result of a technical fix operation."""
    success: bool
    fix_type: str  # "broken_link", "orphan_page", "redirect_chain"
    source_url: str
    target_url: str = ""
    method: str = ""  # "redirection_plugin", "htaccess", "post_update"
    error: str = ""
    backup_path: str = ""
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "fix_type": self.fix_type,
            "source_url": self.source_url,
            "target_url": self.target_url,
            "method": self.method,
            "error": self.error,
            "backup_path": self.backup_path,
            "details": self.details or {}
        }


class TechnicalFixer:
    """Fixes technical SEO issues on WordPress sites.
    
    This class contains REAL implementations that actually modify
    WordPress content - not simulations.
    """
    
    def __init__(self, backup_dir: str = "backups"):
        """Initialize the fixer.
        
        Args:
            backup_dir: Directory for atomic backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self._load_credentials()
        
    def _load_credentials(self):
        """Load WordPress credentials from environment."""
        self.site_url, self.username, self.app_password = get_credentials()
        self.api_base = f"{self.site_url.rstrip('/')}/wp-json/wp/v2"
        
    def _get_auth(self) -> tuple:
        """Get auth tuple for requests."""
        return (self.username, self.app_password)
    
    # =========================================================================
    # BROKEN LINK FIXES (404s)
    # =========================================================================
    
    def fix_broken_link(
        self, 
        broken_url: str, 
        redirect_target: Optional[str] = None
    ) -> FixResult:
        """Create 301 redirect for a broken link.
        
        This is a REAL implementation that calls the Redirection plugin API.
        
        Args:
            broken_url: The broken URL path (e.g., /old-page)
            redirect_target: Where to redirect. If None, will try to find a match.
            
        Returns:
            FixResult with success status and details
        """
        # Auto-find target if not provided
        if not redirect_target:
            redirect_target = self._find_redirect_target(broken_url)
            
        if not redirect_target:
            return FixResult(
                success=False,
                fix_type="broken_link",
                source_url=broken_url,
                error="Could not find suitable redirect target"
            )
        
        # Create backup before any changes
        backup_data = {
            "action": "create_redirect",
            "broken_url": broken_url,
            "redirect_target": redirect_target,
            "timestamp": datetime.now().isoformat()
        }
        backup_path = create_backup(backup_data, str(self.backup_dir), "redirect")
        
        # Try Redirection plugin API first
        redirection_url = f"{self.site_url.rstrip('/')}/wp-json/redirection/v1/redirect"
        
        redirect_data = {
            "url": broken_url,
            "match_type": "url",
            "action_type": "url",
            "action_code": 301,
            "action_data": {"url": redirect_target},
            "group_id": 1  # Default group
        }
        
        try:
            response = requests.post(
                redirection_url,
                json=redirect_data,
                auth=self._get_auth(),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                return FixResult(
                    success=True,
                    fix_type="broken_link",
                    source_url=broken_url,
                    target_url=redirect_target,
                    method="redirection_plugin",
                    backup_path=backup_path,
                    details={"redirect_id": response.json().get("id")}
                )
            elif response.status_code == 404:
                # Redirection plugin not installed - provide .htaccess fallback
                htaccess_rule = f"Redirect 301 {broken_url} {redirect_target}"
                return FixResult(
                    success=False,
                    fix_type="broken_link",
                    source_url=broken_url,
                    target_url=redirect_target,
                    method="htaccess_required",
                    error="Redirection plugin not installed",
                    backup_path=backup_path,
                    details={"htaccess_rule": htaccess_rule}
                )
            else:
                return FixResult(
                    success=False,
                    fix_type="broken_link",
                    source_url=broken_url,
                    error=f"API returned {response.status_code}: {response.text}",
                    backup_path=backup_path
                )
                
        except requests.RequestException as e:
            return FixResult(
                success=False,
                fix_type="broken_link",
                source_url=broken_url,
                error=str(e),
                backup_path=backup_path
            )
    
    def _find_redirect_target(self, broken_url: str) -> Optional[str]:
        """Find a suitable redirect target using fuzzy search.
        
        Args:
            broken_url: The broken URL path
            
        Returns:
            Best matching URL or None
        """
        # Extract search term from URL
        url_parts = broken_url.strip('/').split('/')
        search_term = url_parts[-1].replace('-', ' ')
        
        # Search WordPress for similar content
        search_url = f"{self.api_base}/posts"
        
        try:
            response = requests.get(
                search_url,
                params={"search": search_term, "per_page": 5},
                auth=self._get_auth(),
                timeout=30
            )
            
            if response.status_code == 200:
                posts = response.json()
                if posts:
                    return posts[0].get("link")
                    
        except requests.RequestException:
            pass
        
        return None
    
    # =========================================================================
    # ORPHAN PAGE FIXES
    # =========================================================================
    
    def fix_orphan_page(
        self, 
        post_id: int,
        parent_post_id: Optional[int] = None
    ) -> FixResult:
        """Link an orphan page to a relevant parent post.
        
        This is a REAL implementation that updates WordPress post content.
        
        Args:
            post_id: The orphan page's post ID
            parent_post_id: Specific parent to link from. If None, finds best match.
            
        Returns:
            FixResult with success status and details
        """
        try:
            # Get the orphan post
            orphan_post = fetch_post(
                self.site_url, post_id, self.username, self.app_password
            )
            orphan_title = orphan_post.get("title", {}).get("rendered", "")
            orphan_url = orphan_post.get("link", "")
            orphan_categories = orphan_post.get("categories", [])
            
        except ValueError as e:
            return FixResult(
                success=False,
                fix_type="orphan_page",
                source_url=str(post_id),
                error=str(e)
            )
        
        # Find parent post if not specified
        if parent_post_id is None:
            parent_post_id = self._find_parent_post(orphan_categories)
            
        if parent_post_id is None:
            return FixResult(
                success=False,
                fix_type="orphan_page",
                source_url=orphan_url,
                error="Could not find suitable parent post"
            )
        
        # Get parent post
        try:
            parent_post = fetch_post(
                self.site_url, parent_post_id, self.username, self.app_password
            )
            parent_content = parent_post.get("content", {}).get("rendered", "")
            parent_url = parent_post.get("link", "")
            
        except ValueError as e:
            return FixResult(
                success=False,
                fix_type="orphan_page",
                source_url=orphan_url,
                error=f"Parent post error: {e}"
            )
        
        # Create backup before modifying
        backup_data = {
            "action": "add_internal_link",
            "parent_post_id": parent_post_id,
            "original_content": parent_content,
            "orphan_post_id": post_id,
            "timestamp": datetime.now().isoformat()
        }
        backup_path = create_backup(backup_data, str(self.backup_dir), "orphan_fix")
        
        # Create contextual link HTML
        link_html = f'''
<p><strong>Related:</strong> <a href="{orphan_url}">{orphan_title}</a></p>
'''
        
        # Add link to end of parent content
        updated_content = parent_content.strip() + "\n" + link_html
        
        # Update parent post
        try:
            update_post(
                self.site_url,
                parent_post_id,
                self.username,
                self.app_password,
                {"content": updated_content}
            )
            
            return FixResult(
                success=True,
                fix_type="orphan_page",
                source_url=orphan_url,
                target_url=parent_url,
                method="post_update",
                backup_path=backup_path,
                details={
                    "orphan_post_id": post_id,
                    "parent_post_id": parent_post_id,
                    "link_added": orphan_title
                }
            )
            
        except ValueError as e:
            return FixResult(
                success=False,
                fix_type="orphan_page",
                source_url=orphan_url,
                error=str(e),
                backup_path=backup_path
            )
    
    def _find_parent_post(self, categories: List[int]) -> Optional[int]:
        """Find a high-traffic parent post in the same category.
        
        Args:
            categories: List of category IDs from orphan post
            
        Returns:
            Post ID of best parent or None
        """
        if not categories:
            return None
        
        # Try to find popular post in first category
        category_id = categories[0]
        
        try:
            posts = fetch_posts_by_category(
                self.site_url,
                category_id,
                self.username,
                self.app_password,
                per_page=5,
                orderby="date"  # Could use comment_count if supported
            )
            
            if posts:
                return posts[0].get("id")
                
        except Exception:
            pass
        
        return None
    
    # =========================================================================
    # REDIRECT CHAIN FIXES
    # =========================================================================
    
    def flatten_redirect_chain(
        self,
        start_url: str,
        final_url: str
    ) -> FixResult:
        """Flatten a redirect chain (A→B→C becomes A→C).
        
        This is a REAL implementation that updates Redirection plugin rules.
        
        Args:
            start_url: The initial URL in the chain
            final_url: The final destination URL
            
        Returns:
            FixResult with success status and details
        """
        # Create backup
        backup_data = {
            "action": "flatten_chain",
            "start_url": start_url,
            "final_url": final_url,
            "timestamp": datetime.now().isoformat()
        }
        backup_path = create_backup(backup_data, str(self.backup_dir), "chain_fix")
        
        # Get redirects from Redirection plugin
        redirection_url = f"{self.site_url.rstrip('/')}/wp-json/redirection/v1/redirect"
        
        try:
            response = requests.get(
                redirection_url,
                auth=self._get_auth(),
                timeout=30
            )
            
            if response.status_code != 200:
                return FixResult(
                    success=False,
                    fix_type="redirect_chain",
                    source_url=start_url,
                    error=f"Could not fetch redirects: {response.status_code}",
                    backup_path=backup_path
                )
            
            # Handle the response structure
            data = response.json()
            redirects = data.get("items", data) if isinstance(data, dict) else data
            
            # Find the redirect that matches start_url
            for redirect in redirects:
                if redirect.get("url") == start_url:
                    redirect_id = redirect.get("id")
                    
                    # Update to point directly to final URL
                    update_response = requests.post(
                        f"{redirection_url}/{redirect_id}",
                        json={"action_data": {"url": final_url}},
                        auth=self._get_auth(),
                        timeout=30
                    )
                    
                    if update_response.status_code in [200, 201]:
                        return FixResult(
                            success=True,
                            fix_type="redirect_chain",
                            source_url=start_url,
                            target_url=final_url,
                            method="redirection_plugin",
                            backup_path=backup_path,
                            details={"redirect_id": redirect_id}
                        )
                    else:
                        return FixResult(
                            success=False,
                            fix_type="redirect_chain",
                            source_url=start_url,
                            error=f"Update failed: {update_response.status_code}",
                            backup_path=backup_path
                        )
            
            # Redirect not found - provide manual instruction
            return FixResult(
                success=False,
                fix_type="redirect_chain",
                source_url=start_url,
                target_url=final_url,
                method="htaccess_required",
                error="Redirect rule not found in Redirection plugin",
                backup_path=backup_path,
                details={"htaccess_rule": f"Redirect 301 {start_url} {final_url}"}
            )
            
        except requests.RequestException as e:
            return FixResult(
                success=False,
                fix_type="redirect_chain",
                source_url=start_url,
                error=str(e),
                backup_path=backup_path
            )
    
    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================
    
    def fix_batch(
        self,
        issues: List[Dict[str, Any]],
        notify_indexnow: bool = True
    ) -> List[FixResult]:
        """Fix a batch of technical issues.
        
        Args:
            issues: List of issue dicts with 'type' and relevant fields
            notify_indexnow: Whether to ping search engines after fixes
            
        Returns:
            List of FixResult objects
        """
        results = []
        fixed_urls = []
        
        for issue in issues:
            issue_type = issue.get("type")
            
            if issue_type == "broken_link":
                result = self.fix_broken_link(
                    issue.get("url"),
                    issue.get("redirect_target")
                )
            elif issue_type == "orphan_page":
                result = self.fix_orphan_page(
                    issue.get("post_id"),
                    issue.get("parent_post_id")
                )
            elif issue_type == "redirect_chain":
                result = self.flatten_redirect_chain(
                    issue.get("start_url"),
                    issue.get("final_url")
                )
            else:
                result = FixResult(
                    success=False,
                    fix_type="unknown",
                    source_url=str(issue),
                    error=f"Unknown issue type: {issue_type}"
                )
            
            results.append(result)
            
            if result.success and result.target_url:
                fixed_urls.append(result.target_url)
        
        # Notify search engines of fixes
        if notify_indexnow and fixed_urls:
            submit_indexnow(fixed_urls, self.site_url)
        
        return results


# Convenience function
def create_fixer() -> TechnicalFixer:
    """Create a TechnicalFixer with default settings."""
    return TechnicalFixer()
