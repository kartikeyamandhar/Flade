"""
Database Connection Manager.
Manages Neo4j, LlamaIndex, and OpenAI connections.
UPDATED: Fixed OpenAI client initialization for compatibility
"""

from neo4j import GraphDatabase
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """Singleton database connection manager."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.driver = None
        self.graph_store = None
        self.llm = None
        self.embed_model = None
        self._initialized = True
    
    def connect(self):
        """Initialize all database connections."""
        try:
            # Neo4j driver
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
            )
            
            # Verify connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
            
            logger.info("✓ Neo4j connected successfully")
            
            # Graph store for LlamaIndex
            self.graph_store = Neo4jPropertyGraphStore(
                username=settings.NEO4J_USERNAME,
                password=settings.NEO4J_PASSWORD,
                url=settings.NEO4J_URI,
                database=settings.NEO4J_DATABASE,
            )
            
            # LLM (use cheaper model for learning)
            # FIXED: Initialize with api_key parameter explicitly
            model_name = "gpt-3.5-turbo" if settings.USE_CHEAPER_MODEL else "gpt-4"
            self.llm = OpenAI(
                model=model_name,
                temperature=0,
                api_key=settings.OPENAI_API_KEY
            )
            
            # Embedding model
            # FIXED: Initialize with api_key parameter explicitly  
            self.embed_model = OpenAIEmbedding(
                model="text-embedding-3-small",
                api_key=settings.OPENAI_API_KEY
            )
            
            logger.info("✓ All components initialized")
            return True
        
        except Exception as e:
            logger.error(f"✗ Database connection failed: {e}")
            raise
    
    def close(self):
        """Close all connections."""
        if self.driver:
            self.driver.close()
        logger.info("Database connections closed")
    
    def get_driver(self):
        """Get Neo4j driver instance."""
        return self.driver
    
    def get_graph_store(self):
        """Get LlamaIndex graph store instance."""
        return self.graph_store
    
    def get_llm(self):
        """Get LLM instance."""
        return self.llm
    
    def get_embed_model(self):
        """Get embedding model instance."""
        return self.embed_model


# Global database instance
db = Database()