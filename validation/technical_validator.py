"""Technical Validator - Verify that technical fixes actually worked.

Unlike the old QC that just read log files, this validator
actually hits real URLs to confirm fixes are in place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    check_type: str  # "redirect", "internal_link", "chain"
    success: bool
    source_url: str
    expected_target: str = ""
    actual_target: str = ""
    error: str = ""
    
    
@dataclass
class ValidationReport:
    """Complete validation report."""
    total_checks: int
    passed: int
    failed: int
    results: List[ValidationResult]
    
    @property
    def success_rate(self) -> float:
        return (self.passed / self.total_checks * 100) if self.total_checks > 0 else 0


class TechnicalValidator:
    """Validates technical SEO fixes by hitting real URLs.
    
    This is NOT a log file reader - it makes actual HTTP requests
    to verify that fixes are working in production.
    """
    
    def __init__(self, timeout: int = 10):
        """Initialize validator.
        
        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        # Don't follow redirects automatically so we can inspect them
        self.session.max_redirects = 0
        
    def verify_redirect(
        self, 
        from_url: str, 
        expected_to_url: str
    ) -> ValidationResult:
        """Verify a redirect is working.
        
        Makes HTTP request to from_url and checks that:
        1. Response is 301/302
        2. Location header points to expected_to_url
        
        Args:
            from_url: The source URL that should redirect
            expected_to_url: Where it should redirect to
            
        Returns:
            ValidationResult with pass/fail status
        """
        try:
            response = self.session.get(
                from_url,
                allow_redirects=False,
                timeout=self.timeout
            )
            
            # Check for redirect status
            if response.status_code not in [301, 302, 303, 307, 308]:
                return ValidationResult(
                    check_type="redirect",
                    success=False,
                    source_url=from_url,
                    expected_target=expected_to_url,
                    error=f"Not a redirect: HTTP {response.status_code}"
                )
            
            # Get actual redirect target
            actual_target = response.headers.get("Location", "")
            
            # Handle relative URLs
            if actual_target and not actual_target.startswith("http"):
                actual_target = urljoin(from_url, actual_target)
            
            # Normalize and compare
            expected_normalized = expected_to_url.rstrip("/")
            actual_normalized = actual_target.rstrip("/")
            
            if expected_normalized == actual_normalized:
                return ValidationResult(
                    check_type="redirect",
                    success=True,
                    source_url=from_url,
                    expected_target=expected_to_url,
                    actual_target=actual_target
                )
            else:
                return ValidationResult(
                    check_type="redirect",
                    success=False,
                    source_url=from_url,
                    expected_target=expected_to_url,
                    actual_target=actual_target,
                    error=f"Redirects to wrong URL"
                )
                
        except requests.Timeout:
            return ValidationResult(
                check_type="redirect",
                success=False,
                source_url=from_url,
                expected_target=expected_to_url,
                error="Request timed out"
            )
        except requests.RequestException as e:
            return ValidationResult(
                check_type="redirect",
                success=False,
                source_url=from_url,
                expected_target=expected_to_url,
                error=str(e)
            )
    
    def verify_internal_link(
        self,
        parent_url: str,
        child_url: str
    ) -> ValidationResult:
        """Verify an internal link exists on a page.
        
        Fetches parent_url and checks that it contains
        a link to child_url.
        
        Args:
            parent_url: The page that should contain the link
            child_url: The URL that should be linked to
            
        Returns:
            ValidationResult with pass/fail status
        """
        try:
            response = self.session.get(
                parent_url,
                timeout=self.timeout,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                return ValidationResult(
                    check_type="internal_link",
                    success=False,
                    source_url=parent_url,
                    expected_target=child_url,
                    error=f"Parent page returned HTTP {response.status_code}"
                )
            
            # Parse HTML and find links
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Normalize child URL for comparison
            child_parsed = urlparse(child_url)
            child_path = child_parsed.path.rstrip("/")
            
            # Check all links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Handle relative URLs
                if not href.startswith("http"):
                    href = urljoin(parent_url, href)
                
                # Compare paths
                href_parsed = urlparse(href)
                href_path = href_parsed.path.rstrip("/")
                
                if href_path == child_path or href == child_url:
                    return ValidationResult(
                        check_type="internal_link",
                        success=True,
                        source_url=parent_url,
                        expected_target=child_url,
                        actual_target=href
                    )
            
            return ValidationResult(
                check_type="internal_link",
                success=False,
                source_url=parent_url,
                expected_target=child_url,
                error="Link not found in page content"
            )
            
        except requests.RequestException as e:
            return ValidationResult(
                check_type="internal_link",
                success=False,
                source_url=parent_url,
                expected_target=child_url,
                error=str(e)
            )
    
    def verify_no_chain(
        self,
        start_url: str,
        final_url: str,
        max_hops: int = 1
    ) -> ValidationResult:
        """Verify a redirect chain has been flattened.
        
        Follows redirects from start_url and verifies it reaches
        final_url in max_hops or fewer redirects.
        
        Args:
            start_url: The starting URL
            final_url: Expected final destination
            max_hops: Maximum allowed redirects (1 = no chain)
            
        Returns:
            ValidationResult with pass/fail status
        """
        current_url = start_url
        hops = 0
        
        try:
            while hops < 10:  # Safety limit
                response = self.session.get(
                    current_url,
                    allow_redirects=False,
                    timeout=self.timeout
                )
                
                if response.status_code in [301, 302, 303, 307, 308]:
                    hops += 1
                    location = response.headers.get("Location", "")
                    if not location.startswith("http"):
                        location = urljoin(current_url, location)
                    current_url = location
                else:
                    # Reached final destination
                    break
            
            # Check if we arrived at expected destination
            current_normalized = current_url.rstrip("/")
            final_normalized = final_url.rstrip("/")
            
            if current_normalized != final_normalized:
                return ValidationResult(
                    check_type="chain",
                    success=False,
                    source_url=start_url,
                    expected_target=final_url,
                    actual_target=current_url,
                    error=f"Arrived at wrong destination after {hops} hops"
                )
            
            if hops > max_hops:
                return ValidationResult(
                    check_type="chain",
                    success=False,
                    source_url=start_url,
                    expected_target=final_url,
                    actual_target=current_url,
                    error=f"Chain still exists: {hops} hops (max: {max_hops})"
                )
            
            return ValidationResult(
                check_type="chain",
                success=True,
                source_url=start_url,
                expected_target=final_url,
                actual_target=current_url
            )
            
        except requests.RequestException as e:
            return ValidationResult(
                check_type="chain",
                success=False,
                source_url=start_url,
                expected_target=final_url,
                error=str(e)
            )
    
    def validate_fixes(
        self,
        fixes: List[dict]
    ) -> ValidationReport:
        """Validate a batch of fixes.
        
        Args:
            fixes: List of fix dicts with 'type', 'source_url', 'target_url'
            
        Returns:
            ValidationReport with all results
        """
        results = []
        
        for fix in fixes:
            fix_type = fix.get("type")
            source = fix.get("source_url", "")
            target = fix.get("target_url", "")
            
            if fix_type == "broken_link":
                result = self.verify_redirect(source, target)
            elif fix_type == "orphan_page":
                # For orphan fixes, source is parent, target is child
                result = self.verify_internal_link(target, source)
            elif fix_type == "redirect_chain":
                result = self.verify_no_chain(source, target)
            else:
                result = ValidationResult(
                    check_type="unknown",
                    success=False,
                    source_url=source,
                    error=f"Unknown fix type: {fix_type}"
                )
            
            results.append(result)
        
        passed = sum(1 for r in results if r.success)
        
        return ValidationReport(
            total_checks=len(results),
            passed=passed,
            failed=len(results) - passed,
            results=results
        )


def create_validator() -> TechnicalValidator:
    """Create a TechnicalValidator with default settings."""
    return TechnicalValidator()
