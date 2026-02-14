
# ai_analysis.py
import google.generativeai as genai
import json
from PIL import Image
import io
import streamlit as st

def analyze_drawing(image_file, api_key):
    """
    Analyzes the uploaded drawing using Gemini 1.5 Pro.
    Returns a list of dictionaries representing the components.
    """
    if not api_key:
        st.error("API Key is missing.")
        return []

    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel('gemini-flash-latest')

        prompt = """
        You are an expert steel structure estimator. Analyze this technical drawing (which may include multiple pages) with EXTREME SPEED.
        
        SPEED & EFFICIENCY RULES (CRITICAL):
        1. **NO THINKING TIME:** Do not spend time calculating or deciphering blurry text.
        2. **IMMEDIATE FALLBACK:** If a value is not INSTANTLY clear (within 1 second of looking), DO NOT GUESS.
           - Numeric fields -> Enter 0
           - Text fields -> Enter "CHECK"
        3. **COMPLETION > PERFECTION:** Your goal is to list ALL components. It is better to list a component with "CHECK" dimensions than to miss it trying to be perfect.
        4. **NO MARKDOWN/EXPLANATION:** Return ONLY the JSON object. Do not explain your reasoning.
        
        YOUR MISSION:
        1. **Identify Parent Patterns (Groups)**:
           - Identify the "Main Pole" types (e.g., "Type A", "Type B", "Mk-1", "Mk-2"). these are your Pattern Keys.
           - Consolidate General View and Detail View pages into the SAME pattern structure.
        
        2. **Handle Common Details**:
           - Copy common components (like "Standard Rib") into EVERY pattern they apply to.
 
        3. **Extract Components**:
           - Extract ALL steel components.
        
        4. **Handling Unclear Data (Validation)**:
           - **If a numeric value is illegible or missing -> 0**
           - **If a text value is illegible -> "CHECK"**
           - You MUST populate a `validation_alerts` list for each pattern with specific notes (e.g., "Base plate thickness unclear", "Arm length missing").
        
        RETURN FORMAT:
        Return a strict JSON object with a key "patterns".
        {
            "patterns": [
                {
                    "pattern_name": "Pole Type A (Main)",  // Use the drawing's identifier (e.g. Type A, Mk-1)
                    "validation_alerts": [ "Base Plate thickness is missing", "Check Rib dimensions" ],  // List of specific warnings. Empty if perfect.
                    "components": [
                        {
                            "type": "Pipe" or "Plate",
                            "name": "Main Pole Bottom",
                            "diameter_mm": 318.5,  // Number or 0 if unknown
                            "thickness_mm": 6.0,   // Number or 0 if unknown
                            "length_mm": 5500,     // Number or 0 if unknown
                            "width_mm": 0,         // Number. 0 for Pipes.
                            "count": 1,            // Number
                            "notes": "Overlap connection"
                        },
                        {
                            "type": "Pipe",
                            "name": "Arm",
                            "diameter_mm": "CHECK",  // Use "CHECK" if strictly illegible
                            ...
                        }
                    ]
                },
                ...
            ]
        }
        
        CRITICAL RULES:
        - **Context:** The pages are related. MERGE details from subsequent pages into the correct Main Pole pattern.
        - **Grouping:** Do not create separate patterns for "Base Plate" or "Arm" if they belong to a Main Pole. Put them INSIDE the Main Pole's component list.
        - **Validation:** If you assign 0 or "CHECK", you MUST add a corresponding note in `validation_alerts`.
        """

        input_data = []
        input_data.append(prompt)

        # 1. Handle PIL Image (Already processed in app.py)
        if isinstance(image_file, Image.Image):
            input_data.append(image_file)
        
        # 2. Handle PDF file (Streamlit UploadedFile)
        elif hasattr(image_file, "type") and image_file.type == "application/pdf":
            image_file.seek(0)
            pdf_bytes = image_file.read()
            input_data.append({
                "mime_type": "application/pdf",
                "data": pdf_bytes
            })
            
        # 3. Fallback: Try to open as image if it's a file-like object
        elif hasattr(image_file, 'read'):
             image_file.seek(0)
             try:
                img = Image.open(image_file)
                input_data.append(img)
             except Exception:
                st.error("Unsupported file format. Please upload PNG, JPG, or PDF.")
                return []
        else:
             st.error("Invalid file input.")
             return []

        response = model.generate_content(input_data)
        text = response.text.strip()
        
        # Cleanup potential markdown formatting
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        data = json.loads(text)
        
        # Validate structure: if it returns a list directly (old prompt style), wrap it
        if isinstance(data, list):
            return [{"pattern_name": "Detected Pattern", "components": data}]
        
        return data.get("patterns", [])

    except Exception as e:
        st.error(f"An error occurred during AI analysis: {str(e)}")
        return []

def get_dummy_data():
    """Returns dummy data for testing UI without API calls."""
    return [
        {
            "pattern_name": "Sample Pole Type A",
            "components": [
                {"type": "Pipe", "name": "Bottom Pole (Lower)", "diameter_mm": 318.5, "thickness_mm": 6.0, "length_mm": 5500, "width_mm": 0, "count": 1, "notes": "Overlap connection"},
                {"type": "Pipe", "name": "Top Pole (Upper)", "diameter_mm": 216.3, "thickness_mm": 4.5, "length_mm": 4000, "width_mm": 0, "count": 1, "notes": ""},
                {"type": "Plate", "name": "Base Plate", "diameter_mm": 0, "thickness_mm": 25.0, "length_mm": 600, "width_mm": 600, "count": 1, "notes": "Base Detail"},
                {"type": "Plate", "name": "Rib", "diameter_mm": 0, "thickness_mm": 9.0, "length_mm": 150, "width_mm": 100, "count": 8, "notes": ""}
            ]
        },
        {
            "pattern_name": "Sample Pole Type B (Small)",
            "components": [
                 {"type": "Pipe", "name": "Main Pole", "diameter_mm": 165.2, "thickness_mm": 4.5, "length_mm": 4000, "width_mm": 0, "count": 1, "notes": "Single piece"},
                 {"type": "Plate", "name": "Base Plate", "diameter_mm": 0, "thickness_mm": 19.0, "length_mm": 400, "width_mm": 400, "count": 1, "notes": ""}
            ]
        }
    ]
