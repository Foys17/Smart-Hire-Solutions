import fitz  # PyMuPDF
import numpy as np
import re
from django.apps import apps
from numpy.linalg import norm

def extract_text_from_pdf(cv_file):
    text = ""
    try:
        with fitz.open(stream=cv_file.read(), filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"❌ Error reading CV PDF: {e}")
    return text

def calculate_cosine_similarity(vec_a, vec_b):
    if vec_a is None or vec_b is None:
        return 0.0
    try:
        a = np.array(vec_a)
        b = np.array(vec_b)
        if a.size == 0 or b.size == 0 or np.all(a == 0) or np.all(b == 0):
            return 0.0
        score = np.dot(a, b) / (norm(a) * norm(b))
        return float(score)
    except Exception:
        return 0.0

def process_application(application_instance):
    print(f"--- Processing Application ID: {application_instance.id} ---")
    
    try:
        JobsConfig = apps.get_app_config('jobs')
        gliner = JobsConfig.gliner_model
        jina = JobsConfig.jina_model
    except LookupError:
        print("❌ Jobs app not loaded.")
        return

    if not gliner or not jina:
        print("⚠️ AI Models not loaded.")
        return

    # 1. READ TEXT
    if application_instance.cv_file:
        raw_text = extract_text_from_pdf(application_instance.cv_file)
        application_instance.cv_file.seek(0)
    else:
        return

    # 2. CLEANING
    # Remove bullets but keep newlines to preserve list structure
    clean_text = raw_text.replace("•", "").replace("●", "").replace("|", "")
    # Remove excessive spaces but strictly strictly preserve meaningful text
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    application_instance.cv_text_content = clean_text

    if not clean_text:
        return

    # 3. GLiNER EXTRACTION (Expanded Labels)
    # We added Database, Tool, Platform to catch "MySQL", "Docker", "Git"
    labels = [
        "Skill", "Technology", "Framework", "Programming Language", 
        "Job Title", "Experience", "Project", "Degree", 
        "University", "Database", "Tool", "Platform"
    ]
    
    try:
        # Threshold 0.3 allows it to catch items in dense lists
        entities = gliner.predict_entities(clean_text, labels, threshold=0.3)
        
        unique_data = []
        seen = set()
        
        # Lists to build the "Focused Summary" for Jina
        focused_skills = []
        focused_titles = []
        
        for e in entities:
            # Normalize key: ("skill", "python")
            key = (e['label'], e['text'].strip().lower())
            
            if key not in seen:
                seen.add(key)
                unique_data.append({"label": e["label"], "text": e["text"].strip()})
                
                # Collect keywords for the embedding summary
                if e['label'] in ["Skill", "Technology", "Framework", "Database", "Tool", "Platform"]:
                    focused_skills.append(e["text"].strip())
                elif e['label'] in ["Job Title", "Experience"]:
                    focused_titles.append(e["text"].strip())

        application_instance.extracted_data = unique_data
        print(f"✅ Extracted {len(unique_data)} unique entities.")
        
    except Exception as e:
        print(f"❌ GLiNER failed: {e}")
        application_instance.extracted_data = []
        focused_skills = []
        focused_titles = []

    # 4. JINA EMBEDDING (The Fix)
    # We REMOVED the [:1000] limit. Jina v2 can handle the whole text.
    rich_context = (
        f"Candidate Role: {', '.join(focused_titles)}. "
        f"Key Skills & Tools: {', '.join(focused_skills)}. "
        f"Full Profile: {clean_text}"  # <--- Reading the FULL text now
    )
    
    try:
        print("🔍 Generating Focused Embedding...")
        cv_vector_numpy = jina.encode(rich_context)
        application_instance.cv_embedding = cv_vector_numpy.tolist()
    except Exception as e:
        print(f"❌ Jina Encoding failed: {e}")
        return

    # 5. SCORING
    job_instance = application_instance.job
    job_vector = job_instance.jina_embedding

    if job_vector:
        similarity = calculate_cosine_similarity(application_instance.cv_embedding, job_vector)
        application_instance.match_score = round(similarity * 100, 2)
        print(f"🎉 FINAL SCORE: {application_instance.match_score}%")
    else:
        application_instance.match_score = 0.0

    application_instance.save()