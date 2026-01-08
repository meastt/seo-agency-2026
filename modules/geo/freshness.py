"""Content Freshness Module - Updates date references for contextual awareness.

Ensures content stays current by updating year references in:
- Post titles
- Answer capsules  
- Body content references to "best of [year]", "[year] guide", etc.

Migrated from geo-transformer-skill to seo-agency-2026.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass
class FreshnessResult:
    """Result of freshness updates."""
    original_title: str
    updated_title: str
    original_content: str
    updated_content: str
    year_updates: List[str]
    title_changed: bool
    content_changed: bool


class ContentFreshness:
    """Updates date references in content for contextual freshness."""
    
    def __init__(self, current_year: Optional[int] = None):
        """Initialize with current year."""
        self.current_year = current_year or datetime.now().year
        self.previous_year = self.current_year - 1
    
    def detect_stale_years(self, text: str) -> List[Tuple[int, str]]:
        """Find stale year references in text."""
        stale_years = []
        year_pattern = r'\b(20\d{2})\b'
        
        for match in re.finditer(year_pattern, text):
            year = int(match.group(1))
            if year < self.current_year and year >= self.current_year - 2:
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end]
                stale_years.append((year, context.strip()))
        
        return stale_years
    
    def should_update_year(self, context: str, year: int) -> bool:
        """Determine if a year reference should be updated based on context."""
        context_lower = context.lower()
        
        # Patterns that indicate the year SHOULD be updated
        update_patterns = [
            r'best\s+(?:of\s+)?20\d{2}',
            r'top\s+(?:\d+\s+)?(?:picks|choices|recommendations).*?20\d{2}',
            r'20\d{2}\s+(?:guide|edition|update|picks|roundup|review)',
            r'(?:guide|picks|list|roundup|ideas)\s+(?:for\s+)?20\d{2}',
            r'start\s+20\d{2}',
            r'in\s+20\d{2}\s+(?:right|guide|edition)',
            r'20\d{2}\s+(?:buying|holiday|christmas|summer|winter)',
            r'updated?\s+(?:for\s+)?20\d{2}',
        ]
        
        for pattern in update_patterns:
            if re.search(pattern, context_lower):
                return True
        
        # Patterns that indicate the year should NOT be updated (historical)
        keep_patterns = [
            r'(?:founded|established|since|started)\s+(?:in\s+)?20\d{2}',
            r'(?:was|were)\s+(?:released|launched|published|introduced)\s+(?:in\s+)?20\d{2}',
            r'(?:back\s+in|during)\s+20\d{2}',
            r'copyright\s+20\d{2}',
        ]
        
        for pattern in keep_patterns:
            if re.search(pattern, context_lower):
                return False
        
        # Default: if the year is last year, update it
        if year == self.previous_year:
            return True
        
        return False
    
    def update_title(self, title: str) -> Tuple[str, bool]:
        """Update year in title if appropriate."""
        stale = self.detect_stale_years(title)
        updated = title
        changed = False
        
        for year, _ in stale:
            if year == self.previous_year:
                if self.should_update_year(title, year):
                    updated = re.sub(rf'\b{year}\b', str(self.current_year), updated)
                    changed = True
        
        return updated, changed
    
    def update_content(self, content: str) -> Tuple[str, List[str]]:
        """Update year references in content."""
        changes = []
        updated = content
        
        stale = self.detect_stale_years(content)
        
        years_to_update = set()
        for year, context in stale:
            if self.should_update_year(context, year):
                years_to_update.add(year)
        
        for year in years_to_update:
            pattern = rf'\b{year}\b'
            count = len(re.findall(pattern, updated))
            updated = re.sub(pattern, str(self.current_year), updated)
            changes.append(f"Updated {count} references from {year} to {self.current_year}")
        
        return updated, changes
    
    def update_capsule_for_freshness(self, capsule: str) -> str:
        """Update answer capsule to use current year."""
        for year in range(self.current_year - 3, self.current_year):
            capsule = re.sub(rf'\b{year}\b', str(self.current_year), capsule)
        return capsule
    
    def refresh_content(
        self, 
        title: str, 
        content: str, 
        answer_capsule: Optional[str] = None
    ) -> FreshnessResult:
        """Apply all freshness updates."""
        updated_title, title_changed = self.update_title(title)
        updated_content, content_changes = self.update_content(content)
        
        if answer_capsule:
            updated_capsule = self.update_capsule_for_freshness(answer_capsule)
            if updated_capsule != answer_capsule:
                content_changes.append("Updated answer capsule year references")
        
        return FreshnessResult(
            original_title=title,
            updated_title=updated_title,
            original_content=content,
            updated_content=updated_content,
            year_updates=content_changes,
            title_changed=title_changed,
            content_changed=len(content_changes) > 0
        )


def refresh_for_current_year(title: str, content: str) -> FreshnessResult:
    """Convenience function to refresh content for current year."""
    freshness = ContentFreshness()
    return freshness.refresh_content(title, content)
