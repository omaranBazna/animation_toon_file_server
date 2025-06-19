import os
import requests
import time
from characters import thumbnail_list
# Base URL for the images
base_url = "https://new.express.adobe.com/static/"

# Folder to save downloaded images
output_dir = "downloaded_thumbnails"
os.makedirs(output_dir, exist_ok=True)

# Download each image
for filename in thumbnail_list:
    url = base_url + filename
    print(f"Downloading {filename}...")
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise error on bad status
        with open(os.path.join(output_dir, filename), "wb") as f:
            f.write(response.content)
        time.sleep(1)  # Sleep for 1 second between downloads
    except Exception as e:
        print(f"❌ Failed to download {filename}: {e}")