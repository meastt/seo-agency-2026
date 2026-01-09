"""Batch Operations - Audit multiple posts and generate reports.

Provides batch processing capabilities for:
- Auditing all posts in a category
- Generating CSV/JSON reports
- Prioritizing posts by improvement potential
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.wp_api import get_credentials, fetch_post, fetch_posts_by_category
from modules.geo.auditor import GEOAuditor, AuditResult


@dataclass
class PostAuditSummary:
    """Summary of a single post audit."""
    post_id: int
    title: str
    url: str
    overall_score: int
    answer_capsule_score: int
    structure_score: int
    eeat_score: int
    schema_score: int
    error_count: int
    warning_count: int
    is_processable: bool
    priority: str  # "high", "medium", "low"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BatchAuditReport:
    """Complete batch audit report."""
    site_url: str
    category_id: Optional[int]
    total_posts: int
    audited_posts: int
    failed_posts: int
    average_score: float
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    generated_at: str
    results: List[PostAuditSummary]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_url": self.site_url,
            "category_id": self.category_id,
            "total_posts": self.total_posts,
            "audited_posts": self.audited_posts,
            "failed_posts": self.failed_posts,
            "average_score": round(self.average_score, 1),
            "high_priority_count": self.high_priority_count,
            "medium_priority_count": self.medium_priority_count,
            "low_priority_count": self.low_priority_count,
            "generated_at": self.generated_at,
            "results": [r.to_dict() for r in self.results]
        }


class BatchAuditor:
    """Batch audit multiple posts."""
    
    def __init__(self, report_dir: str = "reports"):
        """Initialize batch auditor.
        
        Args:
            report_dir: Directory to save reports
        """
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True)
        self._load_credentials()
        self.auditor = GEOAuditor()
    
    def _load_credentials(self):
        """Load WordPress credentials."""
        self.site_url, self.username, self.app_password = get_credentials()
    
    def audit_post(self, post_id: int) -> Optional[PostAuditSummary]:
        """Audit a single post and return summary.
        
        Args:
            post_id: WordPress post ID
            
        Returns:
            PostAuditSummary or None if fetch failed
        """
        try:
            post = fetch_post(
                self.site_url, post_id, 
                self.username, self.app_password
            )
            
            content = post.get("content", {}).get("rendered", "")
            title = post.get("title", {}).get("rendered", "Untitled")
            url = post.get("link", "")
            
            result = self.auditor.audit(content, title)
            
            # Determine priority based on score
            if result.overall_score < 40:
                priority = "high"
            elif result.overall_score < 70:
                priority = "medium"
            else:
                priority = "low"
            
            # Count issues
            error_count = sum(1 for i in result.issues if i.severity == "error")
            warning_count = sum(1 for i in result.issues if i.severity == "warning")
            
            return PostAuditSummary(
                post_id=post_id,
                title=title[:100],  # Truncate long titles
                url=url,
                overall_score=result.overall_score,
                answer_capsule_score=result.category_scores.get("answer_capsule", 0),
                structure_score=result.category_scores.get("structure", 0),
                eeat_score=result.category_scores.get("eeat_signals", 0),
                schema_score=result.category_scores.get("schema", 0),
                error_count=error_count,
                warning_count=warning_count,
                is_processable=result.is_processable,
                priority=priority
            )
            
        except Exception as e:
            return None
    
    def audit_category(
        self, 
        category_id: int,
        max_posts: int = 50,
        on_progress: Optional[callable] = None
    ) -> BatchAuditReport:
        """Audit all posts in a category.
        
        Args:
            category_id: WordPress category ID
            max_posts: Maximum posts to audit
            on_progress: Callback(current, total) for progress updates
            
        Returns:
            BatchAuditReport with all results
        """
        # Fetch posts in category
        posts = fetch_posts_by_category(
            self.site_url,
            category_id,
            self.username,
            self.app_password,
            per_page=max_posts
        )
        
        total = len(posts)
        results = []
        failed = 0
        
        for i, post in enumerate(posts):
            post_id = post.get("id")
            
            if on_progress:
                on_progress(i + 1, total)
            
            summary = self.audit_post(post_id)
            if summary:
                results.append(summary)
            else:
                failed += 1
        
        # Sort by priority (high first) then by score (lowest first)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        results.sort(key=lambda x: (priority_order[x.priority], x.overall_score))
        
        # Calculate stats
        if results:
            avg_score = sum(r.overall_score for r in results) / len(results)
        else:
            avg_score = 0
        
        high_count = sum(1 for r in results if r.priority == "high")
        med_count = sum(1 for r in results if r.priority == "medium")
        low_count = sum(1 for r in results if r.priority == "low")
        
        return BatchAuditReport(
            site_url=self.site_url,
            category_id=category_id,
            total_posts=total,
            audited_posts=len(results),
            failed_posts=failed,
            average_score=avg_score,
            high_priority_count=high_count,
            medium_priority_count=med_count,
            low_priority_count=low_count,
            generated_at=datetime.now().isoformat(),
            results=results
        )
    
    def audit_post_ids(
        self,
        post_ids: List[int],
        on_progress: Optional[callable] = None
    ) -> BatchAuditReport:
        """Audit specific posts by ID.
        
        Args:
            post_ids: List of post IDs to audit
            on_progress: Callback(current, total) for progress
            
        Returns:
            BatchAuditReport with all results
        """
        total = len(post_ids)
        results = []
        failed = 0
        
        for i, post_id in enumerate(post_ids):
            if on_progress:
                on_progress(i + 1, total)
            
            summary = self.audit_post(post_id)
            if summary:
                results.append(summary)
            else:
                failed += 1
        
        # Sort by priority then score
        priority_order = {"high": 0, "medium": 1, "low": 2}
        results.sort(key=lambda x: (priority_order[x.priority], x.overall_score))
        
        if results:
            avg_score = sum(r.overall_score for r in results) / len(results)
        else:
            avg_score = 0
        
        high_count = sum(1 for r in results if r.priority == "high")
        med_count = sum(1 for r in results if r.priority == "medium")
        low_count = sum(1 for r in results if r.priority == "low")
        
        return BatchAuditReport(
            site_url=self.site_url,
            category_id=None,
            total_posts=total,
            audited_posts=len(results),
            failed_posts=failed,
            average_score=avg_score,
            high_priority_count=high_count,
            medium_priority_count=med_count,
            low_priority_count=low_count,
            generated_at=datetime.now().isoformat(),
            results=results
        )
    
    def save_report_json(self, report: BatchAuditReport, filename: str = None) -> str:
        """Save report as JSON.
        
        Args:
            report: The batch audit report
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"batch_audit_{timestamp}.json"
        
        filepath = self.report_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        
        return str(filepath)
    
    def save_report_csv(self, report: BatchAuditReport, filename: str = None) -> str:
        """Save report as CSV.
        
        Args:
            report: The batch audit report
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"batch_audit_{timestamp}.csv"
        
        filepath = self.report_dir / filename
        
        if not report.results:
            return str(filepath)
        
        fieldnames = [
            "post_id", "title", "url", "overall_score",
            "answer_capsule_score", "structure_score", "eeat_score", "schema_score",
            "error_count", "warning_count", "is_processable", "priority"
        ]
        
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in report.results:
                writer.writerow(result.to_dict())
        
        return str(filepath)


def create_batch_auditor() -> BatchAuditor:
    """Create a BatchAuditor with default settings."""
    return BatchAuditor()
