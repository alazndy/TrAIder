"""
Upload all .pkl model files to Firebase Storage.
Run this once locally to upload models to cloud.
"""
import os
import firebase_admin
from firebase_admin import credentials, storage

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'tr-ai-der.firebasestorage.app'
    })

bucket = storage.bucket()

def upload_models():
    """Upload all .pkl files from data/ to Firebase Storage."""
    data_dir = "data"
    uploaded = 0
    skipped = 0
    
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.pkl'):
                local_path = os.path.join(root, file)
                # Create cloud path (relative to data/)
                cloud_path = f"models/{local_path.replace(os.sep, '/')}"
                
                print(f"Uploading: {local_path} -> {cloud_path}")
                
                try:
                    blob = bucket.blob(cloud_path)
                    blob.upload_from_filename(local_path)
                    uploaded += 1
                except Exception as e:
                    print(f"  Error: {e}")
                    skipped += 1
    
    print(f"\n✅ Done! Uploaded: {uploaded}, Skipped: {skipped}")

if __name__ == "__main__":
    upload_models()
