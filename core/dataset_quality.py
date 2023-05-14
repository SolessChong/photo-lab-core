from core.face_mask import get_face_mask, crop_face_img
import os
import cv2
import logging
import concurrent.futures
import json
import numpy as np
from scipy.stats import entropy
from PIL import Image
from typing import List
from torchvision import transforms
from torchvision.models import resnet50, vgg16
from core.resource_manager import pil_to_cv2, read_PILimg
from sklearn.cluster import KMeans
from sklearn.metrics import pairwise_distances
from backend import models
from backend.extensions import db, app
import argparse
from typing import Tuple, Dict

from insightface.app import FaceAnalysis
from insightface.data import get_image as ins_get_image


# Global variables
model = None
face_analysis = None

def get_face_analysis() -> FaceAnalysis:
    global face_analysis
    if face_analysis is None:
        face_analysis = FaceAnalysis(allowed_modules=['detection', 'landmark_2d_106', 'landmark_3d_68'])
        face_analysis.prepare(ctx_id=0, det_size=(640, 640))
    return face_analysis

def get_model() -> vgg16:
    global model
    if model is None:
        model = vgg16(pretrained=True)
        model.eval()
    return model


######## Background variety ########
##
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

def analyze_background_variety(images: List[Image.Image]) -> float:
    # Extract backgrounds and convert them to feature vectors
    def process_image(image):
        face_masks = get_face_mask(image)
        features = []
        for face_mask in face_masks:
            background = extract_background(image, face_mask)
            features.append(image_to_feature_vector(background, get_model()))
        return features

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(process_image, images)

    # Flatten the results into a single list of feature vectors
    feature_vectors = [feature for sublist in results for feature in sublist]

    # Ensure all feature vectors have the same shape
    feature_vectors = np.stack(feature_vectors)
    print(f"Feature vectors shape: {feature_vectors.shape}")

    # Calculate the average pairwise distance between feature vectors using the Euclidean metric
    distances = pairwise_distances(feature_vectors.reshape(len(feature_vectors), -1))
    avg_pairwise_distance = np.mean(distances)

    print(f"Average pairwise distance: {avg_pairwise_distance}")

    # map avg_pairwise_distance from [130, 250] to [0, 1] linearly
    variety_score = (avg_pairwise_distance - 100) / (250 - 100)

    return variety_score


######## Face pose variety ########
## 
def analyze_face_pose_variety(images: List[Image.Image]) -> float:
    pose_vectors = []

    def process_image(image):
        img = pil_to_cv2(image)
        rst = get_face_analysis().get(img)
        if len(rst) > 0:
            pose = rst[0].pose
            return pose

    with concurrent.futures.ThreadPoolExecutor() as executor:
        pose_vectors = list(executor.map(process_image, images))

    # Remove None values in case some images didn't return a pose
    pose_vectors = [pose for pose in pose_vectors if pose is not None]

    pose_vectors = np.array(pose_vectors)

    # Calculate the average pairwise distance between pose vectors
    distances = pairwise_distances(pose_vectors)
    avg_pairwise_distance = np.mean(distances)

    print(f"Average pairwise distance: {avg_pairwise_distance}")

    # map avg_pairwise_distance from [4, 30] to [0, 1] linearly
    variety_score = (avg_pairwise_distance - 4) / (30 - 4)
    return variety_score


# Occlusion detection

######## Image Quality ########
##
def estimate_jpeg_compression(image: np.ndarray) -> float:
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    dct_coefficients = cv2.dct(np.float32(gray_image)/255.0)
    compression_level = np.mean(np.abs(dct_coefficients))
    # map compression_level from [0.01, 0.05] to [0, 1] linearly
    compression_level = (compression_level - 0.01) / (0.05 - 0.01)
    return compression_level

def estimate_blurriness(image: np.ndarray) -> float:
    face_area = pil_to_cv2(crop_face_img(image, 0.5)[0])
    gray_image = cv2.cvtColor(face_area, cv2.COLOR_BGR2GRAY)

    cv2.imwrite('face_area.png', gray_image)

    laplacian_variance = cv2.Laplacian(gray_image, cv2.CV_64F).var()
    # map laplacian_variance from [0, 800] to [0, 1] linearly
    laplacian_variance = (laplacian_variance - 0) / (800 - 0)

    return laplacian_variance



