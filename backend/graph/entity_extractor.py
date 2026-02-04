"""
LLM-based Entity Extractor for Academic Knowledge Graphs

Extracts structured academic entities from paper text using Claude 3.5 Haiku.
Implements NLP-AKG methodology for few-shot knowledge graph construction.

Entity Types:
- Problem: Research questions/problems addressed
- Concept: Key theoretical concepts (PRIMARY - become graph nodes)
- Method: Research methodologies used
- Dataset: Datasets mentioned
- Metric: Evaluation metrics
- Finding: Key research results
- Innovation: Novel contributions
- Limitation: Study limitations

Reference: NLP-AKG (https://arxiv.org/html/2502.14192v1)
"""

import asyncio
import json
import logging
import re
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# PERF-011: Slow API call threshold (seconds)
SLOW_API_THRESHOLD = 10.0


# PERF-013: Optimized retry constants (reduced from 2/1.0 to 1/0.5)
# - Max API calls: 3 → 2 (33% reduction)
# - Recovery time: 1.0s → 0.5s
MAX_RETRIES = 1
RETRY_DELAY_SECONDS = 0.5


class EntityType(str, Enum):
    """Entity types for academic knowledge graph."""
    # Metadata types (not visualized as nodes)
    PAPER = "Paper"
    AUTHOR = "Author"

    # Primary node types (visualized)
    CONCEPT = "Concept"
    METHOD = "Method"
    FINDING = "Finding"

    # Extended types (NLP-AKG style)
    PROBLEM = "Problem"
    DATASET = "Dataset"
    METRIC = "Metric"
    INNOVATION = "Innovation"
    LIMITATION = "Limitation"

    # Legacy types
    INSTITUTION = "Institution"


@dataclass
class ExtractedEntity:
    """Entity extracted from academic text."""

    entity_type: EntityType
    name: str
    definition: str = ""  # Brief definition in context
    description: str = ""  # Extended description
    confidence: float = 0.0
    source_paper_id: Optional[str] = None
    properties: dict = field(default_factory=dict)

    def __post_init__(self):
        # Normalize name: lowercase, strip whitespace
        self.name = self.name.strip().lower() if self.name else ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "entity_type": self.entity_type.value if isinstance(self.entity_type, EntityType) else self.entity_type,
            "name": self.name,
            "definition": self.definition,
            "description": self.description,
            "confidence": self.confidence,
            "source_paper_id": self.source_paper_id,
            "properties": self.properties,
        }


# ============================================================================
# NLP-AKG Style Extraction Prompt
# ============================================================================

CONCEPT_CENTRIC_EXTRACTION_PROMPT = """You are an expert academic research analyst building a concept-centric knowledge graph.
Your task is to extract structured entities from academic papers, with CONCEPTS as the primary focus.

## Paper Information
Title: {title}
Abstract: {abstract}

## Extraction Guidelines

### CONCEPTS (Most Important - become graph nodes)
Extract the key theoretical concepts, theories, and domain-specific terms.
- Focus on concepts that connect to other concepts across papers
- Include both broad concepts (e.g., "machine learning") and specific ones (e.g., "transformer architecture")
- Each concept should be a noun or noun phrase
- Provide a brief definition in the context of this paper

### METHODS
Research methodologies, techniques, or approaches used.
- Include study design (e.g., "randomized controlled trial")
- Include analytical methods (e.g., "regression analysis")
- Include tools/frameworks if significant

### FINDINGS
Key results, conclusions, or discoveries.
- Focus on empirical findings with evidence
- Include effect sizes, statistical significance if mentioned
- Phrase as declarative statements

### PROBLEMS (Research Questions)
The research questions or problems being addressed.
- What gap in knowledge does this paper address?
- What is the main research question?

### INNOVATIONS
Novel contributions this paper makes.
- What is new or different about this work?
- What advances does it provide?

### LIMITATIONS
Study limitations acknowledged or implied.
- What are the constraints of this research?
- What couldn't be addressed?

## Response Format

Return a JSON object with this exact structure:
{{
    "concepts": [
        {{
            "name": "concept name (lowercase, 1-4 words)",
            "definition": "brief definition in this paper's context (1-2 sentences)",
            "confidence": 0.9
        }}
    ],
    "methods": [
        {{
            "name": "method name",
            "description": "how it was applied",
            "type": "quantitative|qualitative|mixed",
            "confidence": 0.85
        }}
    ],
    "findings": [
        {{
            "name": "brief finding statement (1 sentence)",
            "description": "detailed finding with evidence",
            "effect_type": "positive|negative|neutral|mixed",
            "confidence": 0.8
        }}
    ],
    "problems": [
        {{
            "name": "research problem/question",
            "description": "context and importance",
            "confidence": 0.85
        }}
    ],
    "innovations": [
        {{
            "name": "innovation summary",
            "description": "what makes it novel",
            "confidence": 0.75
        }}
    ],
    "limitations": [
        {{
            "name": "limitation summary",
            "description": "details and implications",
            "confidence": 0.7
        }}
    ]
}}

## Rules
1. Extract ONLY entities explicitly mentioned or strongly implied
2. Concept names: lowercase, singular form, 1-4 words
3. Confidence: 0.5 (uncertain) to 1.0 (explicit mention)
4. Maximum per type: concepts=10, methods=5, findings=5, others=3
5. Prioritize quality over quantity
6. Return ONLY valid JSON, no additional text

JSON Response:"""


