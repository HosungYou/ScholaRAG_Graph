"""
Hierarchical Retriever for Semantic Chunks

Implements a two-stage retrieval strategy:
1. Search child chunks (precise, paragraph-level)
2. Expand to parent chunks (context, section-level)

This approach balances precision (finding exact relevant passages)
with context (understanding the broader section).

Reference: "Parent Document Retriever" pattern from LangChain
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from enum import Enum

logger = logging.getLogger(__name__)


class RetrievalMode(str, Enum):
    """Retrieval strategy modes."""
    CHILD_ONLY = "child_only"  # Return only matched child chunks
    PARENT_EXPAND = "parent_expand"  # Expand to parent context
    HYBRID = "hybrid"  # Return both child and parent


@dataclass
class RetrievalResult:
    """Result from hierarchical retrieval."""
    chunk_id: str
    text: str
    section_type: str
    chunk_level: int  # 0=parent, 1=child
    score: float
    paper_id: Optional[str] = None
    paper_title: Optional[str] = None
    parent_id: Optional[str] = None
    parent_text: Optional[str] = None  # Populated if expand_to_parent=True
    metadata: Dict = field(default_factory=dict)
    
    @property
    def is_parent(self) -> bool:
        return self.chunk_level == 0
    
    @property
    def is_child(self) -> bool:
        return self.chunk_level == 1


@dataclass
class RetrievalContext:
    """Aggregated context from multiple retrievals."""
    results: List[RetrievalResult]
    total_tokens: int = 0
    sections_covered: Set[str] = field(default_factory=set)
    papers_covered: Set[str] = field(default_factory=set)
    
    def get_context_text(self, max_tokens: int = 4000) -> str:
        """Get concatenated context text within token limit."""
        texts = []
        current_tokens = 0
        
        for result in sorted(self.results, key=lambda x: x.score, reverse=True):
            # Use parent text if available, otherwise child text
            text = result.parent_text or result.text
            # Rough token estimate
            tokens = len(text) // 4
            
            if current_tokens + tokens > max_tokens:
                break
            
            texts.append(f"[{result.section_type}] {text}")
            current_tokens += tokens
        
        return "\n\n---\n\n".join(texts)


class HierarchicalRetriever:
    """
    Hierarchical retriever for semantic chunks.
    
    Features:
    - Child chunk search (precise paragraph-level matching)
    - Parent context expansion (section-level context)
    - Section filtering (focus on specific paper sections)
    - Score-based ranking with reranking support
    """
    
    def __init__(
        self,
        db=None,
        graph_store=None,
        embedding_provider=None,
        default_mode: RetrievalMode = RetrievalMode.PARENT_EXPAND,
        default_top_k: int = 5,
    ):
        """
        Initialize hierarchical retriever.
        
        Args:
            db: Database connection (asyncpg pool or similar)
            graph_store: GraphStore instance (alternative to db)
            embedding_provider: Embedding provider (Cohere or SPECTER2)
            default_mode: Default retrieval mode
            default_top_k: Default number of results to return
        """
        # Support both direct db connection and graph_store
        if graph_store is not None:
            self.db = getattr(graph_store, 'db', None)
            self.graph_store = graph_store
        else:
            self.db = db
            self.graph_store = None
        
        self.embedding_provider = embedding_provider
        self.default_mode = default_mode
        self.default_top_k = default_top_k
    
    async def search(
        self,
        query: str,
        project_id: str,
        top_k: Optional[int] = None,
        mode: Optional[RetrievalMode] = None,
        section_filter: Optional[List[str]] = None,
        min_score: float = 0.5,
        expand_to_parent: bool = True,
    ) -> List[RetrievalResult]:
        """
        Search semantic chunks with hierarchical context.
        
        Args:
            query: Search query text
            project_id: Project UUID to search within
            top_k: Number of results to return
            mode: Retrieval mode (child_only, parent_expand, hybrid)
            section_filter: List of section types to include
                           (e.g., ["methodology", "results"])
            min_score: Minimum similarity score threshold
            expand_to_parent: Whether to fetch parent context for children
            
        Returns:
            List of RetrievalResult objects
        """
        top_k = top_k or self.default_top_k
        mode = mode or self.default_mode
        
        # Generate query embedding
        if not self.embedding_provider:
            raise ValueError("Embedding provider required for search")
        
        query_embedding = await self.embedding_provider.get_embedding(
            query, input_type="search_query"
        )
        
        # Build SQL query
        sql = self._build_search_query(
            project_id=project_id,
            section_filter=section_filter,
            top_k=top_k * 2,  # Get more for filtering
        )
        
        # Execute search
        if self.db:
            rows = await self.db.fetch(sql, query_embedding, project_id, min_score)
        else:
            logger.warning("No database connection - returning empty results")
            return []
        
        # Process results
        results = []
        seen_parents = set()
        
        for row in rows:
            result = RetrievalResult(
                chunk_id=str(row["id"]),
                text=row["text"],
                section_type=row["section_type"],
                chunk_level=row["chunk_level"],
                score=float(row["similarity"]),
                paper_id=str(row["paper_id"]) if row.get("paper_id") else None,
                parent_id=str(row["parent_chunk_id"]) if row.get("parent_chunk_id") else None,
                metadata={
                    "token_count": row.get("token_count"),
                    "sequence_order": row.get("sequence_order"),
                }
            )
            
            results.append(result)
        
        # Expand to parent context if requested
        if expand_to_parent and mode in (RetrievalMode.PARENT_EXPAND, RetrievalMode.HYBRID):
            results = await self._expand_to_parents(results)
        
        # Deduplicate and limit
        results = self._deduplicate_results(results, top_k)
        
        logger.info(
            f"Retrieved {len(results)} chunks for query: '{query[:50]}...' "
            f"(sections: {set(r.section_type for r in results)})"
        )
        
        return results
    
    def _build_search_query(
        self,
        project_id: str,
        section_filter: Optional[List[str]],
        top_k: int,
    ) -> str:
        """Build the vector similarity search SQL query."""
        
        # Base query with vector similarity
        sql = """
        SELECT 
            sc.id,
            sc.text,
            sc.section_type,
            sc.chunk_level,
            sc.parent_chunk_id,
            sc.paper_id,
            sc.token_count,
            sc.sequence_order,
            1 - (sc.embedding <=> $1::vector) AS similarity
        FROM semantic_chunks sc
        WHERE sc.project_id = $2
          AND sc.embedding IS NOT NULL
          AND 1 - (sc.embedding <=> $1::vector) >= $3
        """
        
        # Add section filter if specified
        if section_filter:
            section_list = ", ".join(f"'{s}'" for s in section_filter)
            sql += f"\n  AND sc.section_type IN ({section_list})"
        
        # Prefer child chunks (more precise) but include parents
        sql += """
        ORDER BY 
            similarity DESC,
            sc.chunk_level DESC  -- Children first
        LIMIT """ + str(top_k)
        
        return sql
    
    async def _expand_to_parents(
        self,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """Expand child chunks to include parent context."""
        
        # Collect parent IDs to fetch
        parent_ids = {r.parent_id for r in results if r.parent_id and r.is_child}
        
        if not parent_ids or not self.db:
            return results
        
        # Fetch parent texts
        parent_sql = """
        SELECT id, text FROM semantic_chunks
        WHERE id = ANY($1::uuid[])
        """
        
        try:
            parent_rows = await self.db.fetch(parent_sql, list(parent_ids))
            parent_texts = {str(row["id"]): row["text"] for row in parent_rows}
            
            # Attach parent text to children
            for result in results:
                if result.parent_id and result.parent_id in parent_texts:
                    result.parent_text = parent_texts[result.parent_id]
            
        except Exception as e:
            logger.warning(f"Failed to fetch parent contexts: {e}")
        
        return results
    
    def _deduplicate_results(
        self,
        results: List[RetrievalResult],
        top_k: int,
    ) -> List[RetrievalResult]:
        """Deduplicate results, preferring higher scores."""
        
        seen_texts = set()
        deduplicated = []
        
        for result in sorted(results, key=lambda x: x.score, reverse=True):
            # Use first 100 chars as dedup key
            text_key = result.text[:100].lower()
            
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                deduplicated.append(result)
            
            if len(deduplicated) >= top_k:
                break
        
        return deduplicated
    
    async def search_by_section(
        self,
        query: str,
        project_id: str,
        sections: List[str],
        top_k_per_section: int = 2,
    ) -> Dict[str, List[RetrievalResult]]:
        """
        Search within specific sections, returning results grouped by section.
        
        Useful for structured queries like:
        "What methods were used?" -> search methodology section
        "What were the findings?" -> search results section
        
        Args:
            query: Search query
            project_id: Project UUID
            sections: List of section types to search
            top_k_per_section: Results per section
            
        Returns:
            Dict mapping section type to results
        """
        results_by_section = {}
        
        # Search each section in parallel
        tasks = []
        for section in sections:
            tasks.append(
                self.search(
                    query=query,
                    project_id=project_id,
                    top_k=top_k_per_section,
                    section_filter=[section],
                )
            )
        
        section_results = await asyncio.gather(*tasks)
        
        for section, results in zip(sections, section_results):
            results_by_section[section] = results
        
        return results_by_section
    
    async def get_context(
        self,
        query: str,
        project_id: str,
        max_tokens: int = 4000,
        section_filter: Optional[List[str]] = None,
    ) -> RetrievalContext:
        """
        Get aggregated context for RAG generation.
        
        Convenience method that returns a RetrievalContext object
        with concatenated text ready for LLM input.
        
        Args:
            query: Search query
            project_id: Project UUID
            max_tokens: Maximum tokens in context
            section_filter: Optional section filter
            
        Returns:
            RetrievalContext with results and aggregated text
        """
        results = await self.search(
            query=query,
            project_id=project_id,
            top_k=10,  # Get more for token budgeting
            section_filter=section_filter,
            expand_to_parent=True,
        )
        
        context = RetrievalContext(
            results=results,
            sections_covered={r.section_type for r in results},
            papers_covered={r.paper_id for r in results if r.paper_id},
        )
        
        # Calculate total tokens
        for result in results:
            text = result.parent_text or result.text
            context.total_tokens += len(text) // 4
        
        return context


# Section-aware query routing
SECTION_QUERY_PATTERNS = {
    "methodology": [
        "method", "approach", "technique", "how did", "procedure",
        "data collection", "sample", "participants", "instrument",
    ],
    "results": [
        "finding", "result", "outcome", "effect", "impact",
        "significant", "correlation", "difference", "showed",
    ],
    "discussion": [
        "implication", "limitation", "future", "suggest",
        "conclude", "recommendation", "contribution",
    ],
    "introduction": [
        "background", "context", "purpose", "objective",
        "research question", "gap", "motivation",
    ],
}


def suggest_sections_for_query(query: str) -> List[str]:
    """
    Suggest relevant sections based on query keywords.
    
    Args:
        query: User query
        
    Returns:
        List of suggested section types
    """
    query_lower = query.lower()
    suggestions = []
    
    for section, keywords in SECTION_QUERY_PATTERNS.items():
        if any(kw in query_lower for kw in keywords):
            suggestions.append(section)
    
    # Default to all main sections if no match
    if not suggestions:
        suggestions = ["introduction", "methodology", "results", "discussion"]
    
    return suggestions
