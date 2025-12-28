"""
Document Type Validator - Integrated into backend
Detects if document is procedural/instructional vs other types
"""
import logging
from typing import Tuple
from llama_index.llms.openai import OpenAI

logger = logging.getLogger(__name__)


class DocumentTypeValidator:
    """Validate document type and provide appropriate responses"""
    
    def __init__(self, llm: OpenAI):
        self.llm = llm
    
    async def validate_document_type(self, text_sample: str, filename: str = "document") -> Tuple[bool, str, str]:
        """
        Validate if document is procedural/instructional
        
        Args:
            text_sample: First ~2000 chars of document
            filename: Document filename
        
        Returns:
            Tuple of (is_procedural, document_type, message)
        """
        
        # Sample text for classification
        sample = text_sample[:2000]
        
        # Classify document type
        classification_prompt = f"""Analyze this document sample and classify it:

Document sample:
{sample}

Classify as ONE of:
1. "manual" - Instruction manual, user guide, how-to, procedures, technical specs
2. "narrative" - Story, novel, play, poem, creative writing (like Shakespeare)
3. "academic" - Essay, research paper, textbook, academic writing
4. "business" - Report, memo, presentation, business document
5. "other" - News, blog, general content

Respond with ONLY the category name (one word).

Category:"""
        
        try:
            response = await self.llm.acomplete(classification_prompt)
            doc_type = response.text.strip().lower()
            
            logger.info(f"📄 Document '{filename}' classified as: {doc_type}")
            
            # Check if procedural
            is_procedural = doc_type in ["manual"]
            
            # If not procedural, generate summary and rejection message
            message = ""
            if not is_procedural:
                summary = await self._generate_summary(sample, doc_type)
                message = self._get_rejection_message(doc_type, summary, filename)
            
            return is_procedural, doc_type, message
            
        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            # Default to allowing (fail open)
            return True, "unknown", ""
    
    async def _generate_summary(self, text_sample: str, doc_type: str) -> str:
        """Generate summary for non-procedural documents"""
        
        summary_prompt = f"""Provide a brief 3-sentence summary of this {doc_type}:

{text_sample}

Summary (3 sentences):"""
        
        try:
            response = await self.llm.acomplete(summary_prompt)
            return response.text.strip()
        except:
            return "Summary unavailable."
    
    def _get_rejection_message(self, doc_type: str, summary: str, filename: str) -> str:
        """Get friendly rejection message for non-procedural documents"""
        
        messages = {
            "narrative": f"""📚 **Document Type Notice**

Hi! I noticed "{filename}" appears to be **literary/narrative content** rather than an instruction manual or procedural guide.

**🎯 Claude is optimized for:**
✅ Instruction manuals
✅ User guides  
✅ Technical procedures
✅ How-to documents
✅ Equipment documentation

**📖 Your document appears to be:**
❌ Literary/narrative content (stories, plays, novels like Shakespeare)

**📝 Here's a quick summary of your document:**

{summary}

---

**💡 Recommendation:**

This system is specifically designed for **procedural and technical documents** with steps, equipment, specifications, and troubleshooting procedures.

For literary analysis or discussion of narrative works, I'd be happy to help in a regular Claude chat session! Just start a new conversation without uploading this document.

**Would you like to:**
1. Upload a different document (instruction manual/user guide)
2. Continue analyzing this in regular chat mode
""",
            
            "academic": f"""📚 **Document Type Notice**

Hi! I noticed "{filename}" appears to be **academic content** rather than an instruction manual.

**🎯 Claude is optimized for:**
✅ Instruction manuals
✅ User guides
✅ Technical procedures
✅ Step-by-step guides

**📖 Your document appears to be:**
❌ Academic/scholarly content (essays, research papers, textbooks)

**📝 Here's a quick summary:**

{summary}

---

**💡 Recommendation:**

This system is designed for **procedural documentation** with steps and instructions. For academic document analysis, regular Claude chat works better!

**Would you like to:**
1. Upload a procedural document instead
2. Analyze this in regular chat mode
""",
            
            "business": f"""📊 **Document Type Notice**

Hi! I noticed "{filename}" appears to be **business content** rather than a technical manual.

**🎯 Claude is optimized for:**
✅ Technical instruction manuals
✅ User guides
✅ Equipment procedures
✅ Installation guides

**📖 Your document appears to be:**
❌ Business content (reports, presentations, memos)

**📝 Here's a quick summary:**

{summary}

---

**💡 Recommendation:**

This system specializes in **procedural/technical manuals**. For business document analysis, regular chat mode works better!

**Would you like to:**
1. Upload a technical manual instead
2. Analyze this in regular chat mode
""",
            
            "other": f"""📄 **Document Type Notice**

Hi! "{filename}" doesn't appear to be an **instruction manual or procedural guide**.

**🎯 Claude is optimized for:**
✅ Instruction manuals
✅ User guides
✅ Technical procedures
✅ How-to documentation

**📝 Here's a quick summary of your document:**

{summary}

---

**💡 Recommendation:**

This system is designed specifically for **procedural and technical documents** with steps, equipment lists, and troubleshooting procedures.

For general document analysis, try regular Claude chat mode! This manual system works best with procedural/technical content.

**Would you like to:**
1. Upload a procedural document instead
2. Analyze this in regular chat
"""
        }
        
        return messages.get(doc_type, messages["other"])