# ============================================================================
# Simplified Prompt for High-Speed Extraction (Claude 3.5 Haiku)
# v0.6.0: Fixed to ensure all entity types are extracted, not just concepts
# ============================================================================

FAST_EXTRACTION_PROMPT = """You are an academic entity extraction system. Extract EXACTLY these 7 entity types from the paper. Return ALL categories, even if empty.

## Paper
Title: {title}
Abstract: {abstract}

## Required Entity Types (extract ALL 7):

### 1. CONCEPTS (max 10)
Key theoretical concepts, theories, domain terms.
Example: "machine learning", "cognitive load"

### 2. METHODS (max 3)
Research methodologies, techniques, approaches.
Example: "meta-analysis", "randomized controlled trial"

### 3. FINDINGS (max 3)
Key results, conclusions, discoveries.
Example: "positive effect on learning outcomes"

### 4. PROBLEMS (max 2)
Research questions or problems addressed.
Example: "gap in understanding ai adoption"

### 5. INNOVATIONS (max 2)
Novel contributions of this work.
Example: "new framework for evaluation"

### 6. LIMITATIONS (max 2)
Study limitations acknowledged.
Example: "small sample size"

### 7. DATASETS (max 2)
Datasets used or created.
Example: "imagenet", "custom survey n=500"

## Output Format
Return ONLY valid JSON. ALL 7 keys MUST be present. Use empty arrays [] if no entities found.

{{"concepts": [...], "methods": [...], "findings": [...], "problems": [...], "innovations": [...], "limitations": [...], "datasets": [...]}}

Each entity: {{"name": "lowercase 1-4 words", "confidence": 0.0-1.0}}

JSON:"""


# Legacy prompt (deprecated, kept for reference)
FAST_EXTRACTION_PROMPT_LEGACY = """Extract key entities from this academic paper.

Title: {title}
Abstract: {abstract}

Return JSON with these categories:
- concepts: [{{"name": "...", "definition": "...", "confidence": 0.9}}] (max 10) - Key theoretical concepts
- methods: [{{"name": "...", "type": "quantitative|qualitative|mixed"}}] (max 3) - Research methodologies
- findings: [{{"name": "...", "effect_type": "positive|negative|neutral"}}] (max 3) - Key results
- problems: [{{"name": "...", "description": "..."}}] (max 2) - Research problems/questions addressed
- innovations: [{{"name": "...", "novelty": "..."}}] (max 2) - Novel contributions
- limitations: [{{"name": "...", "impact": "..."}}] (max 2) - Study limitations
- datasets: [{{"name": "...", "size": "...", "domain": "..."}}] (max 2) - Datasets used/created

Rules: lowercase names, 1-4 words each, only JSON output. Omit empty categories.

JSON:"""


# ============================================================================
# Section-Specific Prompts for Section-Aware Extraction
# ============================================================================

