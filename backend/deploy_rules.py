import json
import requests
import firebase_admin
from firebase_admin import credentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Configuration
SERVICE_ACCOUNT_FILE = "backend/serviceAccountKey.json"
RULES_FILE = "firestore.rules"
PROJECT_ID = "tr-ai-der"

def get_access_token():
    """Get access token from service account file"""
    scopes = ['https://www.googleapis.com/auth/cloud-platform']
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=scopes)
    creds.refresh(Request())
    return creds.token

def deploy_rules():
    print(f"Deploying Firestore rules to {PROJECT_ID}...")
    
    # 1. Read rules content
    with open(RULES_FILE, "r") as f:
        rules_content = f.read()
    
    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 2. Create a new Ruleset
    print("Creating new Ruleset...")
    create_ruleset_url = f"https://firebaserules.googleapis.com/v1/projects/{PROJECT_ID}/rulesets"
    
    ruleset_payload = {
        "source": {
            "files": [
                {
                    "content": rules_content,
                    "name": "firestore.rules"
                }
            ]
        }
    }
    
    response = requests.post(create_ruleset_url, headers=headers, json=ruleset_payload)
    if response.status_code != 200:
        print(f"Failed to create ruleset: {response.text}")
        return

    ruleset_name = response.json()["name"]
    print(f"Ruleset created: {ruleset_name}")

    # 3. Update the Release to point to the new Ruleset
    print("Updating Release...")
    release_name = f"projects/{PROJECT_ID}/releases/cloud.firestore"
    
    release_payload = {
        "name": release_name,
        "rulesetName": ruleset_name
    }
    
    # We use PATCH to update existing release, or POST to create if not exists?
    # Usually update is PATCH on the release name
    update_response = requests.patch(
        f"https://firebaserules.googleapis.com/v1/{release_name}",
        headers=headers,
        json={"rulesetName": ruleset_name}
    )
    
    if update_response.status_code != 200:
        # If it doesn't exist, maybe we try create? But usually cloud.firestore exists.
        print(f"Update failed, trying create... ({update_response.text})")
        create_release_url = f"https://firebaserules.googleapis.com/v1/projects/{PROJECT_ID}/releases"
        create_response = requests.post(
            create_release_url, 
            headers=headers, 
            json=release_payload
        )
        if create_response.status_code != 200:
            print(f"Failed to release rules: {create_response.text}")
            return
        print("Release created successfully!")
    else:
        print("Release updated successfully!")

    print("Deployment Complete! Firestore rules are active.")

if __name__ == "__main__":
    deploy_rules()
