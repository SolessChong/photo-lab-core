import os
import requests
import json
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
import argparse

# Replace with your Bing Image Search API key
API_KEY = "50b4fa16370d400fadb079dd7389aaba"

# Define the search query and parameters
search_url = "https://api.bing.microsoft.com/v7.0/images/search"
headers = {"Ocp-Apim-Subscription-Key": API_KEY}
MAX_RESULTS_PER_REQUEST = 50

def download_images(person_name, offset, count):
    # Calculate the number of requests needed
    num_requests = count // MAX_RESULTS_PER_REQUEST
    remaining_images = count % MAX_RESULTS_PER_REQUEST

    # Create the "data" directory if it doesn't exist
    os.makedirs("data", exist_ok=True)

    # Create a directory for the person's images under the "data" directory
    person_dir = os.path.join("pipeline/data", person_name)
    os.makedirs(person_dir, exist_ok=True)

    def download_image(idx, image_url, person_dir, offset):
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


    # Download the images using multiple threads
    with ThreadPoolExecutor(max_workers=20) as executor:
        for i in range(num_requests):
            params = {"q": person_name, "count": MAX_RESULTS_PER_REQUEST, "offset": offset + i * MAX_RESULTS_PER_REQUEST}
            response = requests.get(search_url, headers=headers, params=params)
            response.raise_for_status()
            results = response.json()

            futures = [
                executor.submit(download_image, idx, image["contentUrl"], person_dir, offset + i * MAX_RESULTS_PER_REQUEST)
                for idx, image in enumerate(results["value"])
            ]

            wait(futures)

        if remaining_images > 0:
            params = {"q": person_name, "count": remaining_images, "offset": offset + num_requests * MAX_RESULTS_PER_REQUEST}
            response = requests.get(search_url, headers=headers, params=params)
            response.raise_for_status()
            results = response.json()

            futures = [
                executor.submit(download_image, idx, image["contentUrl"], person_dir, offset + num_requests * MAX_RESULTS_PER_REQUEST)
                for idx, image in enumerate(results["value"])
            ]

            wait(futures)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download images.')
    parser.add_argument('-p', '--person_name', help='The name of the person', required=True)
    parser.add_argument('-o', '--offset', type=int, help='The offset for images', default=0)
    parser.add_argument('-c', '--count', type=int, help='The number of images', default=100)
    args = parser.parse_args()

    download_images(args.person_name, args.offset, args.count)
