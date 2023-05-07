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

# Global variables
face_analysis = None
def get_face_analysis_instance() -> FaceAnalysis:
    global face_analysis_instance
    if face_analysis_instance is None:
        face_analysis_instance = FaceAnalysis(allowed_modules=['detection', 'landmark_3d_68'])
        face_analysis_instance.prepare(ctx_id=0, det_size=(640, 640))
    return face_analysis_instance

# Augment image
def aug_img(fn: str):
    image = Image.open(fn)
    img = pil_to_cv2(image)
    rst = get_face_analysis_instance().get(img)

    if len(rst) > 0:
        pose = rst[0].pose
        roll = pose.roll

        # Rotate the image to make the head horizontally straight
        rotated_image = image.rotate(-roll, resample=Image.BICUBIC, expand=True)

        # Save the augmented image
        file_name, file_ext = os.path.splitext(fn)
        rotated_image.save(f"{file_name}_aug_rot{file_ext}")

        # Flip the image left-right
        flipped_image = image.transpose(Image.FLIP_LEFT_RIGHT)

        # Save the flipped image
        flipped_image.save(f"{file_name}_aug_flip{file_ext}")
    else:
        print(f"No face detected in the image: {fn}")

def aug_folder(folder: str):
    for fn in os.listdir(folder):
        if fn.endswith(".jpg") or fn.endswith(".png"):
            aug_img(os.path.join(folder, fn))

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Augment images in a folder")
    parser.add_argument("folder", help="Path to the folder containing images to be augmented")
    args = parser.parse_args()

    # Augment images in the folder
    aug_folder(args.folder)