SECTION_PROMPTS = {
    "introduction": """Extract entities from the INTRODUCTION section of this academic paper.

Section Text: {text}

Focus on:
- Research problems/questions being addressed
- Key concepts that frame the study
- Background theories or frameworks

Return JSON with:
- concepts: [{{"name": "...", "definition": "...", "confidence": 0.9}}] (max 5)
- problems: [{{"name": "...", "description": "..."}}] (max 3)

Rules: lowercase names, 1-4 words each, only JSON output.

JSON:""",

    "methodology": """Extract entities from the METHODOLOGY section of this academic paper.

Section Text: {text}

Focus on:
- Research methods and approaches used
- Datasets mentioned or created
- Measurement metrics and instruments
- Sample characteristics

Return JSON with:
- methods: [{{"name": "...", "type": "quantitative|qualitative|mixed", "description": "..."}}] (max 5)
- datasets: [{{"name": "...", "size": "...", "domain": "..."}}] (max 3)

Rules: lowercase names, 1-4 words each, only JSON output.

JSON:""",

    "results": """Extract entities from the RESULTS section of this academic paper.

Section Text: {text}

Focus on:
- Key findings and discoveries
- Statistical results and effect sizes
- Metrics and their values

Return JSON with:
- findings: [{{"name": "...", "effect_type": "positive|negative|neutral", "description": "..."}}] (max 5)
- concepts: [{{"name": "...", "definition": "...", "confidence": 0.8}}] (max 3)

Rules: lowercase names, 1-4 words each, only JSON output.

JSON:""",

    "discussion": """Extract entities from the DISCUSSION section of this academic paper.

Section Text: {text}

Focus on:
- Implications and contributions
- Limitations of the study
- Future research directions
- Novel innovations or insights

Return JSON with:
- innovations: [{{"name": "...", "novelty": "..."}}] (max 3)
- limitations: [{{"name": "...", "impact": "..."}}] (max 3)
- concepts: [{{"name": "...", "definition": "...", "confidence": 0.7}}] (max 3)

Rules: lowercase names, 1-4 words each, only JSON output.

JSON:""",
}


