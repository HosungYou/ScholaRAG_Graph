"""
SPECTER2 Embedding Provider for Academic Papers

SPECTER2 is a scientific document embedding model from AllenAI that:
- Is specifically trained on academic papers
- Produces 768-dimensional embeddings
- Excels at finding semantically similar papers
- Works well with title + abstract concatenation

Reference: https://huggingface.co/allenai/specter2

Usage:
    provider = SpecterEmbeddingProvider()
    embeddings = await provider.get_embeddings(["Paper title. Abstract text..."])
"""

import asyncio
import logging
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound operations
_executor = ThreadPoolExecutor(max_workers=2)


class SpecterEmbeddingProvider:
    """
    SPECTER2 embedding provider for academic document embeddings.
    
    Uses AllenAI's SPECTER2 model via sentence-transformers.
    Optimized for academic papers (title + abstract).
    
    Dimension: 768 (fixed by model architecture)
    """
    
    DIMENSION = 768
    MODEL_NAME = "allenai/specter2"
    
    # Alternative models
    MODELS = {
        "specter2": "allenai/specter2",
        "specter2_base": "allenai/specter2_base",
        "scibert": "allenai/scibert_scivocab_uncased",
    }
    
    def __init__(
        self,
        model_name: str = "specter2",
        device: Optional[str] = None,
        batch_size: int = 32,
    ):
        """
        Initialize SPECTER2 embedding provider.
        
        Args:
            model_name: Model to use ("specter2", "specter2_base", "scibert")
            device: Device to use ("cuda", "cpu", or None for auto)
            batch_size: Batch size for encoding
        """
        self.model_name = self.MODELS.get(model_name, model_name)
        self.device = device
        self.batch_size = batch_size
        self._model = None
        self._lock = asyncio.Lock()
    
    def _load_model(self):
        """Load the model (synchronous, called in thread pool)."""
        if self._model is not None:
            return self._model
        
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading SPECTER2 model: {self.model_name}")
            
            # Load model with device specification
            if self.device:
                self._model = SentenceTransformer(self.model_name, device=self.device)
            else:
                self._model = SentenceTransformer(self.model_name)
            
            logger.info(f"SPECTER2 model loaded on device: {self._model.device}")
            return self._model
            
        except ImportError:
            raise ImportError(
                "sentence-transformers package required for SPECTER2. "
                "Install with: pip install sentence-transformers torch"
            )
        except Exception as e:
            logger.error(f"Failed to load SPECTER2 model: {e}")
            raise
    
    def _encode_sync(self, texts: List[str]) -> List[List[float]]:
        """Synchronous encoding (runs in thread pool)."""
        model = self._load_model()
        
        # SPECTER2 works best with "title. abstract" format
        # No special preprocessing needed
        embeddings = model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,  # L2 normalize for cosine similarity
        )
        
        return embeddings.tolist()
    
    async def get_embeddings(
        self,
        texts: List[str],
        input_type: str = "search_document",  # Ignored, for API compatibility
        model: Optional[str] = None,  # Ignored, for API compatibility
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed (ideally "title. abstract" format)
            input_type: Ignored (for Cohere API compatibility)
            model: Ignored (for Cohere API compatibility)
            
        Returns:
            List of 768-dimensional embedding vectors
        """
        if not texts:
            return []
        
        # Run encoding in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        
        async with self._lock:  # Ensure thread-safe model access
            try:
                embeddings = await loop.run_in_executor(
                    _executor,
                    self._encode_sync,
                    texts
                )
                
                logger.info(f"Generated {len(embeddings)} SPECTER2 embeddings")
                return embeddings
                
            except Exception as e:
                logger.error(f"SPECTER2 embedding error: {e}")
                raise
    
    async def get_embedding(
        self,
        text: str,
        input_type: str = "search_document"
    ) -> List[float]:
        """Get embedding for a single text."""
        embeddings = await self.get_embeddings([text], input_type=input_type)
        return embeddings[0] if embeddings else []
    
    @staticmethod
    def format_paper(title: str, abstract: str) -> str:
        """
        Format paper for SPECTER2 embedding.
        
        SPECTER2 works best with "title. abstract" format.
        
        Args:
            title: Paper title
            abstract: Paper abstract
            
        Returns:
            Formatted string for embedding
        """
        title = title.strip()
        abstract = abstract.strip()
        
        if title and abstract:
            return f"{title}. {abstract}"
        elif title:
            return title
        else:
            return abstract


class DualEmbeddingProvider:
    """
    Dual embedding provider combining Cohere and SPECTER2.
    
    Strategy:
    - SPECTER2: For chunk retrieval (academic-specific)
    - Cohere: For entity embeddings (general-purpose)
    
    This allows using the best model for each task:
    - Academic similarity: SPECTER2 (768d)
    - General semantic search: Cohere embed-v4.0 (1536d)
    """
    
    def __init__(
        self,
        cohere_api_key: Optional[str] = None,
        use_specter: bool = True,
        use_cohere: bool = True,
        specter_device: Optional[str] = None,
    ):
        """
        Initialize dual embedding provider.
        
        Args:
            cohere_api_key: Cohere API key (required if use_cohere=True)
            use_specter: Whether to use SPECTER2 embeddings
            use_cohere: Whether to use Cohere embeddings
            specter_device: Device for SPECTER2 ("cuda", "cpu", or None)
        """
        self.use_specter = use_specter
        self.use_cohere = use_cohere
        
        self._specter = None
        self._cohere = None
        
        if use_specter:
            self._specter = SpecterEmbeddingProvider(device=specter_device)
        
        if use_cohere and cohere_api_key:
            from .cohere_embeddings import CohereEmbeddingProvider
            self._cohere = CohereEmbeddingProvider(api_key=cohere_api_key)
    
    async def get_specter_embeddings(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """Get SPECTER2 embeddings (768d)."""
        if not self._specter:
            raise ValueError("SPECTER2 not initialized")
        return await self._specter.get_embeddings(texts)
    
    async def get_cohere_embeddings(
        self,
        texts: List[str],
        input_type: str = "search_document",
    ) -> List[List[float]]:
        """Get Cohere embeddings (1536d)."""
        if not self._cohere:
            raise ValueError("Cohere not initialized")
        return await self._cohere.get_embeddings(texts, input_type=input_type)
    
    async def get_dual_embeddings(
        self,
        texts: List[str],
    ) -> dict:
        """
        Get both SPECTER2 and Cohere embeddings.
        
        Returns:
            Dict with 'specter' and 'cohere' keys
        """
        results = {}
        
        # Run both in parallel if both are enabled
        tasks = []
        
        if self._specter:
            tasks.append(("specter", self._specter.get_embeddings(texts)))
        
        if self._cohere:
            tasks.append(("cohere", self._cohere.get_embeddings(texts)))
        
        if tasks:
            gathered = await asyncio.gather(*[t[1] for t in tasks])
            for i, (name, _) in enumerate(tasks):
                results[name] = gathered[i]
        
        return results


# Singleton for convenience
_specter_provider: Optional[SpecterEmbeddingProvider] = None


def get_specter_embeddings() -> SpecterEmbeddingProvider:
    """Get or create singleton SPECTER2 provider."""
    global _specter_provider
    if _specter_provider is None:
        _specter_provider = SpecterEmbeddingProvider()
    return _specter_provider