def estimate_lighting_conditions(image: np.ndarray) -> float:
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray_image], [0], None, [256], [0, 256])
    hist_norm = hist.ravel() / hist.sum()
    lighting_entropy = entropy(hist_norm)
    # map lighting_entropy from [3, 7] to [0, 1] linearly
    lighting_entropy = (lighting_entropy - 3) / (7 - 3)
    return lighting_entropy

def analyze_image_quality(images: List[Image.Image]) -> dict:
    background_variety_score = analyze_background_variety(images)
    face_pose_variety_score = analyze_face_pose_variety(images)
    
    def process_image(image):
        try:
            img_np = np.array(image.convert("RGB"))[:, :, ::-1].copy()

            jpeg_compression_score = estimate_jpeg_compression(img_np)
            blurriness_score = estimate_blurriness(img_np)
            lighting_score = estimate_lighting_conditions(img_np)
            return (jpeg_compression_score, blurriness_score, lighting_score)
        except Exception as e:
            logging.exception(f"Error: {e}")
            return (None, None, None)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        scores = list(executor.map(process_image, images))

    # Unpack the scores
    jpeg_compression_scores, blurriness_scores, lighting_scores = zip(*scores)

    # Filter out the None values
    jpeg_compression_scores = [score for score in jpeg_compression_scores if score is not None]
    blurriness_scores = [score for score in blurriness_scores if score is not None]
    lighting_scores = [score for score in lighting_scores if score is not None]
                
    avg_jpeg_compression = np.mean(jpeg_compression_scores)
    avg_blurriness = np.mean(blurriness_scores)
    avg_lighting = np.mean(lighting_scores)

    # num_score: linear score, <10 imgs: 0; 1-20 imgs: 0-0.6; >20 imgs: 0.6-1
    num_score = min(1, max(0, (len(images) - 10) / 10 * 0.6))
    
    quality_report = {
        "num_score": num_score,
        "background_variety": background_variety_score,
        "face_pose_variety": face_pose_variety_score,
        "jpeg_compression": avg_jpeg_compression,
        "blurriness": avg_blurriness,
        "lighting": avg_lighting
    }
    
    comments = []
    with open(os.path.join(os.path.dirname(__file__), "resources/image_quality_suggestions.json"), "r") as f:
        suggestions = json.load(f)
    for key, value in quality_report.items():
        if value < suggestions[key]["threshold"]:
            comments.append(f"{suggestions[key]['problem']}:\n{suggestions[key]['suggestion']}\n")

    comment_string = "\n".join(comments)    
    return quality_report, comment_string

def analyze_person(person_id: int) -> Tuple[Dict, str]:
    sources = models.Source.query.filter_by(person_id=person_id).all()
    if len(sources) == 0:
        print("===== Person {} =====".format(person_id))
        print("No sources found.")
        return
    images = []
    def read_image(source):
        return read_PILimg(source.base_img_key)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        images = list(executor.map(read_image, sources))
    quality_report, comment_string = analyze_image_quality(images)
    print("===== Person {} =====".format(person_id))
    person =  models.Person.query.get(person_id)
    person.dataset_quality = quality_report
    db.session.add(person)
    db.session.commit()

    return quality_report, comment_string
    
def is_qualified(quality_report, suggestions):
    for key, value in quality_report.items():
        if key in suggestions and value < suggestions[key]["threshold"]:
            return False
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--person_id", type=int, help="person id")    

    app.app_context().push()

    if parser.parse_args().person_id:
        persons = models.Person.query.filter_by(id=parser.parse_args().person_id).all()
    else:
        # iterate over all persons id desc
        persons = models.Person.query.order_by(models.Person.id.desc()).all()

    for person in persons:
        try:
            analyze_person(person.id)
        except Exception as e:
            logging.exception(f"Error: {e}")
