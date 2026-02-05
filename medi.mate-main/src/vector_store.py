import json
import os
import hashlib
import numpy as np
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from src.config import Config
from src.utils import setup_logger

logger = setup_logger(__name__)


class VectorStoreManager:
    """
    Manages local vector storage using JSON files and numpy for similarity search.
    No external database required.
    """

    def __init__(self):
        self.storage_dir = os.path.join(Config.DATA_DIR, "vectors")
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Initialize Embeddings
        if Config.GOOGLE_API_KEY:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=Config.GOOGLE_API_KEY
            )
        else:
            logger.warning("Google API Key missing for embeddings.")
            self.embeddings = None
        
        logger.info("VectorStoreManager initialized with local storage")

    def _get_storage_path(self, namespace=None):
        """Get the JSON file path for a namespace."""
        filename = f"{namespace}.json" if namespace else "default.json"
        return os.path.join(self.storage_dir, filename)

    def _load_vectors(self, namespace=None):
        """Load vectors from JSON file."""
        path = self._get_storage_path(namespace)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {"vectors": []}
        return {"vectors": []}

    def _save_vectors(self, data, namespace=None):
        """Save vectors to JSON file."""
        path = self._get_storage_path(namespace)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _cosine_similarity(self, vec1, vec2):
        """Compute cosine similarity between two vectors."""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def add_texts(self, texts, metadata_list, namespace=None):
        """
        Generic method to add texts to local vector store.
        """
        if not self.embeddings:
            logger.error("No embeddings available")
            return False

        data = self._load_vectors(namespace)
        existing_ids = {v["id"] for v in data["vectors"]}
        
        new_vectors = []
        for i, text in enumerate(texts):
            text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
            vector_id = f"{namespace}_{text_hash}" if namespace else text_hash
            
            # Skip if already exists
            if vector_id in existing_ids:
                continue
            
            embedding = self.embeddings.embed_query(text)
            
            meta = metadata_list[i].copy() if i < len(metadata_list) else {}
            meta["text"] = text
            
            new_vectors.append({
                "id": vector_id,
                "embedding": embedding,
                "metadata": meta
            })
        
        data["vectors"].extend(new_vectors)
        self._save_vectors(data, namespace)
        
        logger.info(f"Stored {len(new_vectors)} texts in namespace '{namespace}'")
        return True

    def add_prescription(self, prescription_id, text_chunks, metadata):
        """
        Embeds and stores prescription chunks.
        """
        if not self.embeddings:
            return False

        data = self._load_vectors()
        existing_ids = {v["id"] for v in data["vectors"]}
        
        new_vectors = []
        for i, chunk in enumerate(text_chunks):
            vector_id = f"{prescription_id}_{i}"
            
            # Skip if already exists
            if vector_id in existing_ids:
                continue
            
            embedding = self.embeddings.embed_query(chunk)
            
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "text": chunk,
                "chunk_id": i,
                "prescription_id": prescription_id
            })
            
            new_vectors.append({
                "id": vector_id,
                "embedding": embedding,
                "metadata": chunk_metadata
            })

        data["vectors"].extend(new_vectors)
        self._save_vectors(data)
        
        logger.info(f"Stored {len(new_vectors)} chunks for prescription {prescription_id}")
        return True

    def search(self, query, prescription_id=None, namespace=None, top_k=5):
        """
        Searches for relevant chunks using cosine similarity.
        If prescription_id is provided, filters by that ID (Local Search).
        """
        if not self.embeddings:
            return []

        query_embedding = self.embeddings.embed_query(query)
        data = self._load_vectors(namespace)
        
        # Filter by prescription_id if provided
        vectors = data["vectors"]
        if prescription_id:
            vectors = [v for v in vectors if v["metadata"].get("prescription_id") == prescription_id]
        
        # Calculate similarities
        results = []
        for vector in vectors:
            similarity = self._cosine_similarity(query_embedding, vector["embedding"])
            results.append({
                "id": vector["id"],
                "score": similarity,
                "metadata": vector["metadata"]
            })
        
        # Sort by similarity (descending) and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Convert to match-like objects for compatibility
        class Match:
            def __init__(self, id, score, metadata):
                self.id = id
                self.score = score
                self.metadata = metadata
        
        return [Match(r["id"], r["score"], r["metadata"]) for r in results[:top_k]]
