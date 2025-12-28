"""
Detects if document is procedural/instructional vs other types
"""
import logging
from typing import Tuple
from llama_index.llms.openai import OpenAI

logger = logging.getLogger(__name__)


class DocumentTypeValidator:
    """Validate document type"""
    
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
2. "narrative" - Story, novel, play, poem, creative writing
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
        
        summary_prompt = f"""Provide a brief 2-sentence summary of this {doc_type}:

{text_sample}

Summary (2 sentences):"""
        
        try:
            response = await self.llm.acomplete(summary_prompt)
            return response.text.strip()
        except:
            return "Summary unavailable."
    
    def _get_rejection_message(self, doc_type: str, summary: str, filename: str) -> str:
        """Get funny rejection message for non-procedural documents"""
        
        messages = {
            "narrative": f"""**Whoa there, literature lover!**

I see you've uploaded "{filename}" - which appears to be some fine literary/narrative content. Beautiful stuff, really. But here's the thing...

**I'm optimized for:**
- Instruction manuals
- User guides
- Technical procedures
- How-to documents
- Equipment specs

**Your document appears to be:**
- Literary/narrative content (poems, stories, novels, etc.)

**Quick summary of what you uploaded:**

{summary}

---

**Here's the deal:**

This is a passion learning project specifically built for procedural and technical documentation. Think installation guides, troubleshooting manuals, equipment specs - you know, the thrilling stuff that keeps engineers up at night.

For poetry analysis or literary discussion, you'll want something more sophisticated. Maybe try GPT-4, Gemini Pro, or another top-tier LLM that actually knows what a metaphor is. This system? It thinks a metaphor is a type of industrial measuring device.

**Your options:**
1. Upload a technical manual instead (I'm really good at those!)
2. Take this literary masterpiece to a more advanced AI that appreciates the finer things
""",
            
            "academic": f"""**Academic Paper Detected!**

So you've uploaded "{filename}" - looks like some quality academic work. Impressive credentials, probably. But...

**I'm built for:**
- Instruction manuals
- Technical procedures
- User guides
- How-to documentation

**Your document appears to be:**
- Academic/scholarly content (essays, research papers, textbooks)

**Quick summary:**

{summary}

---

**The honest truth:**

This is a learning project I built to handle procedural documentation. Academic papers? That's above my pay grade (which is currently zero).

For academic document analysis, you'll want to consult a more sophisticated LLM. I'm like a really specialized wrench - great at one thing, confused by everything else.

**What now:**
1. Upload a technical manual (my specialty!)
2. Try a general-purpose AI for this academic content
""",
            
            "business": f"""**Business Document Detected!**

Hey! I see "{filename}" - looks very professional. Quarterly reports? Strategic analysis? Synergies?

**I'm optimized for:**
- Technical manuals
- Installation guides
- Equipment procedures
- How-to docs

**Your document appears to be:**
- Business content (reports, presentations, memos)

**Summary:**

{summary}

---

**Full disclosure:**

This is a passion project built for technical/procedural manuals. Business strategy? Financial analysis? That's not my wheelhouse. I'm more of a "turn the wrench counterclockwise" kind of system.

For business doc analysis, try a more versatile AI. They're better at corporate speak anyway.

**Options:**
1. Upload a technical manual instead
2. Use a general-purpose LLM for business docs
""",
            
            "other": f"""**Hmm, Interesting Choice!**

You've uploaded "{filename}" which is... definitely a document!

**I'm designed for:**
- Instruction manuals
- Technical procedures
- User guides
- How-to documentation

**Quick summary of your upload:**

{summary}

---

**Here's the thing:**

This is a learning project specifically built for procedural and technical documents. You know - installation steps, troubleshooting guides, equipment specifications. The kind of content that makes people say "there's gotta be a manual for this."

For general document analysis, you'll want a more well-rounded LLM. I'm like a really good screwdriver - excellent for screws, questionable for everything else.

**What you can do:**
1. Upload a technical/instruction manual
2. Try GPT-4 or Gemini for this content
"""
        }
        
        return messages.get(doc_type, messages["other"])