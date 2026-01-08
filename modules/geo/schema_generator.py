"""JSON-LD Schema Generator for GEO optimization.

Generates structured data for Product, Review, HowTo, and FAQPage schemas.
Migrated from geo-transformer-skill to seo-agency-2026.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SchemaValidationResult:
    """Result of schema validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class SchemaGenerator:
    """Generate and inject JSON-LD structured data."""
    
    @staticmethod
    def detect_content_type(content: str) -> str:
        """Detect the most appropriate schema type for content."""
        text = re.sub(r'<[^>]+>', ' ', content).lower()
        
        # Check for FAQ patterns
        faq_indicators = [
            r'\bfaq\b', r'frequently asked',
            r'<h[234][^>]*>\s*(?:q:|question:?)',
            r'<strong>\s*(?:q:|question:?)',
        ]
        faq_score = sum(1 for p in faq_indicators if re.search(p, content, re.IGNORECASE))
        if faq_score >= 2 or re.search(r'\bfaq\b', text):
            return 'FAQPage'
        
        # Check for HowTo patterns
        howto_indicators = [
            r'how to\b', r'step \d+', r'step-by-step',
            r'<ol[^>]*>', r'instructions',
        ]
        howto_score = sum(1 for p in howto_indicators if re.search(p, content, re.IGNORECASE))
        if howto_score >= 2:
            return 'HowTo'
        
        # Check for Review patterns
        review_indicators = [
            r'review\b', r'rating', r'\d+/\d+',
            r'pros and cons', r'verdict', r'score:',
        ]
        review_score = sum(1 for p in review_indicators if re.search(p, content, re.IGNORECASE))
        if review_score >= 2:
            return 'Review'
        
        # Check for Product patterns
        product_indicators = [
            r'\$\d+', r'price', r'buy now',
            r'product', r'specs', r'features:',
        ]
        product_score = sum(1 for p in product_indicators if re.search(p, content, re.IGNORECASE))
        if product_score >= 2:
            return 'Product'
        
        return 'Article'
    
    @staticmethod
    def generate_product_schema(
        name: str,
        description: str,
        price: float,
        currency: str = "USD",
        image: Optional[str] = None,
        brand: Optional[str] = None,
        gtin: Optional[str] = None,
        sku: Optional[str] = None,
        availability: str = "InStock",
        review_rating: Optional[float] = None,
        review_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate Product schema with required Price.
        
        QC REQUIREMENT: Product schema MUST have price and should have GTIN.
        """
        schema: Dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": name,
            "description": description,
            "offers": {
                "@type": "Offer",
                "price": price,
                "priceCurrency": currency,
                "availability": f"https://schema.org/{availability}"
            }
        }
        
        if image:
            schema["image"] = image
        
        if brand:
            schema["brand"] = {"@type": "Brand", "name": brand}
        
        if gtin:
            if len(gtin) == 13:
                schema["gtin13"] = gtin
            elif len(gtin) == 14:
                schema["gtin14"] = gtin
            else:
                schema["gtin"] = gtin
        
        if sku:
            schema["sku"] = sku
        
        if review_rating and review_count:
            schema["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": review_rating,
                "reviewCount": review_count
            }
        
        return schema
    
    @staticmethod
    def generate_review_schema(
        item_name: str,
        item_type: str,
        review_body: str,
        rating: float,
        author_name: str,
        date_published: Optional[str] = None,
        best_rating: float = 5,
        worst_rating: float = 1
    ) -> Dict[str, Any]:
        """Generate Review schema."""
        if date_published is None:
            date_published = datetime.now().strftime("%Y-%m-%d")
        
        return {
            "@context": "https://schema.org",
            "@type": "Review",
            "itemReviewed": {"@type": item_type, "name": item_name},
            "reviewRating": {
                "@type": "Rating",
                "ratingValue": rating,
                "bestRating": best_rating,
                "worstRating": worst_rating
            },
            "author": {"@type": "Person", "name": author_name},
            "datePublished": date_published,
            "reviewBody": review_body
        }
    
    @staticmethod
    def generate_howto_schema(
        name: str,
        description: str,
        steps: List[Dict[str, str]],
        total_time: Optional[str] = None,
        image: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate HowTo schema."""
        schema: Dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": name,
            "description": description,
            "step": [
                {
                    "@type": "HowToStep",
                    "name": step.get("name", f"Step {i+1}"),
                    "text": step["text"]
                }
                for i, step in enumerate(steps)
            ]
        }
        
        if total_time:
            schema["totalTime"] = total_time
        if image:
            schema["image"] = image
        
        return schema
    
    @staticmethod
    def generate_faq_schema(qa_pairs: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate FAQPage schema."""
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": qa["question"],
                    "acceptedAnswer": {"@type": "Answer", "text": qa["answer"]}
                }
                for qa in qa_pairs
            ]
        }
    
    @staticmethod
    def generate_article_schema(
        headline: str,
        description: str,
        author_name: str,
        date_published: Optional[str] = None,
        date_modified: Optional[str] = None,
        image: Optional[str] = None,
        publisher_name: Optional[str] = None,
        publisher_logo: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate Article schema for general content."""
        if date_published is None:
            date_published = datetime.now().strftime("%Y-%m-%d")
        
        schema: Dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": headline[:110],
            "description": description,
            "author": {"@type": "Person", "name": author_name},
            "datePublished": date_published
        }
        
        if date_modified:
            schema["dateModified"] = date_modified
        if image:
            schema["image"] = image
        if publisher_name:
            publisher: Dict[str, Any] = {"@type": "Organization", "name": publisher_name}
            if publisher_logo:
                publisher["logo"] = {"@type": "ImageObject", "url": publisher_logo}
            schema["publisher"] = publisher
        
        return schema
    
    @staticmethod
    def validate_schema(schema: Dict[str, Any]) -> SchemaValidationResult:
        """Validate schema against QC requirements."""
        errors = []
        warnings = []
        
        schema_type = schema.get("@type", "")
        
        if "@context" not in schema:
            errors.append("Missing @context")
        if "@type" not in schema:
            errors.append("Missing @type")
        
        if schema_type == "Product":
            offers = schema.get("offers", {})
            if not offers:
                errors.append("Product schema missing 'offers'")
            elif "price" not in offers:
                errors.append("Product schema missing 'price' in offers")
            
            has_identifier = any(
                k in schema for k in ["gtin", "gtin13", "gtin14", "gtin8", "isbn", "sku", "mpn"]
            )
            if not has_identifier:
                warnings.append("Product schema missing identifier (gtin/sku/mpn)")
        
        if schema_type == "HowTo" and not schema.get("step"):
            errors.append("HowTo schema missing 'step' array")
        
        if schema_type == "FAQPage" and not schema.get("mainEntity"):
            errors.append("FAQPage schema missing 'mainEntity' array")
        
        return SchemaValidationResult(len(errors) == 0, errors, warnings)
    
    @classmethod
    def inject_schema(cls, content: str, schema: Dict[str, Any]) -> str:
        """Inject JSON-LD schema into the <head> section."""
        validation = cls.validate_schema(schema)
        if not validation.is_valid:
            raise ValueError(f"Schema validation failed: {', '.join(validation.errors)}")
        
        schema_json = json.dumps(schema, indent=2)
        script_block = f'<script type="application/ld+json">\n{schema_json}\n</script>'
        
        head_match = re.search(r'(</head>)', content, re.IGNORECASE)
        if head_match:
            insert_pos = head_match.start()
            return content[:insert_pos] + "\n" + script_block + "\n" + content[insert_pos:]
        
        return script_block + "\n" + content
    
    @classmethod
    def extract_schemas(cls, content: str) -> List[Dict[str, Any]]:
        """Extract all JSON-LD schemas from content."""
        schemas = []
        
        matches = re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            content,
            re.DOTALL | re.IGNORECASE
        )
        
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, list):
                    schemas.extend(data)
                else:
                    schemas.append(data)
            except json.JSONDecodeError:
                continue
        
        return schemas


