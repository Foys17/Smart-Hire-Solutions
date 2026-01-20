from django.apps import AppConfig
from gliner import GLiNER
from sentence_transformers import SentenceTransformer
import os
from django.conf import settings

class JobsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'jobs'

    gliner_model = None
    jina_model = None

    def ready(self):
    # Only auto-load when running the server (keeps other commands fast)
        if os.environ.get('RUN_MAIN') == 'true':
            self.load_models()
            

    def load_models(self):
        """
        Manually loads the AI models. 
        This is required for management commands to work.
        """
        if self.jina_model and self.gliner_model:
            print("🧠 Models already loaded.")
            return

        print("🧠 Loading AI Models...")
        
        try:
            # 1. Load GLiNER
            self.gliner_model = GLiNER.from_pretrained("urchade/gliner_small-v2.1")
            
            # 2. Load Your Local Fine-Tuned Jina Model
            model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'my_finetuned_jina')
            
            if os.path.exists(model_path):
                self.jina_model = SentenceTransformer(model_path, trust_remote_code=True)
                print(f"✅ Loaded Jina Model from: {model_path}")
            else:
                print(f"❌ Model FOLDER not found at: {model_path}")
                print("   -> Please make sure you created the 'ml_models' folder in your project root.")
                
        except Exception as e:
            print(f"❌ Error loading models: {e}")