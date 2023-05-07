import cv2
import numpy as np
from PIL import Image
from typing import List
import os
from core.resource_manager import cv2_to_pil
from insightface.app import FaceAnalysis
from insightface.data import get_image as ins_get_image

face_analysis = None

def get_face_analysis_instance() -> FaceAnalysis:
    global face_analysis_instance
    if face_analysis_instance is None:
        face_analysis_instance = FaceAnalysis(allowed_modules=['detection', 'landmark_2d_106'])
        face_analysis_instance.prepare(ctx_id=0, det_size=(640, 640))
    return face_analysis_instance

# return array of PIL.Image
def get_face_mask(image: Image.Image, expand_face=0.6) -> List[Image.Image]:
    image = np.array(image)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    # Detect the face(s) in the image
    faces = get_face_analysis_instance().get(image)

    # Loop through each detected face
    mask_list = []
    for face in faces:
        # Predict facial landmarks
        lmk = np.round(face.landmark_2d_106).astype(np.int)

        # estimate forhead with nose and eye
        vec = (lmk[39] + lmk[89]) / 2 - lmk[80]
        left_forehead = lmk[1] + vec
        right_forehead = lmk[17] + vec

        # Get the points of interest (landmarks) for the face mask
        mask_points = []
        for i in range(0, 33):
            mask_points.append((lmk[i][0], lmk[i][1]))
        mask_points.append((int(left_forehead[0]), int(left_forehead[1])))
        mask_points.append((int(right_forehead[0]), int(right_forehead[1])))

        # Create a mask using the mask_points
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        convex_hull = cv2.convexHull(np.array(mask_points))
        mask = cv2.fillConvexPoly(mask, convex_hull, (255,))
        # expand the mask to include the entire face
        if expand_face:
            r = int((face.bbox[2] - face.bbox[0]) * expand_face / 2)
            mask = cv2.dilate(mask, np.ones((r, r), np.uint8), iterations=1)

        # Apply the mask to the original image
        # result = cv2.bitwise_and(image, image, mask=mask)
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2RGB)
        mask = Image.fromarray(mask)
        mask_list.append(mask)

    return mask_list

def crop_face_img(image: Image, enlarge=0.3) -> List[Image.Image]:
    image = np.array(image)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    # Detect the face(s) in the image
    faces = get_face_analysis_instance().get(image)
    face_imgs = []
    for face in faces:
        # enlarge the bounding box by enlarge
        r = int((face.bbox[2] - face.bbox[0]) * enlarge / 2)
        b = face.bbox
        b[0] = max(0, b[0] - r)
        b[1] = max(0, b[1] - r)
        b[2] = min(image.shape[1], b[2] + r)
        b[3] = min(image.shape[0], b[3] + r)

        # crop the face
        face_img = image[int(b[1]):int(b[3]), int(b[0]):int(b[2])]

        face_imgs.append(cv2_to_pil(face_img))
    return face_imgs
    