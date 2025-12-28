#!/usr/bin/env python3
"""
Direct LLM Entity Extraction Test
Calls OpenAI directly to see what it returns for entity extraction.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import db
from app.core.config import settings
import json

# Sample text from a manual
SAMPLE_TEXT = """
HYDRAULIC PUMP MODEL HP-3000 INSTALLATION MANUAL

SAFETY WARNINGS
WARNING: Disconnect all electrical power before servicing the Hydraulic Pump HP-3000. 
High voltage can cause serious injury or death.

EQUIPMENT SPECIFICATIONS
The Hydraulic Pump HP-3000 is a high-performance industrial pump designed for heavy-duty applications.
Operating Pressure: 3000 PSI maximum
Power Supply: 480V AC three-phase
Flow Rate: 50 GPM at full speed

REQUIRED TOOLS
The following tools are required for installation:
- Torque Wrench (50-200 ft-lbs range)
- Digital Multimeter
- Pipe Wrench Set
"""

FLEXIBLE_SCHEMA = """
Extract entities and relationships from this document.

Entity Types:
- ITEM: Any physical thing (devices, parts, tools)
- ATTRIBUTE: Properties, specifications, measurements
- ACTION: Steps, procedures, processes
- WARNING: Warnings, cautions

Relationship Types:
- HAS_ATTRIBUTE: Item has a property
- REQUIRES: One thing needs another
- WARNS_ABOUT: Warning relates to something

Extract ALL entities and create relationships between them.

Respond with a list of:
1. Entities in format: (TYPE: name)
2. Relationships in format: (entity1)-[RELATIONSHIP]->(entity2)

Example:
Entities:
- (ITEM: Hydraulic Pump HP-3000)
- (ATTRIBUTE: 3000 PSI)
- (ITEM: Torque Wrench)

Relationships:
- (Hydraulic Pump HP-3000)-[HAS_ATTRIBUTE]->(3000 PSI)
- (Installation)-[REQUIRES]->(Torque Wrench)
"""

def test_direct_extraction():
    """Test what the LLM actually returns."""
    print("🔍 Direct LLM Entity Extraction Test")
    print("=" * 80)
    
    # Connect to database
    print("\n1️⃣ Connecting to database...")
    db.connect()
    llm = db.get_llm()
    print(f"✅ Connected! Using model: {llm.model}")
    
    # Create prompt
    print("\n2️⃣ Creating extraction prompt...")
    full_prompt = f"""{FLEXIBLE_SCHEMA}

Text to analyze:
{SAMPLE_TEXT}

Now extract entities and relationships:"""
    
    print(f"📝 Prompt length: {len(full_prompt)} characters")
    
    # Call LLM
    print("\n3️⃣ Calling OpenAI...")
    response = llm.complete(full_prompt)
    
    print("\n4️⃣ RAW RESPONSE FROM OPENAI:")
    print("-" * 80)
    print(response.text)
    print("-" * 80)
    
    # Analyze response
    print("\n5️⃣ ANALYSIS:")
    response_text = response.text.lower()
    
    if "entity" in response_text or "entities" in response_text:
        print("✅ Response mentions 'entities'")
    else:
        print("❌ Response does NOT mention 'entities'")
    
    if "relationship" in response_text:
        print("✅ Response mentions 'relationships'")
    else:
        print("❌ Response does NOT mention 'relationships'")
    
    if "(" in response_text and ")" in response_text:
        print("✅ Response contains parentheses (likely entity format)")
    else:
        print("❌ Response missing parentheses")
    
    if "-[" in response_text and "]->" in response_text:
        print("✅ Response contains relationship arrows")
    else:
        print("❌ Response missing relationship format")
    
    # Count potential entities
    entity_count = response.text.count("(ITEM:") + response.text.count("(ATTRIBUTE:") + \
                   response.text.count("(ACTION:") + response.text.count("(WARNING:")
    print(f"\n📊 Potential entities found: {entity_count}")
    
    relationship_count = response.text.count("]->(")
    print(f"📊 Potential relationships found: {relationship_count}")
    
    print("\n" + "=" * 80)
    print("💡 CONCLUSION:")
    if entity_count > 0:
        print("✅ LLM IS extracting entities correctly!")
        print("🔍 Issue is likely with SimpleLLMPathExtractor parsing")
    else:
        print("❌ LLM is NOT extracting entities in expected format")
        print("🔍 Need to adjust the prompt/schema")
    
    db.close()

if __name__ == "__main__":
    try:
        test_direct_extraction()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()