def generate_schema_for_content(
    content: str,
    title: str,
    author: str,
    **kwargs
) -> Dict[str, Any]:
    """Auto-generate appropriate schema based on content type."""
    gen = SchemaGenerator()
    content_type = gen.detect_content_type(content)
    
    if content_type == "FAQPage":
        qa_pairs = _extract_qa_pairs(content)
        if qa_pairs:
            return gen.generate_faq_schema(qa_pairs)
    
    elif content_type == "HowTo":
        steps = _extract_steps(content)
        if steps:
            return gen.generate_howto_schema(
                name=title,
                description=kwargs.get("description", title),
                steps=steps
            )
    
    elif content_type == "Product":
        return gen.generate_product_schema(
            name=title,
            description=kwargs.get("description", ""),
            price=kwargs.get("price", 0),
            gtin=kwargs.get("gtin"),
            sku=kwargs.get("sku")
        )
    
    elif content_type == "Review":
        return gen.generate_review_schema(
            item_name=kwargs.get("item_name", title),
            item_type=kwargs.get("item_type", "Product"),
            review_body=kwargs.get("review_body", ""),
            rating=kwargs.get("rating", 4),
            author_name=author
        )
    
    return gen.generate_article_schema(
        headline=title,
        description=kwargs.get("description", ""),
        author_name=author
    )


def _extract_qa_pairs(content: str) -> List[Dict[str, str]]:
    """Extract Q&A pairs from FAQ-style content."""
    pairs = []
    
    qa_pattern = r'(?:Q:|Question:?)\s*(.+?)(?:A:|Answer:?)\s*(.+?)(?=(?:Q:|Question:?)|$)'
    matches = re.findall(qa_pattern, content, re.IGNORECASE | re.DOTALL)
    
    for q, a in matches:
        q = re.sub(r'<[^>]+>', '', q).strip()
        a = re.sub(r'<[^>]+>', '', a).strip()
        if q and a:
            pairs.append({"question": q, "answer": a})
    
    if not pairs:
        h_pattern = r'<h[34][^>]*>([^<]+)</h[34]>\s*<p[^>]*>([^<]+)</p>'
        matches = re.findall(h_pattern, content, re.IGNORECASE)
        for q, a in matches:
            if '?' in q or q.lower().startswith(('how', 'what', 'why', 'when', 'where', 'who')):
                pairs.append({"question": q.strip(), "answer": a.strip()})
    
    return pairs


def _extract_steps(content: str) -> List[Dict[str, str]]:
    """Extract steps from HowTo-style content."""
    steps = []
    
    li_pattern = r'<li[^>]*>(.+?)</li>'
    ol_match = re.search(r'<ol[^>]*>(.*?)</ol>', content, re.DOTALL | re.IGNORECASE)
    
    if ol_match:
        items = re.findall(li_pattern, ol_match.group(1), re.DOTALL | re.IGNORECASE)
        for i, item in enumerate(items):
            text = re.sub(r'<[^>]+>', '', item).strip()
            steps.append({"name": f"Step {i+1}", "text": text})
    
    if not steps:
        step_pattern = r'(?:Step\s+(\d+):?)\s*(.+?)(?=Step\s+\d+|$)'
        matches = re.findall(step_pattern, content, re.IGNORECASE | re.DOTALL)
        for num, text in matches:
            text = re.sub(r'<[^>]+>', '', text).strip()
            steps.append({"name": f"Step {num}", "text": text})
    
    return steps
