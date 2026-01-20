"""
Semantic Chunking Pipeline for Academic Papers

Implements hierarchical chunking strategy:
1. Section Detection: Identify Introduction, Methods, Results, Discussion
2. Parent Chunks: Full section content
3. Child Chunks: Paragraph-level chunks (~400 tokens)

Reference: "Chunking Strategies for RAG" (LangChain best practices)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class SectionType(str, Enum):
    """Academic paper section types."""
    TITLE = "title"
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    BACKGROUND = "background"
    LITERATURE_REVIEW = "literature_review"
    METHODOLOGY = "methodology"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    APPENDIX = "appendix"
    ACKNOWLEDGMENTS = "acknowledgments"
    UNKNOWN = "unknown"


# Section header patterns (case-insensitive)
SECTION_PATTERNS = {
    SectionType.ABSTRACT: [
        r'^abstract\s*$',
        r'^summary\s*$',
    ],
    SectionType.INTRODUCTION: [
        r'^1\.?\s*introduction',
        r'^introduction\s*$',
        r'^i\.?\s*introduction',
    ],
    SectionType.BACKGROUND: [
        r'^2\.?\s*background',
        r'^background\s*$',
        r'^theoretical\s+background',
        r'^related\s+work',
    ],
    SectionType.LITERATURE_REVIEW: [
        r'^literature\s+review',
        r'^review\s+of\s+literature',
        r'^prior\s+work',
    ],
    SectionType.METHODOLOGY: [
        r'^\d+\.?\s*method',
        r'^method(s|ology)?\s*$',
        r'^research\s+method',
        r'^materials?\s+and\s+methods?',
        r'^experimental\s+(design|setup|method)',
        r'^\d+\.?\s*materials?\s+and\s+method',
    ],
    SectionType.RESULTS: [
        r'^\d+\.?\s*results?',
        r'^results?\s*$',
        r'^findings?\s*$',
        r'^results?\s+and\s+discussion',
    ],
    SectionType.DISCUSSION: [
        r'^\d+\.?\s*discussion',
        r'^discussion\s*$',
        r'^analysis\s*$',
        r'^general\s+discussion',
    ],
    SectionType.CONCLUSION: [
        r'^\d+\.?\s*conclusion',
        r'^conclusion(s)?\s*$',
        r'^concluding\s+remarks',
        r'^summary\s+and\s+conclusion',
        r'^summary\s*$',
    ],
    SectionType.REFERENCES: [
        r'^references?\s*$',
        r'^bibliography\s*$',
        r'^works?\s+cited',
    ],
    SectionType.APPENDIX: [
        r'^appendix',
        r'^appendices',
        r'^supplementary',
    ],
    SectionType.ACKNOWLEDGMENTS: [
        r'^acknowledgment',
        r'^acknowledgement',
    ],
}


@dataclass
class Section:
    """Represents a detected section in the paper."""
    section_type: SectionType
    title: str
    content: str
    start_line: int
    end_line: int
    level: int = 1  # Section hierarchy level (1=main, 2=subsection)


@dataclass
class Chunk:
    """Represents a text chunk for RAG."""
    text: str
    section_type: SectionType
    chunk_level: int  # 0=parent (full section), 1=child (paragraph)
    parent_id: Optional[str] = None
    sequence_order: int = 0
    token_count: int = 0
    metadata: Dict = field(default_factory=dict)
    
    @property
    def id(self) -> str:
        """Generate a unique ID for the chunk."""
        import hashlib
        content_hash = hashlib.md5(self.text[:100].encode()).hexdigest()[:8]
        return f"{self.section_type.value}_{self.chunk_level}_{self.sequence_order}_{content_hash}"


class AcademicSectionParser:
    """
    Parse academic papers into structured sections.
    
    Uses regex patterns + heuristics to detect section boundaries.
    Falls back to paragraph-based chunking for non-standard papers.
    """
    
    def __init__(self):
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[SectionType, List[re.Pattern]]:
        """Compile section patterns for efficiency."""
        compiled = {}
        for section_type, patterns in SECTION_PATTERNS.items():
            compiled[section_type] = [
                re.compile(p, re.IGNORECASE | re.MULTILINE)
                for p in patterns
            ]
        return compiled
    
    def detect_section_type(self, line: str) -> Optional[SectionType]:
        """Detect if a line is a section header."""
        line = line.strip()
        
        # Skip very short or very long lines
        if len(line) < 3 or len(line) > 100:
            return None
        
        # Check against all patterns
        for section_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.match(line):
                    return section_type
        
        return None
    
    def parse_text(self, text: str) -> List[Section]:
        """
        Parse text into sections.
        
        Args:
            text: Full text of the paper
            
        Returns:
            List of Section objects
        """
        lines = text.split('\n')
        sections = []
        current_section = None
        current_content = []
        current_start = 0
        
        for i, line in enumerate(lines):
            section_type = self.detect_section_type(line)
            
            if section_type:
                # Save previous section
                if current_section:
                    sections.append(Section(
                        section_type=current_section,
                        title=lines[current_start].strip(),
                        content='\n'.join(current_content).strip(),
                        start_line=current_start,
                        end_line=i - 1,
                    ))
                
                # Start new section
                current_section = section_type
                current_content = []
                current_start = i
            else:
                current_content.append(line)
        
        # Save last section
        if current_section and current_content:
            sections.append(Section(
                section_type=current_section,
                title=lines[current_start].strip() if current_start < len(lines) else "",
                content='\n'.join(current_content).strip(),
                start_line=current_start,
                end_line=len(lines) - 1,
            ))
        
        # If no sections detected, create a single UNKNOWN section
        if not sections and text.strip():
            sections.append(Section(
                section_type=SectionType.UNKNOWN,
                title="",
                content=text.strip(),
                start_line=0,
                end_line=len(lines) - 1,
            ))
        
        return sections


class HierarchicalChunker:
    """
    Create hierarchical chunks from parsed sections.
    
    Strategy:
    - Parent chunks: Full section content (for context retrieval)
    - Child chunks: Paragraph-level (~400 tokens, for precise retrieval)
    """
    
    def __init__(
        self,
        target_chunk_tokens: int = 400,
        overlap_tokens: int = 50,
        min_chunk_tokens: int = 100,
    ):
        self.target_chunk_tokens = target_chunk_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_tokens = min_chunk_tokens
        
        # Try to import tiktoken for accurate token counting
        try:
            import tiktoken
            self._encoder = tiktoken.get_encoding("cl100k_base")
            self._use_tiktoken = True
        except ImportError:
            self._encoder = None
            self._use_tiktoken = False
            logger.warning("tiktoken not available, using approximate token counting")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self._use_tiktoken and self._encoder:
            return len(self._encoder.encode(text))
        else:
            # Approximate: ~4 characters per token
            return len(text) // 4
    
    def chunk_section(self, section: Section) -> List[Chunk]:
        """
        Create hierarchical chunks from a section.
        
        Returns:
            List of Chunk objects (1 parent + N children)
        """
        chunks = []
        
        # Create parent chunk (full section)
        parent_chunk = Chunk(
            text=section.content,
            section_type=section.section_type,
            chunk_level=0,
            sequence_order=0,
            token_count=self.count_tokens(section.content),
            metadata={
                "title": section.title,
                "start_line": section.start_line,
                "end_line": section.end_line,
            }
        )
        chunks.append(parent_chunk)
        
        # Create child chunks (paragraph-level)
        paragraphs = self._split_into_paragraphs(section.content)
        child_chunks = self._merge_paragraphs_to_chunks(paragraphs, parent_chunk.id)
        
        for i, child in enumerate(child_chunks):
            child.section_type = section.section_type
            child.sequence_order = i + 1
            chunks.append(child)
        
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split on double newlines or single newlines followed by indent
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _merge_paragraphs_to_chunks(
        self,
        paragraphs: List[str],
        parent_id: str
    ) -> List[Chunk]:
        """
        Merge small paragraphs into target-sized chunks.
        
        Uses a greedy algorithm:
        1. Accumulate paragraphs until target size reached
        2. Add overlap from previous chunk
        """
        chunks = []
        current_text = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self.count_tokens(para)
            
            # If adding this paragraph exceeds target, save current chunk
            if current_text and current_tokens + para_tokens > self.target_chunk_tokens:
                chunk_text = '\n\n'.join(current_text)
                chunks.append(Chunk(
                    text=chunk_text,
                    section_type=SectionType.UNKNOWN,  # Will be set by caller
                    chunk_level=1,
                    parent_id=parent_id,
                    token_count=current_tokens,
                ))
                
                # Keep overlap
                overlap_text = current_text[-1] if current_text else ""
                current_text = [overlap_text] if self.count_tokens(overlap_text) <= self.overlap_tokens else []
                current_tokens = self.count_tokens('\n\n'.join(current_text))
            
            current_text.append(para)
            current_tokens += para_tokens
        
        # Save remaining
        if current_text and current_tokens >= self.min_chunk_tokens:
            chunk_text = '\n\n'.join(current_text)
            chunks.append(Chunk(
                text=chunk_text,
                section_type=SectionType.UNKNOWN,
                chunk_level=1,
                parent_id=parent_id,
                token_count=current_tokens,
            ))
        
        return chunks


class SemanticChunker:
    """
    Main entry point for semantic chunking pipeline.
    
    Usage:
        chunker = SemanticChunker()
        chunks = chunker.process_text(full_text)
        # or
        chunks = chunker.process_pdf(pdf_path)
    """
    
    def __init__(
        self,
        target_chunk_tokens: int = 400,
        overlap_tokens: int = 50,
    ):
        self.section_parser = AcademicSectionParser()
        self.hierarchical_chunker = HierarchicalChunker(
            target_chunk_tokens=target_chunk_tokens,
            overlap_tokens=overlap_tokens,
        )
    
    def process_text(self, text: str) -> List[Chunk]:
        """
        Process text into hierarchical chunks.
        
        Args:
            text: Full text of the paper
            
        Returns:
            List of Chunk objects
        """
        # Parse into sections
        sections = self.section_parser.parse_text(text)
        logger.info(f"Detected {len(sections)} sections: {[s.section_type.value for s in sections]}")
        
        # Create chunks for each section
        all_chunks = []
        for section in sections:
            chunks = self.hierarchical_chunker.chunk_section(section)
            all_chunks.extend(chunks)
        
        logger.info(
            f"Created {len(all_chunks)} chunks: "
            f"{sum(1 for c in all_chunks if c.chunk_level == 0)} parents, "
            f"{sum(1 for c in all_chunks if c.chunk_level == 1)} children"
        )
        
        return all_chunks
    
    def process_pdf(self, pdf_path: str) -> List[Chunk]:
        """
        Process PDF file into hierarchical chunks.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of Chunk objects
        """
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page in doc:
                full_text += page.get_text() + "\n"
            
            doc.close()
            
            return self.process_text(full_text)
            
        except ImportError:
            logger.error("PyMuPDF (fitz) not installed. Install with: pip install pymupdf")
            raise
        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}")
            raise
    
    def get_section_summary(self, chunks: List[Chunk]) -> Dict[str, int]:
        """
        Get summary of chunks by section type.
        
        Returns:
            Dict mapping section type to chunk count
        """
        summary = {}
        for chunk in chunks:
            section = chunk.section_type.value
            summary[section] = summary.get(section, 0) + 1
        return summary

    def chunk_academic_text(
        self,
        text: str,
        paper_id: str,
        detect_sections: bool = True,
        max_chunk_tokens: int = 400,
    ) -> Dict[str, Any]:
        """
        Chunk academic text with section detection.
        
        This is the main interface for the import pipeline.
        
        Args:
            text: Full text of the paper
            paper_id: ID of the paper for linking
            detect_sections: Whether to detect academic sections
            max_chunk_tokens: Maximum tokens per child chunk
            
        Returns:
            Dict containing:
                - chunks: List of chunk dicts ready for storage
                - sections: List of detected sections
                - summary: Section type counts
        """
        # Process text to get Chunk objects
        chunks = self.process_text(text)
        
        # Get sections from parser
        sections = self.section_parser.parse_text(text) if detect_sections else []
        
        # Convert Chunk objects to dicts for storage
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                "text": chunk.text,
                "section_type": chunk.section_type.value,
                "chunk_level": 0 if chunk.parent_id is None else 1,
                "parent_id": chunk.parent_id,
                "sequence_order": chunk.sequence_order,
                "token_count": chunk.token_count,
                "paper_id": paper_id,
            }
            chunk_dicts.append(chunk_dict)
        
        # Convert Section objects to dicts
        section_dicts = []
        for sec in sections:
            section_dicts.append({
                "type": sec.section_type,
                "title": sec.title,
                "content": sec.content,
            })
        
        return {
            "chunks": chunk_dicts,
            "sections": section_dicts,
            "summary": self.get_section_summary(chunks),
        }


# Convenience function
def chunk_academic_text(
    text: str,
    target_tokens: int = 400,
    overlap_tokens: int = 50,
) -> List[Chunk]:
    """
    Convenience function to chunk academic text.
    
    Args:
        text: Full text of academic paper
        target_tokens: Target size for child chunks
        overlap_tokens: Overlap between chunks
        
    Returns:
        List of Chunk objects
    """
    chunker = SemanticChunker(
        target_chunk_tokens=target_tokens,
        overlap_tokens=overlap_tokens,
    )
    return chunker.process_text(text)
