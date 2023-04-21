import os
import requests
import json
import shutil

# Replace with your Bing Image Search API key
API_KEY = "87eaa95062ba42399cd23525e4de48c1"

# Define the search query and parameters
person_name = "周杰伦"
offset = 0
search_query = person_name
search_url = "https://api.bing.microsoft.com/v7.0/images/search"
headers = {"Ocp-Apim-Subscription-Key": API_KEY}
params = {"q": search_query, "count": 200, "offset": offset}  # Adjust the count to get more or fewer images

# Make the API request
response = requests.get(search_url, headers=headers, params=params)
response.raise_for_status()
results = response.json()

# Create the "data" directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# Create a directory for the person's images under the "data" directory
person_dir = os.path.join("pipeline/data", person_name)
os.makedirs(person_dir, exist_ok=True)

# Download the images
for idx, image in enumerate(results["value"]):
    image_url = image["contentUrl"]
    try:
        response = requests.get(image_url, stream=True, timeout=5)
        response.raise_for_status()

        # Save the image to the person's directory under the "data" directory
        image_file = os.path.join(person_dir, f"img_{idx + offset}.jpg")
        with open(image_file, "wb") as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)

        print(f"Downloaded {image_file}")

    except Exception as e:
        print(f"Error downloading image {idx}: {e}")