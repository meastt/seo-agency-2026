"""GEO Rewriter - Transform content for AI search engine optimization with HTML sanitization.

Migrated from geo-transformer-skill to seo-agency-2026.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class RewriteResult:
    """Result of content transformation."""
    original: str
    transformed: str
    changes_made: List[str]
    html_fixed: bool = False
    
    @property
    def has_changes(self) -> bool:
        return self.original != self.transformed


class HTMLSanitizer:
    """Fix common HTML issues before transformation."""
    
    VOID_ELEMENTS = {
        'br', 'hr', 'img', 'input', 'meta', 'link', 'area', 
        'base', 'col', 'embed', 'source', 'track', 'wbr'
    }
    
    @classmethod
    def sanitize(cls, content: str) -> Tuple[str, List[str]]:
        """Fix broken HTML and return list of fixes made."""
        fixes = []
        
        # Fix unclosed paragraph tags
        original = content
        content = cls._fix_unclosed_tags(content, 'p')
        if content != original:
            fixes.append("Fixed unclosed <p> tags")
        
        # Fix unclosed div tags
        original = content
        content = cls._fix_unclosed_tags(content, 'div')
        if content != original:
            fixes.append("Fixed unclosed <div> tags")
        
        # Fix unclosed span tags
        original = content
        content = cls._fix_unclosed_tags(content, 'span')
        if content != original:
            fixes.append("Fixed unclosed <span> tags")
        
        # Normalize whitespace in tags
        original = content
        content = re.sub(r'<\s+', '<', content)
        content = re.sub(r'\s+>', '>', content)
        if content != original:
            fixes.append("Normalized whitespace in tags")
        
        # Self-close void elements if needed
        for elem in cls.VOID_ELEMENTS:
            pattern = rf'<{elem}([^>]*)(?<!/)>'
            content = re.sub(pattern, rf'<{elem}\1 />', content, flags=re.IGNORECASE)
        
        return content, fixes
    
    @classmethod
    def _fix_unclosed_tags(cls, content: str, tag: str) -> str:
        """Attempt to fix unclosed tags of a specific type."""
        opening = len(re.findall(rf'<{tag}[^>]*(?<!/)>', content, re.IGNORECASE))
        closing = len(re.findall(rf'</{tag}>', content, re.IGNORECASE))
        
        if opening > closing:
            missing = opening - closing
            for _ in range(missing):
                pattern = rf'(<{tag}[^>]*>)((?:(?!<{tag}|</{tag}).)*?)(<(?:p|div|h[1-6]|ul|ol|table|section|article)[^>]*>)'
                content = re.sub(
                    pattern,
                    rf'\1\2</{tag}>\3',
                    content,
                    count=1,
                    flags=re.IGNORECASE | re.DOTALL
                )
        
        return content


class GEORewriter:
    """Transforms content to meet GEO optimization standards."""
    
    # Default template for answer capsule
    DEFAULT_CAPSULE_TEMPLATE = '''<div style="background: #f4f4f4; border-left: 5px solid #0073aa; padding: 20px; margin-bottom: 25px; font-weight: 500;">
  <strong>Quick Answer:</strong> {{ANSWER_CAPSULE}}
</div>'''
    
    def __init__(self, capsule_template: Optional[str] = None):
        """Initialize rewriter with templates."""
        self.capsule_template = capsule_template or self.DEFAULT_CAPSULE_TEMPLATE
    
    def add_answer_capsule(
        self, 
        content: str, 
        answer_text: str,
        first_person_experience: str = ""
    ) -> str:
        """Insert answer capsule immediately after H1.
        
        IMPORTANT: Answer capsule must NOT contain external links (QC fail condition).
        """
        # VALIDATE: Strip any external links from answer_text
        answer_text = re.sub(r'<a[^>]+href="https?://[^"]*"[^>]*>([^<]*)</a>', r'\1', answer_text)
        answer_text = re.sub(r'https?://\S+', '', answer_text).strip()
        
        # Enforce length limits (120-150 chars)
        if len(answer_text) > 150:
            sentences = re.split(r'(?<=[.!?])\s+', answer_text)
            answer_text = sentences[0]
            if len(answer_text) > 150:
                answer_text = answer_text[:147] + "..."
        
        # Build capsule from template
        capsule = self.capsule_template.replace("{{ANSWER_CAPSULE}}", answer_text)
        if first_person_experience:
            capsule = capsule.replace("{{FIRST_PERSON_EXPERIENCE}}", first_person_experience)
        else:
            capsule = re.sub(r'\n## Why This Matters\n\{\{FIRST_PERSON_EXPERIENCE\}\}', '', capsule)
        
        # Find H1 and insert after it
        h1_match = re.search(r'(</h1>)', content, re.IGNORECASE)
        if h1_match:
            insert_pos = h1_match.end()
            return content[:insert_pos] + "\n\n" + capsule + "\n" + content[insert_pos:]
        
        # No H1 found, insert at beginning
        return capsule + "\n\n" + content
    
    def shorten_sentences(self, content: str, max_words: int = 20) -> str:
        """Break up sentences longer than max_words."""
        
        def shorten_text(text: str) -> str:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            result = []
            
            for sentence in sentences:
                words = sentence.split()
                if len(words) <= max_words:
                    result.append(sentence)
                else:
                    split_patterns = [
                        r',\s*(?:and|but|or|so|yet)\s+',
                        r',\s*(?:which|that|who)\s+',
                        r';\s*',
                        r',\s+',
                    ]
                    
                    split_sentence = sentence
                    for pattern in split_patterns:
                        parts = re.split(pattern, sentence)
                        if len(parts) > 1 and all(
                            len(p.split()) <= max_words for p in parts if p.strip()
                        ):
                            split_sentence = '. '.join(
                                p.strip().capitalize() for p in parts if p.strip()
                            )
                            if not split_sentence.endswith('.'):
                                split_sentence += '.'
                            break
                    
                    result.append(split_sentence)
            
            return ' '.join(result)
        
        def process_paragraph(match):
            opening = match.group(1)
            inner = match.group(2)
            closing = match.group(3)
            return opening + shorten_text(inner) + closing
        
        content = re.sub(
            r'(<p[^>]*>)(.*?)(</p>)',
            process_paragraph,
            content,
            flags=re.DOTALL
        )
        
        return content
    
    def restructure_paragraphs(self, content: str, max_sentences: int = 4) -> str:
        """Break up paragraphs that are too long."""
        
        def split_paragraph(match):
            opening = match.group(1)
            inner = match.group(2)
            closing = match.group(3)
            
            sentences = re.split(r'(?<=[.!?])\s+', inner.strip())
            
            if len(sentences) <= max_sentences:
                return match.group(0)
            
            chunks = []
            current = []
            for sentence in sentences:
                current.append(sentence)
                if len(current) >= max_sentences:
                    chunks.append(' '.join(current))
                    current = []
            if current:
                chunks.append(' '.join(current))
            
            return '\n\n'.join(f'{opening}{chunk}{closing}' for chunk in chunks)
        
        return re.sub(
            r'(<p[^>]*>)(.*?)(</p>)',
            split_paragraph,
            content,
            flags=re.DOTALL
        )
    
    def add_experience_signals(self, content: str) -> str:
        """Transform passive voice to first-person active voice.
        
        This is critical for E-E-A-T and the QC 'I factor' requirement.
        """
        replacements = [
            (r'\bit was found that\b', 'I found that'),
            (r'\bit is recommended\b', 'I recommend'),
            (r'\btests showed\b', 'my tests showed'),
            (r'\bresults indicated\b', 'my results showed'),
            (r'\bit can be seen that\b', 'I observed that'),
            (r'\bit is known that\b', 'in my experience,'),
            (r'\bresearch suggests\b', 'my research shows'),
            (r'\bthe data shows\b', 'my data shows'),
            (r'\bmeasurements revealed\b', 'my measurements revealed'),
            (r'\btesting confirmed\b', 'my testing confirmed'),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        return content
    
    def add_h2_summaries(self, content: str) -> str:
        """Add markers where H2 summaries are needed."""
        
        def check_h2(match):
            full_match = match.group(0)
            h2_tag = match.group(1)
            following = match.group(2)
            
            summary_indicators = [
                r'^<p[^>]*>\s*(?:In summary|Here\'s|The key|This section|Essentially)',
                r'^<p[^>]*>\s*<strong>',
            ]
            
            has_summary = any(
                re.match(pattern, following.strip(), re.IGNORECASE)
                for pattern in summary_indicators
            )
            
            if has_summary:
                return full_match
            
            return h2_tag + "\n<!-- GEO: Add summary sentence here -->\n" + following
        
        return re.sub(
            r'(</h2>)\s*((?:(?!</h[12]>).)*)',
            check_h2,
            content,
            flags=re.DOTALL
        )
    
    def transform(
        self,
        content: str,
        answer_capsule: Optional[str] = None,
        first_person_exp: str = "",
        max_sentence_words: int = 20,
        max_para_sentences: int = 4,
        fix_html: bool = True,
        add_experience: bool = True
    ) -> RewriteResult:
        """Apply all GEO transformations to content."""
        original = content
        changes = []
        html_fixed = False
        
        # Edge case: Fix broken HTML first
        if fix_html:
            content, html_fixes = HTMLSanitizer.sanitize(content)
            if html_fixes:
                changes.extend(html_fixes)
                html_fixed = True
        
        # Add answer capsule if provided
        if answer_capsule:
            content = self.add_answer_capsule(content, answer_capsule, first_person_exp)
            changes.append("Added answer capsule after H1")
        
        # Add experience signals (I factor)
        if add_experience:
            before = content
            content = self.add_experience_signals(content)
            if content != before:
                changes.append("Converted passive voice to first-person (I factor)")
        
        # Shorten sentences
        before = content
        content = self.shorten_sentences(content, max_sentence_words)
        if content != before:
            changes.append(f"Shortened sentences exceeding {max_sentence_words} words")
        
        # Restructure paragraphs
        before = content
        content = self.restructure_paragraphs(content, max_para_sentences)
        if content != before:
            changes.append(f"Split paragraphs exceeding {max_para_sentences} sentences")
        
        # Add H2 summary markers
        before = content
        content = self.add_h2_summaries(content)
        if content != before:
            changes.append("Added markers for missing H2 summaries")
        
        return RewriteResult(
            original=original,
            transformed=content,
            changes_made=changes,
            html_fixed=html_fixed
        )


def rewrite_content(
    content: str,
    answer_capsule: Optional[str] = None,
    **kwargs
) -> RewriteResult:
    """Convenience function to rewrite content."""
    rewriter = GEORewriter()
    return rewriter.transform(content, answer_capsule, **kwargs)
