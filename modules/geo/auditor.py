"""GEO Auditor - Validates content against GEO checklist standards with edge case handling.

Migrated from geo-transformer-skill to seo-agency-2026.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple


@dataclass
class AuditIssue:
    """Single audit issue found in content."""
    category: str
    severity: str  # "error", "warning", "info"
    message: str
    suggestion: str = ""


@dataclass
class AuditResult:
    """Complete audit results for a piece of content."""
    overall_score: int  # 0-100
    category_scores: dict[str, int] = field(default_factory=dict)
    issues: list[AuditIssue] = field(default_factory=list)
    passed_checks: list[str] = field(default_factory=list)
    edge_case_flags: list[str] = field(default_factory=list)
    is_processable: bool = True  # False if content fails edge case checks
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "overall_score": self.overall_score,
            "category_scores": self.category_scores,
            "issues": [
                {
                    "category": i.category,
                    "severity": i.severity, 
                    "message": i.message,
                    "suggestion": i.suggestion
                }
                for i in self.issues
            ],
            "passed_checks": self.passed_checks,
            "edge_case_flags": self.edge_case_flags,
            "is_processable": self.is_processable
        }


class GEOAuditor:
    """Audits content against GEO optimization checklist with edge case detection."""
    
    def __init__(self, checklist_path: Optional[str] = None):
        """Initialize auditor with checklist.
        
        Args:
            checklist_path: Path to geo_checklist.json. If None, uses bundled checklist.
        """
        if checklist_path is None:
            checklist_path = Path(__file__).parent / "geo_checklist.json"
        
        with open(checklist_path) as f:
            self.checklist = json.load(f)
        
        # Minimum word count for processable content
        self.min_word_count = 50
    
    def audit(self, content: str, title: str = "") -> AuditResult:
        """Audit content against GEO checklist.
        
        Args:
            content: HTML or text content to audit
            title: Optional title/H1 of the content
            
        Returns:
            AuditResult with scores and issues
        """
        issues = []
        passed = []
        edge_flags = []
        category_scores = {}
        
        # === EDGE CASE DETECTION ===
        is_processable, edge_issues = self._check_edge_cases(content)
        issues.extend(edge_issues)
        edge_flags = [i.message for i in edge_issues if i.severity == "error"]
        
        if not is_processable:
            return AuditResult(
                overall_score=0,
                category_scores={"edge_cases": 0},
                issues=issues,
                passed_checks=[],
                edge_case_flags=edge_flags,
                is_processable=False
            )
        
        # === STANDARD AUDITS ===
        capsule_score, capsule_issues, capsule_passed = self._audit_answer_capsule(content)
        category_scores["answer_capsule"] = capsule_score
        issues.extend(capsule_issues)
        passed.extend(capsule_passed)
        
        structure_score, structure_issues, structure_passed = self._audit_structure(content)
        category_scores["structure"] = structure_score
        issues.extend(structure_issues)
        passed.extend(structure_passed)
        
        eeat_score, eeat_issues, eeat_passed = self._audit_eeat_signals(content)
        category_scores["eeat_signals"] = eeat_score
        issues.extend(eeat_issues)
        passed.extend(eeat_passed)
        
        schema_score, schema_issues, schema_passed = self._audit_schema(content)
        category_scores["schema"] = schema_score
        issues.extend(schema_issues)
        passed.extend(schema_passed)
        
        # Calculate weighted overall score
        weights = {
            "answer_capsule": 0.30,
            "structure": 0.25,
            "eeat_signals": 0.25,
            "schema": 0.20
        }
        overall_score = int(sum(
            category_scores.get(cat, 0) * weight 
            for cat, weight in weights.items()
        ))
        
        return AuditResult(
            overall_score=overall_score,
            category_scores=category_scores,
            issues=issues,
            passed_checks=passed,
            edge_case_flags=edge_flags,
            is_processable=True
        )
    
    def _check_edge_cases(self, content: str) -> Tuple[bool, List[AuditIssue]]:
        """Check for edge cases that may prevent processing."""
        issues = []
        is_processable = True
        
        # Strip HTML to get text content
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'\s+', ' ', text).strip()
        word_count = len(text.split())
        
        # Edge Case 1: Empty Post (< 50 words)
        if word_count < self.min_word_count:
            issues.append(AuditIssue(
                category="edge_case",
                severity="error",
                message=f"Empty/minimal content ({word_count} words, min: {self.min_word_count})",
                suggestion="Content too short for GEO transformation. Add more substantive content first."
            ))
            is_processable = False
        
        # Also check for image-only content
        img_count = len(re.findall(r'<img[^>]*>', content, re.IGNORECASE))
        if img_count > 0 and word_count < 20:
            issues.append(AuditIssue(
                category="edge_case",
                severity="error",
                message=f"Image-heavy with minimal text ({img_count} images, {word_count} words)",
                suggestion="Add text content to support the images before GEO transformation."
            ))
            is_processable = False
        
        # Edge Case 2: Broken HTML
        html_issues = self._detect_broken_html(content)
        if html_issues:
            issues.append(AuditIssue(
                category="edge_case",
                severity="warning",
                message=f"Broken HTML detected: {', '.join(html_issues[:3])}",
                suggestion="HTML will be sanitized before transformation."
            ))
        
        # Edge Case 3: Legacy Shortcodes
        shortcodes = re.findall(r'\[([a-zA-Z_]+)(?:\s[^\]]+)?\]', content)
        if shortcodes:
            unique_shortcodes = list(set(shortcodes))[:5]
            issues.append(AuditIssue(
                category="edge_case",
                severity="warning",
                message=f"Legacy shortcodes detected: [{', '.join(unique_shortcodes)}]",
                suggestion="Shortcodes will be preserved but may need manual conversion to Gutenberg."
            ))
        
        return is_processable, issues
    
    def _detect_broken_html(self, content: str) -> List[str]:
        """Detect common HTML issues."""
        issues = []
        
        void_elements = {
            'br', 'hr', 'img', 'input', 'meta', 'link', 'area', 
            'base', 'col', 'embed', 'source', 'track', 'wbr'
        }
        
        # Find all opening/closing tags
        opening_tags = re.findall(r'<([a-zA-Z][a-zA-Z0-9]*)(?:\s[^>]*)?(?<!/)>', content)
        closing_tags = re.findall(r'</([a-zA-Z][a-zA-Z0-9]*)>', content)
        
        # Filter out void elements
        opening_tags = [t.lower() for t in opening_tags if t.lower() not in void_elements]
        closing_tags = [t.lower() for t in closing_tags]
        
        # Count mismatch
        open_counts = Counter(opening_tags)
        close_counts = Counter(closing_tags)
        
        for tag, count in open_counts.items():
            close_count = close_counts.get(tag, 0)
            if count > close_count:
                issues.append(f"unclosed <{tag}> ({count - close_count} missing)")
        
        return issues
    
    def _audit_answer_capsule(self, content: str) -> Tuple[int, List[AuditIssue], List[str]]:
        """Check for answer capsule presence and quality."""
        issues = []
        passed = []
        score = 0
        
        capsule_config = self.checklist.get("answer_capsule", {})
        min_len = capsule_config.get("length_chars", {}).get("min", 120)
        max_len = capsule_config.get("length_chars", {}).get("max", 150)
        
        # Look for answer capsule patterns
        capsule_patterns = [
            r'<div[^>]*class="[^"]*(?:quick-answer|answer-capsule|tldr|summary)[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*style="[^"]*(?:background|border-left)[^"]*"[^>]*>.*?<strong>Quick Answer:?</strong>(.*?)</div>',
            r'<strong>(?:Quick Answer|TL;DR|Bottom Line):?</strong>\s*([^<]+)',
        ]
        
        capsule_text = None
        for pattern in capsule_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                capsule_text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                break
        
        if capsule_text:
            score += 50
            passed.append("Answer capsule present")
            
            capsule_len = len(capsule_text)
            if min_len <= capsule_len <= max_len:
                score += 30
                passed.append(f"Answer capsule length ({capsule_len} chars) within optimal range")
            elif capsule_len < min_len:
                issues.append(AuditIssue(
                    category="answer_capsule",
                    severity="warning",
                    message=f"Answer capsule too short ({capsule_len} chars, min: {min_len})",
                    suggestion="Expand the quick answer to include more detail"
                ))
                score += 15
            else:
                issues.append(AuditIssue(
                    category="answer_capsule",
                    severity="warning",
                    message=f"Answer capsule too long ({capsule_len} chars, max: {max_len})",
                    suggestion="Shorten to be more concise and citeable"
                ))
                score += 15
            
            # Check for external links in capsule
            full_capsule_match = re.search(
                r'<div[^>]*>.*?(?:Quick Answer|TL;DR).*?</div>',
                content, re.IGNORECASE | re.DOTALL
            )
            capsule_html = full_capsule_match.group(0) if full_capsule_match else ""
            
            if re.search(r'<a[^>]+href="https?://', capsule_html):
                issues.append(AuditIssue(
                    category="answer_capsule",
                    severity="error",
                    message="FAIL: Answer capsule contains external links",
                    suggestion="Remove ALL external links from the quick answer block"
                ))
            else:
                score += 20
                passed.append("No external links in answer capsule")
        else:
            issues.append(AuditIssue(
                category="answer_capsule",
                severity="error",
                message="No answer capsule found",
                suggestion="Add a Quick Answer block immediately after the H1"
            ))
        
        return min(score, 100), issues, passed
    
    def _audit_structure(self, content: str) -> Tuple[int, List[AuditIssue], List[str]]:
        """Check content structure against inverted pyramid standards."""
        issues = []
        passed = []
        score = 0
        
        structure_config = self.checklist.get("structure", {})
        max_sentence_len = structure_config.get("max_sentence_length", 20)
        max_para_sentences = structure_config.get("max_paragraph_sentences", 4)
        
        # Strip HTML for text analysis
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Check sentence lengths
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        long_sentences = []
        for sentence in sentences:
            words = sentence.split()
            if len(words) > max_sentence_len:
                long_sentences.append(len(words))
        
        if not long_sentences:
            score += 35
            passed.append(f"All sentences under {max_sentence_len} words")
        elif len(sentences) > 0:
            pct_long = len(long_sentences) / len(sentences) * 100
            if pct_long < 20:
                score += 20
                issues.append(AuditIssue(
                    category="structure",
                    severity="warning",
                    message=f"{len(long_sentences)} sentences exceed {max_sentence_len} words",
                    suggestion="Break up long sentences for better readability"
                ))
            else:
                issues.append(AuditIssue(
                    category="structure",
                    severity="error",
                    message=f"{pct_long:.0f}% of sentences exceed max length",
                    suggestion="Significant rewriting needed to shorten sentences"
                ))
        
        # Check paragraph structure
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
        long_paras = 0
        for para in paragraphs:
            para_text = re.sub(r'<[^>]+>', '', para)
            para_sentences = len([s for s in re.split(r'[.!?]+', para_text) if s.strip()])
            if para_sentences > max_para_sentences:
                long_paras += 1
        
        if long_paras == 0:
            score += 35
            passed.append(f"All paragraphs have ≤{max_para_sentences} sentences")
        else:
            issues.append(AuditIssue(
                category="structure",
                severity="warning",
                message=f"{long_paras} paragraphs exceed {max_para_sentences} sentences",
                suggestion="Break long paragraphs into smaller chunks"
            ))
            score += 15
        
        # Check H2 structure
        h2_count = len(re.findall(r'<h2[^>]*>', content))
        if h2_count >= 3:
            score += 30
            passed.append(f"Good H2 structure ({h2_count} headings)")
        elif h2_count > 0:
            score += 15
            issues.append(AuditIssue(
                category="structure",
                severity="info",
                message=f"Only {h2_count} H2 headings found",
                suggestion="Consider adding more H2 sections for better structure"
            ))
        else:
            issues.append(AuditIssue(
                category="structure",
                severity="warning",
                message="No H2 headings found",
                suggestion="Add H2 headings to structure the content"
            ))
        
        return min(score, 100), issues, passed
    
    def _audit_eeat_signals(self, content: str) -> Tuple[int, List[AuditIssue], List[str]]:
        """Check for E-E-A-T signals in content."""
        issues = []
        passed = []
        score = 0
        
        text = re.sub(r'<[^>]+>', ' ', content).lower()
        
        # Check first-person language (THE "I" FACTOR)
        first_person_terms = [
            r'\bi\b', r'\bmy\b', r'\bme\b', r'\bour\b', r'\bwe\b',
            r'in my experience', r'i tested', r'i found', r'our team',
            r'in my field test', r'my results'
        ]
        first_person_count = sum(
            len(re.findall(term, text)) 
            for term in first_person_terms
        )
        
        if first_person_count >= 5:
            score += 35
            passed.append(f"Strong first-person voice ({first_person_count} instances)")
        elif first_person_count >= 2:
            score += 20
            issues.append(AuditIssue(
                category="eeat_signals",
                severity="warning",
                message="Limited first-person experiential language",
                suggestion="Add more personal experience and testing language"
            ))
        else:
            issues.append(AuditIssue(
                category="eeat_signals",
                severity="error",
                message="FAIL: No 'I' factor - missing first-person experiential language",
                suggestion="Include personal testing, experiences, or observations"
            ))
        
        # Check for data points / statistics
        data_patterns = [
            r'\d+(?:\.\d+)?%',
            r'\d+(?:\.\d+)?x',
            r'\d+ (?:hours?|days?|minutes?|seconds?)',
            r'\$\d+',
            r'(?:tested|measured|found|observed) \d+',
        ]
        data_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in data_patterns
        )
        
        if data_count >= 5:
            score += 35
            passed.append(f"Good data density ({data_count} data points)")
        elif data_count >= 2:
            score += 20
            issues.append(AuditIssue(
                category="eeat_signals",
                severity="info",
                message=f"Some data points present ({data_count})",
                suggestion="Add more specific metrics and statistics"
            ))
        else:
            issues.append(AuditIssue(
                category="eeat_signals",
                severity="warning",
                message="Few or no data points found",
                suggestion="Include specific numbers, percentages, or test results"
            ))
        
        # Check for author credentials
        if re.search(r'author|written by|reviewed by|expert|credential', text):
            score += 30
            passed.append("Author credentials indicator present")
        else:
            issues.append(AuditIssue(
                category="eeat_signals",
                severity="info",
                message="No author credentials visible in content",
                suggestion="Add author bio or credentials reference"
            ))
        
        return min(score, 100), issues, passed
    
    def _audit_schema(self, content: str) -> Tuple[int, List[AuditIssue], List[str]]:
        """Check for JSON-LD schema markup."""
        issues = []
        passed = []
        score = 0
        
        required_types = self.checklist.get("required_schema", [])
        
        # Find all JSON-LD blocks
        schema_matches = re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            content,
            re.DOTALL | re.IGNORECASE
        )
        
        if schema_matches:
            score += 50
            passed.append("JSON-LD schema markup present")
            
            found_types = []
            for schema_str in schema_matches:
                try:
                    schema_data = json.loads(schema_str)
                    schemas_to_check = []
                    
                    if isinstance(schema_data, dict):
                        schemas_to_check.append(schema_data)
                        if "@type" in schema_data:
                            found_types.append(schema_data["@type"])
                    elif isinstance(schema_data, list):
                        schemas_to_check.extend(schema_data)
                        for item in schema_data:
                            if isinstance(item, dict) and "@type" in item:
                                found_types.append(item["@type"])
                    
                    # Validate Product schema
                    for schema in schemas_to_check:
                        if isinstance(schema, dict) and schema.get("@type") == "Product":
                            has_price = "offers" in schema and (
                                "price" in schema.get("offers", {}) or
                                isinstance(schema.get("offers"), list)
                            )
                            has_gtin = any(k in schema for k in ["gtin", "gtin13", "gtin14", "gtin8", "isbn", "sku"])
                            
                            if not has_price:
                                issues.append(AuditIssue(
                                    category="schema",
                                    severity="error",
                                    message="FAIL: Product schema missing Price in offers",
                                    suggestion="Add offers.price to Product schema"
                                ))
                            if not has_gtin:
                                issues.append(AuditIssue(
                                    category="schema",
                                    severity="warning",
                                    message="Product schema missing GTIN/SKU identifier",
                                    suggestion="Add gtin, isbn, or sku to Product schema"
                                ))
                                
                except json.JSONDecodeError:
                    issues.append(AuditIssue(
                        category="schema",
                        severity="error",
                        message="FAIL: Invalid JSON-LD markup (parse error)",
                        suggestion="Fix JSON syntax errors in schema block"
                    ))
            
            # Check for recommended types
            matching_types = set(found_types) & set(required_types)
            if matching_types:
                score += 50
                passed.append(f"Has recommended schema types: {', '.join(matching_types)}")
            else:
                issues.append(AuditIssue(
                    category="schema",
                    severity="info",
                    message=f"No recommended schema types ({', '.join(required_types)})",
                    suggestion=f"Add one of: {', '.join(required_types)}"
                ))
                score += 20
        else:
            issues.append(AuditIssue(
                category="schema",
                severity="error",
                message="No JSON-LD schema markup found",
                suggestion="Add structured data for better AI engine understanding"
            ))
        
        return min(score, 100), issues, passed


def audit_content(content: str, title: str = "") -> AuditResult:
    """Convenience function to audit content."""
    auditor = GEOAuditor()
    return auditor.audit(content, title)
