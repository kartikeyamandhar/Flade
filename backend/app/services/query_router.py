"""
Query Router - Simple Version (Workaround).
Uses keyword-based classification instead of LLM to avoid API issues.
"""

from typing import Tuple
import logging
import re

logger = logging.getLogger(__name__)


class QueryRouter:
    """Route questions to appropriate retrieval method using keyword matching."""
    
    def __init__(self, llm=None):
        """
        Initialize the query router.
        
        Args:
            llm: Not used in simple version (for API compatibility)
        """
        self.llm = llm  # Keep for compatibility but don't use
        
        # Define keyword patterns for each method
        self.patterns = {
            'text2cypher': [
                r'\bhow many\b', r'\bcount\b', r'\bnumber of\b',
                r'\bhow much\b', r'\btotal\b', r'\blist all\b',
                r'\bshow all\b', r'\bfind all\b'
            ],
            'graph': [
                r'\bconnect', r'\brelat', r'\bcompat',
                r'\brequire', r'\bdepend', r'\blink',
                r'\bpart of\b', r'\bbelongs to\b', r'\buses\b',
                r'\bwhat.*with\b', r'\bwhich.*with\b'
            ],
            'web_search': [
                r'\bcurrent\b', r'\blatest\b', r'\brecent\b',
                r'\bprice\b', r'\bcost\b', r'\btoday\b',
                r'\bnow\b', r'\bmarket\b', r'\bupdate'
            ]
        }
    
    def classify_query(self, question: str) -> Tuple[str, str]:
        """
        Classify question using keyword matching.
        
        Args:
            question: User's question
            
        Returns:
            Tuple of (retrieval_method, reasoning)
        """
        question_lower = question.lower()
        
        # Check each method's patterns
        for method, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    reasoning = f"Keyword match: detected {method} query pattern"
                    logger.info(f"Query classified as: {method} (keyword-based)")
                    return method, reasoning
        
        # Default to vector search
        reasoning = "Default to vector search for semantic similarity"
        logger.info("Query classified as: vector (default)")
        return "vector", reasoning


# Backward compatibility - keep the class name the same
SimpleQueryRouter = QueryRouter