import fitz  # PyMuPDF
from django.apps import apps
import re  # Regex for cleaning & detection
from numpy.linalg import norm
import numpy as np

def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")
    return text

def run_ai_pipeline(job_instance):
    """
    1. Extract & Clean Text
    2. GLiNER Extraction (With Regex Correction)
    3. Jina Embedding (Full Text)
    """
    print(f"--- Processing Job: {job_instance.title} ---")

    try:
        JobsConfig = apps.get_app_config('jobs')
        gliner = JobsConfig.gliner_model
        jina = JobsConfig.jina_model
    except LookupError:
        print("⚠️ Jobs app not found.")
        return

    if not gliner or not jina:
        print("⚠️ AI Models not loaded.")
        return

    # 1. Get Raw Text
    raw_text = job_instance.description_text or ""
    
    if job_instance.description_file:
        try:
            file_text = extract_text_from_pdf(job_instance.description_file)
            if file_text:
                raw_text += "\n" + file_text
            job_instance.description_file.seek(0)
        except Exception as e:
            print(f"⚠️ Failed to process file: {e}")

    # 2. Clean Text
    # Remove bullets and normalize spaces
    clean_text = raw_text.replace("•", "").replace("●", "").replace("- ", "")
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Save for Debugging View
    job_instance.processed_text = clean_text

    if not clean_text:
        print("⚠️ No text found to process.")
        return

    # 3. GLiNER Extraction
    # Added 'Cloud' and 'Service' to catch AWS components
    labels = [
        "Skill", "Technology", "Framework", "Programming Language", 
        "Software", "Tool", "Platform", "Database", "Cloud", "Service",
        "Experience", "Job Title", "Degree", "Qualification"
    ]
    
    try:
        entities = gliner.predict_entities(clean_text, labels, threshold=0.3)
        
        unique_data = []
        seen = set()
        
        for e in entities:
            text = e['text'].strip()
            label = e['label']
            
            # --- FIX 1: FORCE EXPERIENCE RELABELING ---
            # If it mentions "year" or "years", it is Experience, NOT a Skill.
            if "year" or "years" in text.lower():
                label = "Experience"

            # --- FIX 2: FORCE AWS RELABELING ---
            # Sometimes specific cloud terms get missed or generic labels
            if text.upper() in ["AWS", "AZURE", "GCP", "EC2", "RDS", "LAMBDA", "DOCKER", "KUBERNETES"]:
                if label not in ["Experience", "Job Title"]:
                    label = "Technology" # Force them to appear in Tech Stack
            
            # Create unique key
            key = (label, text.lower())
            
            if key not in seen:
                seen.add(key)
                unique_data.append({"label": label, "text": text})

        job_instance.gliner_entities = unique_data
        print(f"✅ Extracted {len(unique_data)} unique entities.")

    except Exception as e:
        print(f"❌ GLiNER Error: {e}")
        job_instance.gliner_entities = []

    # 4. Jina Embedding
    try:
        # Use full clean text for embedding
        embedding = jina.encode(clean_text)
        job_instance.jina_embedding = embedding.tolist()
        print(f"✅ Embedding Generated. Size: {len(job_instance.jina_embedding)}")
    except Exception as e:
        print(f"❌ Jina Embedding Error: {e}")

    job_instance.save()