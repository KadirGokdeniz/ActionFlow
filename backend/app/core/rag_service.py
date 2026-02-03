"""
ActionFlow RAG Service - Pinecone Integration
Semantic search for travel policies using OpenAI embeddings + Pinecone
"""

import os
import logging
from typing import List, Dict, Optional
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger("ActionFlow-RAG")

# Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "actionflow-policies")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class RAGService:
    """
    RAG Service for policy document retrieval using Pinecone
    """
    
    def __init__(self):
        self.embeddings = None
        self.vector_store = None
        self.index = None
        self._initialized = False
        
    def initialize(self):
        """Initialize Pinecone connection and embeddings"""
        try:
            if not PINECONE_API_KEY:
                logger.error("❌ PINECONE_API_KEY not found in environment")
                return False
                
            if not OPENAI_API_KEY:
                logger.error("❌ OPENAI_API_KEY not found in environment")
                return False
            
            # Initialize Pinecone
            logger.info("🔧 Initializing Pinecone...")
            pc = Pinecone(api_key=PINECONE_API_KEY)
            
            # Check if index exists, create if not
            if PINECONE_INDEX_NAME not in pc.list_indexes().names():
                logger.info(f"📦 Creating Pinecone index: {PINECONE_INDEX_NAME}")
                pc.create_index(
                    name=PINECONE_INDEX_NAME,
                    dimension=1536,  # OpenAI ada-002 embedding size
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=PINECONE_ENVIRONMENT
                    )
                )
            
            # Initialize embeddings
            logger.info("🔧 Initializing OpenAI embeddings...")
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-ada-002",
                openai_api_key=OPENAI_API_KEY
            )
            
            # Initialize vector store
            self.vector_store = PineconeVectorStore(
                index_name=PINECONE_INDEX_NAME,
                embedding=self.embeddings
            )
            
            self._initialized = True
            logger.info("✅ RAG Service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG Service: {e}")
            return False
    
    def index_documents(self, documents: List[str], metadatas: List[Dict] = None):
        """
        Index documents into Pinecone
        
        Args:
            documents: List of text documents
            metadatas: Optional metadata for each document
        """
        if not self._initialized:
            logger.error("❌ RAG Service not initialized")
            return False
            
        try:
            logger.info(f"📚 Indexing {len(documents)} documents...")
            
            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            
            # Create Document objects
            docs = []
            for i, doc_text in enumerate(documents):
                metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                # Split each document
                splits = text_splitter.split_text(doc_text)
                for j, split in enumerate(splits):
                    docs.append(Document(
                        page_content=split,
                        metadata={**metadata, "chunk": j, "source_doc": i}
                    ))
            
            logger.info(f"📦 Created {len(docs)} chunks from {len(documents)} documents")
            
            # Add to vector store
            self.vector_store.add_documents(docs)
            
            logger.info(f"✅ Successfully indexed {len(docs)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to index documents: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Semantic search for relevant policy information
        
        Args:
            query: User's question
            top_k: Number of results to return
            
        Returns:
            List of relevant document chunks with metadata
        """
        if not self._initialized:
            logger.warning("⚠️ RAG Service not initialized, returning empty results")
            return []
            
        try:
            logger.info(f"🔍 Searching for: {query}")
            
            # Perform similarity search
            results = self.vector_store.similarity_search_with_score(
                query,
                k=top_k
            )
            
            # Format results
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": float(score)
                })
            
            logger.info(f"✅ Found {len(formatted_results)} relevant chunks")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def get_context_for_query(self, query: str, max_chunks: int = 3) -> str:
        """
        Get formatted context for LLM from search results
        
        Args:
            query: User's question
            max_chunks: Maximum number of chunks to include
            
        Returns:
            Formatted context string
        """
        results = self.search(query, top_k=max_chunks)
        
        if not results:
            return "No relevant policy information found."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"[Source {i}]:\n{result['content']}\n")
        
        return "\n".join(context_parts)


# Global RAG service instance
_rag_service = None

def get_rag_service() -> RAGService:
    """Get or create global RAG service instance"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
        _rag_service.initialize()
    return _rag_service


# Convenience functions
def search_policies(query: str, top_k: int = 5) -> List[Dict]:
    """Search policy documents"""
    rag = get_rag_service()
    return rag.search(query, top_k)


def get_policy_context(query: str) -> str:
    """Get formatted policy context for LLM"""
    rag = get_rag_service()
    return rag.get_context_for_query(query)