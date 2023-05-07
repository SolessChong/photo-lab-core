from core.face_mask import get_face_mask
import os
import numpy as np
from PIL import Image
from typing import List
from torchvision import transforms
from torchvision.models import resnet50, vgg16
from core.resource_manager import pil_to_cv2
import torch
from sklearn.cluster import KMeans
from sklearn.metrics import pairwise_distances

from insightface.app import FaceAnalysis
from insightface.data import get_image as ins_get_image



def extract_background(image: Image.Image, face_mask: Image.Image) -> Image.Image:
    background = Image.composite(Image.new("RGB", image.size), image, face_mask.convert("L"))
    background.save('background.png')
    return background

def image_to_feature_vector(image: Image.Image, model) -> np.ndarray:
    preprocess = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    
    input_tensor = preprocess(image).unsqueeze(0)  # Create a mini-batch as expected by the model
    features = model.features(input_tensor).detach().numpy().reshape(-1)
    
    return features

from sklearn.preprocessing import normalize
from sklearn.metrics import silhouette_score

def optimal_num_clusters(feature_vectors, max_clusters=10):
    wcss = []
    for i in range(2, max_clusters + 1):
        kmeans = KMeans(n_clusters=i, random_state=42)
        kmeans.fit(feature_vectors)
        wcss.append(kmeans.inertia_)

    # Calculate the "elbow point" using the second derivative of the WCSS curve
    deltas = np.diff(wcss, 2)
    elbow_point = np.argmax(deltas) + 2

    return elbow_point


model = vgg16(pretrained=True)
model.eval()

def analyze_background_variety(images: List[Image.Image]) -> float:
    # Extract backgrounds and convert them to feature vectors
    feature_vectors = []
    for image in images:
        face_masks = get_face_mask(image)
        for face_mask in face_masks:
            background = extract_background(image, face_mask)
            features = image_to_feature_vector(background, model)
            feature_vectors.append(features)

    # Ensure all feature vectors have the same shape
    feature_vectors = np.stack(feature_vectors)
    print(f"Feature vectors shape: {feature_vectors.shape}")

    # Calculate the average pairwise distance between feature vectors using the Euclidean metric
    distances = pairwise_distances(feature_vectors.reshape(len(feature_vectors), -1))
    avg_pairwise_distance = np.mean(distances)

    # Normalize the variety score between 0 and 1
    variety_score = avg_pairwise_distance

    print(f"Average pairwise distance: {avg_pairwise_distance}, variety score: {variety_score}")

    # map avg_pairwise_distance from [130, 250] to [0, 1] linearly
    avg_pairwise_distance = (avg_pairwise_distance - 130) / (250 - 130)
    
    return variety_score

def analyze_face_pose_variety(images: List[Image.Image]) -> float:
    pose_vectors = []

    for image in images:
        img = pil_to_cv2(image)
        rst = face_analysis.get(img)
        
        if len(rst) > 0:
            pose = rst[0].pose
            pose_vectors.append(pose)

    pose_vectors = np.array(pose_vectors)

    # Calculate the average pairwise distance between pose vectors
    distances = pairwise_distances(pose_vectors)
    avg_pairwise_distance = np.mean(distances)

    print(f"Average pairwise distance: {avg_pairwise_distance}")

    # map avg_pairwise_distance from [4, 25] to [0, 1] linearly
    avg_pairwise_distance = (avg_pairwise_distance - 4) / (25 - 4)
    return avg_pairwise_distance


# Occlusion detection
# Image quality

face_analysis = None

if __name__ == "__main__":
    face_analysis = FaceAnalysis(allowed_modules=['detection', 'landmark_2d_106', 'landmark_3d_68'])
    face_analysis.prepare(ctx_id=0, det_size=(640, 640))

    for dataset_name in [2, 3, 6, 127, 190, 255, 256, 271, 273]:
        print(f"===== Dataset {dataset_name} =====")
        dir_name = f"core/data/train_dataset/{dataset_name}/img_raw"
        images = []  # List of PIL.Image objects
        for fn in os.listdir(dir_name):
            img = Image.open(os.path.join(dir_name, fn))
            images.append(img)
        variety_score_background = analyze_background_variety(images)
        variety_score_face_pose = analyze_face_pose_variety(images)
        print(f"Variety score (background): {variety_score_background}, variety score (face pose): {variety_score_face_pose}")