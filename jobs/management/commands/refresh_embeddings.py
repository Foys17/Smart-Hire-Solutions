from django.core.management.base import BaseCommand
from candidates.models import Application
from django.apps import apps
import sys

class Command(BaseCommand):
    help = 'Refreshes CV embeddings using the local Fine-Tuned Jina model'

    def handle(self, *args, **kwargs):
        self.stdout.write("🔄 Initializing...")
        
        try:
            # Access the JobsConfig
            JobsConfig = apps.get_app_config('jobs')
            
            # CRITICAL CHECK: Does apps.py have the function?
            if not hasattr(JobsConfig, 'load_models'):
                self.stdout.write(self.style.ERROR("❌ Error: 'JobsConfig' in jobs/apps.py does not have a 'load_models' method."))
                self.stdout.write("   -> You must update jobs/apps.py with the code provided.")
                return

            # Force load the models
            JobsConfig.load_models()
            model = JobsConfig.jina_model
            
        except LookupError:
            self.stdout.write(self.style.ERROR("❌ Could not find 'jobs' app config."))
            return

        if not model:
            self.stdout.write(self.style.ERROR("❌ Jina Model failed to load."))
            self.stdout.write(self.style.WARNING("   -> Check if the 'ml_models/my_finetuned_jina' folder exists in your project."))
            return

        self.stdout.write(self.style.SUCCESS("✅ Fine-Tuned Model loaded. Starting update..."))

        apps_list = Application.objects.all()
        count = 0
        updated = 0

        for app in apps_list:
            if not app.cv_text_content:
                # Optional: Try to read PDF if text is missing
                continue

            try:
                # Re-encode using the local model (limit to 2000 chars)
                embedding = model.encode(app.cv_text_content[:2000]).tolist()
                app.cv_embedding = embedding
                app.save()
                
                self.stdout.write(f"  -> Updated: {app.candidate.full_name}")
                updated += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Error {app.candidate.full_name}: {e}"))
            
            count += 1

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Done! Processed {count} candidates. Updated {updated} embeddings."))