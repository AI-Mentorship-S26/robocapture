import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import numpy
from supabase import create_client 
from dotenv import load_dotenv
import os


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
model.eval()

model.classifier = torch.nn.Identity()

transform = transforms.Compose([transforms.Resize((224,224)),
                                transforms.ToTensor(),
                                transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])
                                ])
img_path = input("enter the images location : ")
img = Image.open(img_path).convert("RGB")
tensor = transform(img).unsqueeze(0)
with torch.no_grad():
    vector = model(tensor)
vector =  vector.squeeze().numpy()
print(vector.shape)
print(vector)


response = supabase.table("image_vectors").insert({"filename" : img_path, "embedding" : vector.tolist()}).execute()
print(response)
