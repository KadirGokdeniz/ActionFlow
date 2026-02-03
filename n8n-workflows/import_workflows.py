import requests
import json
import os
from dotenv import load_dotenv

import pathlib
dotenv_path = pathlib.Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path)

N8N_URL = "http://localhost:5678"
WORKFLOWS_DIR = "n8n-workflows"
API_KEY = os.getenv("N8N_API_KEY")  # ← .env'den oku

if not API_KEY:
    print("❌ Error: N8N_API_KEY not found in .env file!")
    exit(1)

workflows = [
    "escalation_alert.json",
    "booking_confirmation.json",
    "cancellation_refund.json"
]

for workflow_file in workflows:
    filepath = os.path.join(WORKFLOWS_DIR, workflow_file)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        
        # Remove read-only fields
        workflow_data.pop('tags', None)  # ← EKLE
        workflow_data.pop('id', None)     # ← EKLE
        
        response = requests.post(
            f"{N8N_URL}/api/v1/workflows",
            json=workflow_data,
            headers={
                "Content-Type": "application/json",
                "X-N8N-API-KEY": API_KEY
            }
        )
        
        if response.status_code in [200, 201]:
            print(f"✅ Imported: {workflow_file}")
        elif response.status_code == 409:
            print(f"⚠️ Already exists: {workflow_file}")
        else:
            print(f"❌ Failed: {workflow_file} - {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error with {workflow_file}: {e}")

print("\n✅ Import complete!")