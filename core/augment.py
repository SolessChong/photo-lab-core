from core.face_mask import get_face_mask, crop_face_img
import os
import cv2
import logging
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

from insightface.app import FaceAnalysis
from insightface.data import get_image as ins_get_image
from concurrent.futures import ThreadPoolExecutor

# Global variables
face_analysis = None
def get_face_analysis_instance() -> FaceAnalysis:
    global face_analysis
    if face_analysis is None:
        face_analysis = FaceAnalysis(allowed_modules=['detection', 'landmark_3d_68'])
        face_analysis.prepare(ctx_id=0, det_size=(640, 640))
    return face_analysis

def save_rotated_image(image, roll, fn, angle, r):
    rotated_image = image.rotate(roll * angle, resample=Image.BICUBIC, expand=True)

    # Save the augmented image
    file_name, file_ext = os.path.splitext(fn)
    rotated_image.save(f"{file_name}_aug_rot_{r}{file_ext}")

# Augment image
def aug_img(fn: str):
    image = Image.open(fn)
    img = pil_to_cv2(image)
    rst = get_face_analysis_instance().get(img)

    if len(rst) > 0:
        pose = rst[0].pose
        #pitch, yaw, roll
        roll = pose[2]

        # Rotate the image to make the head horizontally straight
        angles =  [-0.8, -0.5, 0.5, 0.75, 1, 1.25, 1.5, 1.8]
        with ThreadPoolExecutor() as executor:
            for r, angle in enumerate(angles):
                executor.submit(save_rotated_image, image, roll, fn, angle, r)

        # Flip the image left-right
        flipped_image = image.transpose(Image.FLIP_LEFT_RIGHT)

        # Save the flipped image
        file_name, file_ext = os.path.splitext(fn)
        flipped_image.save(f"{file_name}_aug_flip{file_ext}")
    else:
        print(f"No face detected in the image: {fn}")
    return len(angles) + 1

def aug_folder(folder: str):
    total = 0
    for fn in os.listdir(folder):
        if fn.endswith(".jpg") or fn.endswith(".png"):
            try:
                n = aug_img(os.path.join(folder, fn))
                total += n + 1    # original + augmented
            except Exception as e:
                logging.exception(f"Error augmenting image: {fn}")
    return total

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Augment images in a folder")
    parser.add_argument("folder", help="Path to the folder containing images to be augmented")
    args = parser.parse_args()

    # Augment images in the folder
    aug_folder(args.folder)