import cv2
import dlib
import numpy as np
from PIL import Image
from typing import List
import os
from insightface.app import FaceAnalysis
from insightface.data import get_image as ins_get_image

face_analysis = FaceAnalysis(allowed_modules=['detection', 'landmark_2d_106'])
face_analysis.prepare(ctx_id=0, det_size=(640, 640))

# return array of PIL.Image
def get_face_mask(image: Image.Image, expand_face=0.6) -> List[Image.Image]:
    image = np.array(image)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    # Detect the face(s) in the image
    faces = face_analysis.get(image)

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


def crop_face_img(image: Image.Image, enlarge=1.2) -> Image.Image:
    # Read the input image
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # get current path
    script_path = os.path.dirname(os.path.abspath(__file__))
    # join path to haarcascade.xml
    xml_path = os.path.join(script_path, 'haarcascade.xml')

    # Load the Haar Cascade Classifier
    face_cascade = cv2.CascadeClassifier(xml_path)

    # Detect faces in the image
    faces = face_cascade.detectMultiScale(
        gray_image,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
        flags=cv2.CASCADE_SCALE_IMAGE
    )

    subj_img = image

    # Check if a face was detected
    # TODO: handle multiple face situation
    if len(faces) > 0:
        x, y, w, h = faces[0]  # Use the first detected face

        # Make the bounding box square
        if w > h:
            y -= (w - h) // 2
            h = w
        elif h > w:
            x -= (h - w) // 2
            w = h

        # Enlarge the bounding box by the specified scale
        scale = enlarge
        w_enlarged, h_enlarged = int(w * scale), int(h * scale)
        x_center, y_center = x + w // 2, y + h // 2
        x, y = x_center - w_enlarged // 2, y_center - int(h / 2 * (1 + (enlarge - 1) * 0.3))
        
        w, h = w_enlarged, h_enlarged

        # Calculate the required padding for each side
        height, width = image.shape[:2]
        left_pad = max(-x, 0)
        right_pad = max(x + w - width, 0)
        top_pad = max(-y, 0)
        bottom_pad = max(y + h - height, 0)

        # Pad the image using the calculated padding values
        image_padded = cv2.copyMakeBorder(image, top_pad, bottom_pad, left_pad, right_pad, cv2.BORDER_CONSTANT, value=(255, 255, 255))

        # Update the bounding box coordinates
        x = x + left_pad
        y = y + top_pad

        # Crop the face and resize it to the desired size
        subj_img = image_padded[y:y + h, x:x + w]

    return subj_img