class EntityExtractor:
    """
    Extracts entities from academic papers using LLM.

    Uses Claude 3.5 Haiku for fast, cost-effective extraction.
    Implements NLP-AKG methodology for academic knowledge graph construction.
    """

    def __init__(self, llm_provider=None, use_fast_mode: bool = True):
        """
        Initialize entity extractor.

        Args:
            llm_provider: LLM provider instance (Claude, OpenAI, etc.)
            use_fast_mode: Use simplified prompt for faster extraction
        """
        self.llm = llm_provider
        self.use_fast_mode = use_fast_mode
        self._extraction_cache: Dict[str, dict] = {}

    async def extract_from_paper(
        self,
        title: str,
        abstract: str,
        paper_id: Optional[str] = None,
        use_accurate_model: bool = False,
        seed_concepts: Optional[List[str]] = None,
        user_notes: Optional[List[str]] = None,
    ) -> dict:
        """
        Extract entities from a paper's title and abstract.

        Args:
            title: Paper title
            abstract: Paper abstract
            paper_id: Optional paper ID for tracking source
            use_accurate_model: Use more accurate (slower/expensive) model
            seed_concepts: User-provided concepts (from Zotero tags) to boost
            user_notes: User notes to include in extraction context

        Returns:
            Dictionary with extracted entities by type
        """
        if not title and not abstract:
            return self._empty_result()

        # Check cache
        cache_key = f"{title[:50]}_{hash(abstract[:100])}"
        if cache_key in self._extraction_cache:
            logger.debug(f"Cache hit for: {title[:50]}...")
            return self._extraction_cache[cache_key]

        # Use LLM if available
        if self.llm:
            try:
                result = await self._llm_extraction(
                    title, abstract, paper_id, use_accurate_model,
                    seed_concepts=seed_concepts, user_notes=user_notes
                )
                self._extraction_cache[cache_key] = result
                return result
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}, using fallback")

        # Fallback to keyword extraction
        result = self._fallback_extraction(title, abstract, paper_id)
        self._extraction_cache[cache_key] = result
        return result

    async def extract_entities(
        self,
        text: str,
        title: str = "",
        context: str = "",
        seed_concepts: Optional[List[str]] = None,
        user_notes: Optional[List[str]] = None,
    ) -> list:
        """
        Extract entities from text (wrapper for compatibility with importers).

        Args:
            text: Text to extract entities from (abstract or full text)
            title: Paper title
            context: Research context (not used, for API compatibility)
            seed_concepts: User-provided concepts (from Zotero tags) to boost
            user_notes: User notes to include in extraction context

        Returns:
            List of ExtractedEntity objects
        """
        # Use extract_from_paper internally
        result = await self.extract_from_paper(
            title=title,
            abstract=text,
            paper_id=None,
            use_accurate_model=False,
            seed_concepts=seed_concepts,
            user_notes=user_notes,
        )

        # Convert dict result to list of ExtractedEntity
        entities = []

        for entity_type, entity_list in result.items():
            if entity_type in ("concepts", "methods", "findings", "problems", "innovations", "limitations", "datasets"):
                type_map = {
                    "concepts": EntityType.CONCEPT,
                    "methods": EntityType.METHOD,
                    "findings": EntityType.FINDING,
                    "problems": EntityType.PROBLEM,
                    "innovations": EntityType.INNOVATION,
                    "limitations": EntityType.LIMITATION,
                    "datasets": EntityType.DATASET,
                }
                for entity_data in entity_list:
                    if isinstance(entity_data, dict):
                        entities.append(ExtractedEntity(
                            name=entity_data.get("name", ""),
                            entity_type=type_map.get(entity_type, EntityType.CONCEPT),
                            description=entity_data.get("description", ""),
                            confidence=entity_data.get("confidence", 0.5),
                            source_paper_id=entity_data.get("source_paper_id"),
                            properties=entity_data.get("properties", {}),
                        ))
                    elif isinstance(entity_data, ExtractedEntity):
                        entities.append(entity_data)

        # Add seed concepts as high-confidence USER_TAG entities
        if seed_concepts:
            for tag in seed_concepts:
                # Check if tag already exists in extracted entities
                tag_normalized = tag.strip().lower()
                if not any(e.name == tag_normalized for e in entities):
                    entities.append(ExtractedEntity(
                        name=tag_normalized,
                        entity_type=EntityType.CONCEPT,
                        description=f"User-tagged concept from Zotero",
                        confidence=0.95,  # High confidence for user-provided tags
                        properties={"source": "zotero_tag", "user_provided": True},
                    ))

        return entities

    async def _llm_extraction(
        self,
        title: str,
        abstract: str,
        paper_id: Optional[str],
        use_accurate: bool,
        seed_concepts: Optional[List[str]] = None,
        user_notes: Optional[List[str]] = None,
    ) -> dict:
        """Extract entities using LLM with retry logic (BUG-031 Fix)."""
        # Build additional context from seed concepts and notes
        additional_context = ""
        if seed_concepts:
            additional_context += f"\nUser-tagged keywords: {', '.join(seed_concepts)}"
        if user_notes:
            # Truncate notes to avoid token overflow
            notes_text = " | ".join(n[:200] for n in user_notes[:3])
            additional_context += f"\nUser notes: {notes_text}"

        # Select prompt based on mode
        if self.use_fast_mode:
            prompt = FAST_EXTRACTION_PROMPT.format(
                title=title,
                abstract=abstract[:2000] + additional_context,
            )
        else:
            prompt = CONCEPT_CENTRIC_EXTRACTION_PROMPT.format(
                title=title,
                abstract=abstract[:3000] + additional_context,
            )

        # BUG-031 Fix: Add retry logic for resilience
        # PERF-011: Track timing for debugging long API calls
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                # PERF-011: Log before API call to track gaps
                api_start_time = time.time()
                logger.debug(f"PERF-011: Starting LLM API call for '{title[:40]}...' (attempt {attempt + 1})")

                # Try generate_json() first if available (BUG-031 Fix)
                if hasattr(self.llm, 'generate_json'):
                    try:
                        response = await self.llm.generate_json(
                            prompt,
                            max_tokens=1500,
                            temperature=0.1,
                        )
                        # PERF-011: Log API call timing
                        api_elapsed = time.time() - api_start_time
                        if api_elapsed > SLOW_API_THRESHOLD:
                            logger.warning(f"PERF-011: Slow LLM API call: {api_elapsed:.1f}s for '{title[:40]}...'")

                        # generate_json returns dict directly
                        if isinstance(response, dict) and response:
                            result = self._parse_json_data(response, paper_id)
                            logger.info(
                                f"Extracted from '{title[:40]}...' ({api_elapsed:.1f}s): "
                                f"{len(result['concepts'])} concepts, "
                                f"{len(result['methods'])} methods, "
                                f"{len(result['findings'])} findings"
                            )
                            return result
                    except Exception as json_err:
                        logger.debug(f"generate_json() failed, falling back to generate(): {json_err}")

                # Fallback to generate() with manual JSON parsing
                # PERF-011: Reset timer for generate() fallback
                if not hasattr(self.llm, 'generate_json'):
                    api_start_time = time.time()
                    logger.debug(f"PERF-011: Starting LLM generate() for '{title[:40]}...'")

                response = await self.llm.generate(
                    prompt,
                    max_tokens=1500,
                    temperature=0.1,
                    use_accurate=use_accurate,
                )

                # PERF-011: Log API call timing for generate()
                api_elapsed = time.time() - api_start_time
                if api_elapsed > SLOW_API_THRESHOLD:
                    logger.warning(f"PERF-011: Slow LLM generate() call: {api_elapsed:.1f}s for '{title[:40]}...'")

                # Parse response
                result = self._parse_llm_response(response, paper_id)

                # PERF-013: Accept valid responses even if empty (prevent unnecessary retries)
                # A valid response with no entities is better than retrying and hitting rate limits
                if result is not None:
                    if result['concepts'] or result['methods'] or result['findings']:
                        logger.info(
                            f"Extracted from '{title[:40]}...' ({api_elapsed:.1f}s): "
                            f"{len(result['concepts'])} concepts, "
                            f"{len(result['methods'])} methods, "
                            f"{len(result['findings'])} findings"
                        )
                    else:
                        # PERF-013: Empty but valid result - don't retry
                        logger.info(f"No entities in '{title[:40]}...' ({api_elapsed:.1f}s, valid response)")
                    return result

                # Only retry if result is None (actual failure)
                if attempt < MAX_RETRIES:
                    logger.warning(f"Null result, retrying ({attempt + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue

            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    logger.warning(f"LLM extraction attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error(f"All LLM extraction attempts failed: {e}")

        # All retries exhausted, return empty result
        if last_error:
            logger.error(f"LLM extraction failed after {MAX_RETRIES + 1} attempts: {last_error}")
        return self._empty_result()

    def _extract_json_from_text(self, text: str) -> Optional[dict]:
        """
        BUG-031 Fix: Extract JSON from LLM response using multiple strategies.

        Strategies (in order):
        1. Direct JSON parse (if response is pure JSON)
        2. Code block extraction (```json ... ```)
        3. Greedy brace matching (first { to last })
        4. Relaxed brace matching (any valid JSON object)

        Returns:
            Parsed JSON dict or None if extraction fails
        """
        if not text or not text.strip():
            return None

        text = text.strip()

        # Handle if already a dict (from generate_json)
        if isinstance(text, dict):
            return text

        # Strategy 1: Try direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from code block (```json ... ``` or ``` ... ```)
        code_block_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Strategy 3: Greedy brace matching (first { to last })
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(text[first_brace:last_brace + 1])
            except json.JSONDecodeError:
                pass

        # Strategy 4: Find any valid JSON object using regex
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested objects
            r'\{[\s\S]*?\}',  # Any JSON-like structure
        ]
        for pattern in json_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, dict) and any(k in parsed for k in ['concepts', 'methods', 'findings']):
                        return parsed
                except json.JSONDecodeError:
                    continue

        logger.warning(f"Failed to extract JSON from response (length={len(text)})")
        return None

    def _parse_json_data(self, data: dict, paper_id: Optional[str]) -> dict:
        """
        BUG-031 Fix: Parse already-extracted JSON data into structured entities.
        Separated from _parse_llm_response for use with generate_json().

        v0.6.0 Fix: Validates all expected keys are present and logs missing categories.
        """
        result = self._empty_result()

        if not data or not isinstance(data, dict):
            return result

        # v0.6.0: Validate all expected keys are present
        expected_keys = {'concepts', 'methods', 'findings', 'problems', 'innovations', 'limitations', 'datasets'}
        missing_keys = expected_keys - set(data.keys())
        if missing_keys:
            logger.warning(f"Entity extraction missing categories: {missing_keys}")
            for key in missing_keys:
                data[key] = []

        # Log extraction distribution for monitoring
        non_empty_counts = {k: len(v) for k, v in data.items() if isinstance(v, list) and len(v) > 0}
        if non_empty_counts:
            logger.debug(f"Extraction distribution: {non_empty_counts}")

        try:
            # Parse concepts (primary nodes)
            for c in data.get("concepts", [])[:10]:
                if not c.get("name"):
                    continue
                result["concepts"].append(
                    ExtractedEntity(
                        entity_type=EntityType.CONCEPT,
                        name=c.get("name", ""),
                        definition=c.get("definition", ""),
                        description=c.get("description", ""),
                        confidence=float(c.get("confidence", 0.7)),
                        source_paper_id=paper_id,
                    )
                )

            # Parse methods
            for m in data.get("methods", [])[:5]:
                if not m.get("name"):
                    continue
                result["methods"].append(
                    ExtractedEntity(
                        entity_type=EntityType.METHOD,
                        name=m.get("name", ""),
                        description=m.get("description", ""),
                        confidence=float(m.get("confidence", 0.7)),
                        source_paper_id=paper_id,
                        properties={"type": m.get("type", "unknown")},
                    )
                )

            # Parse findings
            for f in data.get("findings", [])[:5]:
                if not f.get("name"):
                    continue
                result["findings"].append(
                    ExtractedEntity(
                        entity_type=EntityType.FINDING,
                        name=f.get("name", ""),
                        description=f.get("description", ""),
                        confidence=float(f.get("confidence", 0.7)),
                        source_paper_id=paper_id,
                        properties={"effect_type": f.get("effect_type", "neutral")},
                    )
                )

            # Parse problems
            for p in data.get("problems", [])[:3]:
                if not p.get("name"):
                    continue
                result["problems"].append(
                    ExtractedEntity(
                        entity_type=EntityType.PROBLEM,
                        name=p.get("name", ""),
                        description=p.get("description", ""),
                        confidence=float(p.get("confidence", 0.7)),
                        source_paper_id=paper_id,
                    )
                )

            # Parse innovations
            for i in data.get("innovations", [])[:3]:
                if not i.get("name"):
                    continue
                result["innovations"].append(
                    ExtractedEntity(
                        entity_type=EntityType.INNOVATION,
                        name=i.get("name", ""),
                        description=i.get("description", ""),
                        confidence=float(i.get("confidence", 0.7)),
                        source_paper_id=paper_id,
                    )
                )

            # Parse limitations
            for l in data.get("limitations", [])[:3]:
                if not l.get("name"):
                    continue
                result["limitations"].append(
                    ExtractedEntity(
                        entity_type=EntityType.LIMITATION,
                        name=l.get("name", ""),
                        description=l.get("description", ""),
                        confidence=float(l.get("confidence", 0.7)),
                        source_paper_id=paper_id,
                    )
                )

            # Parse datasets
            for d in data.get("datasets", [])[:3]:
                if not d.get("name"):
                    continue
                result["datasets"].append(
                    ExtractedEntity(
                        entity_type=EntityType.DATASET,
                        name=d.get("name", ""),
                        description=d.get("description", ""),
                        confidence=float(d.get("confidence", 0.7)),
                        source_paper_id=paper_id,
                        properties={
                            "size": d.get("size", ""),
                            "domain": d.get("domain", ""),
                        },
                    )
                )

        except Exception as e:
            logger.error(f"Error parsing JSON data: {e}")

        return result

    def _parse_llm_response(self, response: str, paper_id: Optional[str]) -> dict:
        """
        Parse LLM response into structured entities.
        BUG-031 Fix: Delegates to improved JSON extraction and unified parsing.
        """
        # Extract JSON using improved multi-strategy approach
        data = self._extract_json_from_text(response)
        if not data:
            return self._empty_result()

        # Delegate to unified JSON parsing
        return self._parse_json_data(data, paper_id)

    def _fallback_extraction(
        self, title: str, abstract: str, paper_id: Optional[str]
    ) -> dict:
        """
        Keyword-based extraction fallback when LLM is unavailable.
        """
        text = f"{title} {abstract}".lower()
        result = self._empty_result()

        # Concept patterns (domain-agnostic academic concepts)
        concept_patterns = [
            # AI/ML concepts
            (r"\b(artificial intelligence|ai)\b", "artificial intelligence", "Computer systems that perform tasks requiring human intelligence"),
            (r"\b(machine learning|ml)\b", "machine learning", "Algorithms that learn from data"),
            (r"\b(deep learning)\b", "deep learning", "Neural network-based learning"),
            (r"\b(neural network)\b", "neural network", "Computing systems inspired by biological networks"),
            (r"\b(natural language processing|nlp)\b", "natural language processing", "Computer understanding of human language"),
            (r"\b(large language model|llm)\b", "large language model", "Large-scale text generation models"),
            (r"\b(generative ai|genai)\b", "generative ai", "AI that creates new content"),
            (r"\b(chatbot|conversational agent)\b", "chatbot", "Automated conversational systems"),
            (r"\b(transformer)\b", "transformer architecture", "Attention-based neural network architecture"),

            # Education concepts
            (r"\b(learning outcome)\b", "learning outcome", "Measurable results of educational activities"),
            (r"\b(student engagement)\b", "student engagement", "Student involvement in learning"),
            (r"\b(personalized learning)\b", "personalized learning", "Individualized educational approaches"),
            (r"\b(self-regulated learning)\b", "self-regulated learning", "Learner control over learning process"),
            (r"\b(cognitive load)\b", "cognitive load", "Mental effort required for learning"),
            (r"\b(formative assessment)\b", "formative assessment", "Ongoing evaluation for learning improvement"),

            # Research concepts
            (r"\b(effect size)\b", "effect size", "Magnitude of research effect"),
            (r"\b(statistical significance)\b", "statistical significance", "Probability-based evidence threshold"),
            (r"\b(validity)\b", "validity", "Accuracy of measurement or conclusions"),
            (r"\b(reliability)\b", "reliability", "Consistency of measurement"),
        ]

        # Method patterns
        method_patterns = [
            (r"\b(randomized controlled trial|rct)\b", "randomized controlled trial", "quantitative"),
            (r"\b(experimental study|experiment)\b", "experimental study", "quantitative"),
            (r"\b(quasi-experimental)\b", "quasi-experimental design", "quantitative"),
            (r"\b(meta-analysis)\b", "meta-analysis", "quantitative"),
            (r"\b(systematic review)\b", "systematic review", "mixed"),
            (r"\b(survey|questionnaire)\b", "survey", "quantitative"),
            (r"\b(interview)\b", "interview", "qualitative"),
            (r"\b(case study)\b", "case study", "qualitative"),
            (r"\b(mixed method)\b", "mixed methods", "mixed"),
            (r"\b(content analysis)\b", "content analysis", "qualitative"),
            (r"\b(regression analysis)\b", "regression analysis", "quantitative"),
            (r"\b(anova|analysis of variance)\b", "analysis of variance", "quantitative"),
        ]

        # Extract concepts
        for pattern, name, definition in concept_patterns:
            if re.search(pattern, text):
                result["concepts"].append(
                    ExtractedEntity(
                        entity_type=EntityType.CONCEPT,
                        name=name,
                        definition=definition,
                        confidence=0.6,
                        source_paper_id=paper_id,
                    )
                )

        # Extract methods
        for pattern, name, method_type in method_patterns:
            if re.search(pattern, text):
                result["methods"].append(
                    ExtractedEntity(
                        entity_type=EntityType.METHOD,
                        name=name,
                        confidence=0.6,
                        source_paper_id=paper_id,
                        properties={"type": method_type},
                    )
                )

        # Extract findings (pattern-based)
        finding_patterns = [
            (r"significantly (improved|increased|enhanced)", "significant improvement", "positive"),
            (r"significantly (decreased|reduced|declined)", "significant decrease", "negative"),
            (r"positive (effect|impact|correlation|relationship)", "positive effect", "positive"),
            (r"negative (effect|impact|correlation|relationship)", "negative effect", "negative"),
            (r"no significant (difference|effect|impact)", "no significant effect", "neutral"),
            (r"outperformed", "superior performance", "positive"),
        ]

        for pattern, name, effect_type in finding_patterns:
            if re.search(pattern, text):
                result["findings"].append(
                    ExtractedEntity(
                        entity_type=EntityType.FINDING,
                        name=name,
                        confidence=0.5,
                        source_paper_id=paper_id,
                        properties={"effect_type": effect_type},
                    )
                )
                break  # Only first finding

        # Limit results
        result["concepts"] = result["concepts"][:10]
        result["methods"] = result["methods"][:5]
        result["findings"] = result["findings"][:5]

        return result

    def _empty_result(self) -> dict:
        """Return empty result structure."""
        return {
            "concepts": [],
            "methods": [],
            "findings": [],
            "problems": [],
            "innovations": [],
            "limitations": [],
            "datasets": [],
        }

    async def batch_extract(
        self,
        papers: List[dict],
        batch_size: int = 10,
        progress_callback=None,
    ) -> List[dict]:
        """
        Extract entities from multiple papers in batches.

        Args:
            papers: List of dicts with 'title', 'abstract', 'paper_id'
            batch_size: Number of papers to process before progress update
            progress_callback: Optional callback(current, total)

        Returns:
            List of extraction results
        """
        results = []
        total = len(papers)

        for i, paper in enumerate(papers):
            result = await self.extract_from_paper(
                title=paper.get("title", ""),
                abstract=paper.get("abstract", ""),
                paper_id=paper.get("paper_id"),
            )
            results.append(result)

            if progress_callback and (i + 1) % batch_size == 0:
                progress_callback(i + 1, total)

        if progress_callback:
            progress_callback(total, total)

        return results

    def clear_cache(self):
        """Clear extraction cache."""
        self._extraction_cache.clear()
        logger.debug("Extraction cache cleared")

    async def extract_from_sections(
        self,
        sections: List[Dict],
        paper_id: Optional[str] = None,
    ) -> List:
        """
        Extract entities from paper sections using section-specific prompts.

        This method provides more accurate extraction by using prompts
        tailored to each section type (introduction, methodology, results, discussion).

        Args:
            sections: List of dicts with 'section_type', 'text', 'title' keys
                      (compatible with SemanticChunker Section output)
            paper_id: Optional paper ID for tracking source

        Returns:
            List of ExtractedEntity objects
        """
        all_entities = []

        for section in sections:
            section_type = section.get("section_type", "unknown").lower()
            text = section.get("text", "")

            if not text or len(text) < 50:
                continue

            # Get section-specific prompt or fall back to default
            if section_type in ("methodology", "methods"):
                prompt_template = SECTION_PROMPTS.get("methodology")
            elif section_type in ("results", "findings"):
                prompt_template = SECTION_PROMPTS.get("results")
            elif section_type in ("discussion", "conclusion"):
                prompt_template = SECTION_PROMPTS.get("discussion")
            elif section_type == "introduction":
                prompt_template = SECTION_PROMPTS.get("introduction")
            else:
                # Use fast extraction for other sections
                prompt_template = None

            if prompt_template and self.llm:
                try:
                    # Use section-specific prompt
                    prompt = prompt_template.format(text=text[:3000])

                    response = await self.llm.generate(
                        prompt,
                        max_tokens=1000,
                        temperature=0.1,
                    )

                    # Parse response
                    result = self._parse_llm_response(response, paper_id)

                    # Convert to entities with section metadata
                    for entity_type, entity_list in result.items():
                        for entity in entity_list:
                            if isinstance(entity, ExtractedEntity):
                                entity.properties["source_section"] = section_type
                                all_entities.append(entity)

                    logger.debug(f"Extracted {len(result)} entity types from {section_type} section")

                except Exception as e:
                    logger.warning(f"Section extraction failed for {section_type}: {e}")
            else:
                # Fall back to general extraction
                result = await self.extract_from_paper(
                    title=section.get("title", ""),
                    abstract=text[:2000],
                    paper_id=paper_id,
                )

                for entity_type, entity_list in result.items():
                    for entity in entity_list:
                        if isinstance(entity, ExtractedEntity):
                            entity.properties["source_section"] = section_type
                            all_entities.append(entity)

        # Deduplicate entities by name
        seen_names = set()
        unique_entities = []
        for entity in all_entities:
            if entity.name not in seen_names:
                seen_names.add(entity.name)
                unique_entities.append(entity)

        logger.info(f"Section-aware extraction: {len(unique_entities)} unique entities from {len(sections)} sections")

        return unique_entities


