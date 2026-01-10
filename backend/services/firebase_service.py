
import firebase_admin
from firebase_admin import credentials, firestore
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

class FirebaseService:
    def __init__(self):
        self.db = None
        self._initialize_app()

    def _initialize_app(self):
        """Initializes Firebase App with credentials."""
        try:
            # Check if already initialized
            if firebase_admin._apps:
                self.db = firestore.client()
                return

            cred_path = os.getenv("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
            
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print(f"[Firebase] Initialized with {cred_path}")
            else:
                # Try default credentials (useful for Cloud Run)
                print("[Firebase] No serviceAccountKey.json found, trying default credentials...")
                firebase_admin.initialize_app()
                
            self.db = firestore.client()
        except Exception as e:
            print(f"[Firebase] Initialization Failed: {e}")
            self.db = None

    def save_backtest(self, result: Dict[str, Any]) -> str:
        """Saves a backtest result to Firestore."""
        if not self.db:
            print("[Firebase] DB not initialized")
            return None
            
        try:
            # Add timestamp
            result["created_at"] = datetime.utcnow()
            
            # Create a new document in 'backtests' collection
            doc_ref = self.db.collection("backtests").document()
            doc_ref.set(result)
            return doc_ref.id
        except Exception as e:
            print(f"[Firebase] Save Error: {e}")
            return None

    def get_recent_backtests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent backtests."""
        if not self.db:
            return []
            
        try:
            docs = self.db.collection("backtests")\
                .order_by("created_at", direction=firestore.Query.DESCENDING)\
                .limit(limit)\
                .stream()
                
            return [{**doc.to_dict(), "id": doc.id} for doc in docs]
        except Exception as e:
            print(f"[Firebase] Fetch Error: {e}")
            return []
            
    def save_trade(self, trade: Dict[str, Any], strategy_id: str):
        """Saves a live trade execution."""
        if not self.db:
            return
            
        try:
            trade["strategy_id"] = strategy_id
            trade["timestamp"] = datetime.utcnow()
            self.db.collection("trades").add(trade)
        except Exception as e:
            print(f"[Firebase] Trade Save Error: {e}")

# Global instance
firebase_client = FirebaseService()
