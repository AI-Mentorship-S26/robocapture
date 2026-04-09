import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import numpy
from supabase import create_client 
from dotenv import load_dotenv
import os


import sys

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Optimize PyTorch CPU execution for single-request processing
torch.set_grad_enabled(False)
torch.set_num_threads(1)  # Prevents thread starvation under load

model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
model.eval()

model.classifier = torch.nn.Identity()

transform = transforms.Compose([transforms.Resize((224,224)),
                                transforms.ToTensor(),
                                transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])
                                ])

# Support command line args for web backend, or fallback to input
if len(sys.argv) > 1:
    img_path = sys.argv[1]
    user_id = sys.argv[2] if len(sys.argv) > 2 else "anonymous"
else:
    img_path = input("enter the images location : ")
    user_id = "local_test_user"

try:
    img = Image.open(img_path).convert("RGB")
    tensor = transform(img).unsqueeze(0)
    with torch.no_grad():
        vector = model(tensor)
    vector =  vector.squeeze().numpy()

    # Pass the user_id (make sure the user_id column exists in Supabase!)
    payload = {"filename": img_path, "embedding": vector.tolist(), "user_id": user_id}
    
    # We output a clean JSON response if called from Node
    if len(sys.argv) > 1:
        response = supabase.table("image_vectors").insert(payload).execute()
        import json
        print(json.dumps({"success": True, "message": "Successfully vectorized and uploaded", "path": img_path}))
    else:
        print(vector.shape)
        print(vector)
        response = supabase.table("image_vectors").insert(payload).execute()
        print(response)

except Exception as e:
    if len(sys.argv) > 1:
        import json
        print(json.dumps({"success": False, "error": str(e)}))
    else:
        print(f"Error: {e}")
