import firebase_admin
from firebase_admin import credentials, firestore
import os
import sys

def reset_all_data():
    # Initialize Firebase
    cred_path = "backend/serviceAccountKey.json"
    if not os.path.exists(cred_path):
        cred_path = "serviceAccountKey.json"
        
    if not os.path.exists(cred_path):
        print(f"Error: Credentials file not found at {cred_path}")
        return

    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    collections = ["signals", "backtests", "trades", "portfolios", "portfolio_snapshots"]
    
    print("WARNING: This will delete ALL data from the following collections:")
    for c in collections:
        print(f" - {c}")
    
    print("\nStarting deletion process...")
    
    for coll_name in collections:
        print(f"[*] Deleting collection: {coll_name}...")
        delete_collection(db.collection(coll_name), batch_size=50)
        print(f"[+] Collection {coll_name} deleted.")

    print("\n[SUCCESS] All data has been reset.")

def delete_collection(coll_ref, batch_size):
    """Recursively delete a collection in batches."""
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)

if __name__ == "__main__":
    reset_all_data()
