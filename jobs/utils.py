import fitz  # PyMuPDF
from django.apps import apps

def extract_text_from_pdf(pdf_file):
    """Extracts raw text from the uploaded PDF."""
    text = ""
    try:
        with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

def run_ai_pipeline(job_instance):
    """
    1. Extract Text
    2. Extract Entities (GLiNER)
    3. Generate Embedding (Jina v2)
    """
    # 1. Get the app config to access loaded models
    JobsConfig = apps.get_app_config('jobs')
    gliner = JobsConfig.gliner_model
    jina = JobsConfig.jina_model

    if not gliner or not jina:
        print("⚠️ Models are not loaded. Skipping AI processing.")
        return

    # 2. Get Raw Text
    raw_text = job_instance.description_text
    if job_instance.description_file:
        raw_text = extract_text_from_pdf(job_instance.description_file)
        # Reset file pointer if you need to save it again, though usually not needed here
        job_instance.description_file.seek(0)

    # 3. Clean Text (Basic)
    clean_text = raw_text.strip()
    job_instance.processed_text = clean_text

    # 4. GLiNER Extraction
    # We construct a string to feed Jina based on what GLiNER finds.
    labels = ["Skill", "Experience", "Job Title", "Degree"]
    entities = gliner.predict_entities(clean_text, labels)
    
    # Format for JSON storage: [{'label': 'Skill', 'text': 'Python'}, ...]
    job_instance.gliner_entities = [{"label": e["label"], "text": e["text"]} for e in entities]

    # 5. Prepare Input for Jina
    # Strategy: We combine the raw text with emphasized entities for the best embedding
    # Or, if your Jina model was fine-tuned on the raw descriptions (Anchors), pass raw text.
    # Based on your dataset, your anchors are sentences like "Looking for a Backend Developer..."
    # So we pass the full clean text.
    
    if clean_text:
        embedding = jina.encode(clean_text)
        job_instance.jina_embedding = embedding.tolist() # Convert numpy array to list

    job_instance.save()