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
        # Initialize Firebase with explicit credentials if not already done
        if not firebase_admin._apps:
            # 1. Check for JSON Content in Env Var (Render Support)
            import json
            env_creds_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
            cred = None
            
            if env_creds_json:
                try:
                    if env_creds_json.startswith("'") and env_creds_json.endswith("'"):
                        env_creds_json = env_creds_json[1:-1]
                    cred_dict = json.loads(env_creds_json)
                    cred = credentials.Certificate(cred_dict)
                    print("[MODEL_SYNC] Loaded credentials from FIREBASE_CREDENTIALS_JSON")
                except Exception as e:
                    print(f"[MODEL_SYNC] Failed to parse env var credentials: {e}")
            
            # 2. Check for File
            if not cred:
                cred_path = "serviceAccountKey.json"
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    print("[MODEL_SYNC] Firebase initialized with credentials file.")

            # 3. Init App
            if cred:
                firebase_admin.initialize_app(cred, {
                    'storageBucket': 'tr-ai-der.firebasestorage.app'
                })
            else:
                # Try default credentials (Cloud Run, etc)
                firebase_admin.initialize_app(options={
                    'storageBucket': 'tr-ai-der.firebasestorage.app'
                })
                print("[MODEL_SYNC] Firebase initialized with default credentials.")
        
        bucket = storage.bucket()
        blobs = list(bucket.list_blobs(prefix="models/data/"))
        
        if len(blobs) == 0:
            print("[MODEL_SYNC] No models found in cloud storage.")
            return
            
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
    download_models()
