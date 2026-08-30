from PIL import Image
import os

def convert_to_icon(jpg_path, ico_name):
    if os.path.exists(jpg_path):
        img = Image.open(jpg_path)
        # Resize to 128x128 as requested
        img = img.resize((128, 128), Image.Resampling.LANCZOS)
        img.save(ico_name, format='ICO', sizes=[(128, 128)])
        print(f"Converted {jpg_path} to {ico_name} (128x128)")
    else:
        print(f"File {jpg_path} not found")

if __name__ == "__main__":
    icons = {
        "stormhexeditor.jpg": "stormhexeditor.ico",
        "stormgamedictionary.jpg": "stormgamedictionary.ico",
        "stormtilemanager.jpg": "stormtilemanager.ico",
        "stormsuite.jpg": "stormsuite.ico"
    }
    
    for jpg, ico in icons.items():
        convert_to_icon(jpg, ico)
