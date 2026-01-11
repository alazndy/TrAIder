"""
Download ML models from Firebase Storage on startup.
Called automatically when the app starts on Render.
"""
import os
import firebase_admin
from firebase_admin import credentials, storage

def download_models():
    """Download all .pkl files from Firebase Storage to local data/ folder."""
    
    # Skip if models already exist
    if os.path.exists("data/ai_BTC_USDT.pkl"):
        print("[MODEL_SYNC] Models already exist locally. Skipping download.")
        return
    
    print("[MODEL_SYNC] Downloading models from Firebase Storage...")
    
    try:
        bucket = storage.bucket()
        blobs = bucket.list_blobs(prefix="models/data/")
        
        downloaded = 0
        for blob in blobs:
            if blob.name.endswith('.pkl'):
                # Convert cloud path to local path
                local_path = blob.name.replace("models/", "").replace("/", os.sep)
                
                # Create directory if needed
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                # Download file
                blob.download_to_filename(local_path)
                downloaded += 1
                
                if downloaded % 50 == 0:
                    print(f"  [MODEL_SYNC] Downloaded {downloaded} models...")
        
        print(f"[MODEL_SYNC] ✅ Downloaded {downloaded} models successfully!")
        
    except Exception as e:
        print(f"[MODEL_SYNC] ⚠️ Error downloading models: {e}")
        print("[MODEL_SYNC] Will continue without AI models (fallback to simpler strategies)")

if __name__ == "__main__":
    # For local testing
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'tr-ai-der.firebasestorage.app'
        })
    download_models()