# ============================================================================
# Entity Disambiguator (NLP-AKG style)
# ============================================================================

class EntityDisambiguator:
    """
    Disambiguates extracted entities using embedding similarity.

    Groups similar entities and selects canonical names.
    Prevents duplicate concepts like "AI" and "artificial intelligence".
    """

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self._canonical_map: Dict[str, str] = {}

    def add_synonym(self, canonical: str, *synonyms: str):
        """Add manual synonym mapping."""
        for syn in synonyms:
            self._canonical_map[syn.lower()] = canonical.lower()

    def get_canonical_name(self, name: str) -> str:
        """Get canonical name for an entity."""
        name_lower = name.lower().strip()

        # Check manual mappings first
        if name_lower in self._canonical_map:
            return self._canonical_map[name_lower]

        return name_lower

    def disambiguate_entities(
        self, entities: List[ExtractedEntity]
    ) -> List[ExtractedEntity]:
        """
        Merge duplicate entities, keeping highest confidence.

        Returns deduplicated list with merged source papers.
        """
        # Group by canonical name
        entity_groups: Dict[str, List[ExtractedEntity]] = {}

        for entity in entities:
            canonical = self.get_canonical_name(entity.name)
            if canonical not in entity_groups:
                entity_groups[canonical] = []
            entity_groups[canonical].append(entity)

        # Merge groups
        result = []
        for canonical, group in entity_groups.items():
            # Take entity with highest confidence
            best = max(group, key=lambda e: e.confidence)

            # Merge source papers
            all_sources = set()
            for e in group:
                if e.source_paper_id:
                    all_sources.add(e.source_paper_id)

            # Create merged entity
            merged = ExtractedEntity(
                entity_type=best.entity_type,
                name=canonical,
                definition=best.definition,
                description=best.description,
                confidence=max(e.confidence for e in group),
                source_paper_id=None,  # Will be stored as array
                properties={
                    **best.properties,
                    "source_count": len(all_sources),
                    "source_paper_ids": list(all_sources),
                },
            )
            result.append(merged)

        return result


# Pre-configured synonyms for academic concepts
DEFAULT_SYNONYMS = [
    ("artificial intelligence", "ai", "A.I."),
    ("machine learning", "ml", "M.L."),
    ("natural language processing", "nlp", "N.L.P."),
    ("large language model", "llm", "L.L.M.", "large language models"),
    ("randomized controlled trial", "rct", "R.C.T."),
    ("chatbot", "chat bot", "conversational agent", "dialogue system"),
    ("deep learning", "dl", "D.L."),
    ("neural network", "nn", "neural net", "neural networks"),
]


def create_default_disambiguator() -> EntityDisambiguator:
    """Create disambiguator with default academic synonyms."""
    disambiguator = EntityDisambiguator()
    for synonyms in DEFAULT_SYNONYMS:
        canonical = synonyms[0]
        disambiguator.add_synonym(canonical, *synonyms[1:])
    return disambiguator
