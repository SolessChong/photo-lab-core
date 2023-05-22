from PIL import Image
import argparse
import cv2
import logging
from core import conf
from insightface.app import FaceAnalysis
from pathlib import Path
from core import templates
import webuiapi
from core import face_mask
from core.libs.openpose.body import Body
from core import pose_detect
from backend import models
from backend.extensions import app, migrate, db

import numpy as np
import typing
from core.libs.openpose.util import draw_bodypose
from core.resource_manager import *

api = webuiapi.WebUIApi(host='127.0.0.1', port=7890)
body_estimate = Body()

face_analysis = None
def get_face_analysis() -> FaceAnalysis:
    global face_analysis
    if face_analysis is None:
        face_analysis = FaceAnalysis(name='buffalo_l')
        face_analysis.prepare(ctx_id=0, det_size=(640, 640))
    return face_analysis

def prepare_scene(scene_id):
    # download base_img
    base_img_url = models.Scene.query.get(scene_id).base_img_key
    if base_img_url is None:
        raise Exception(f"Base image not found! Scene: {scene_id}")

    # generate pose_img if not exist
    pose_img_url = models.Scene.query.get(scene_id).get_pose_img()

    ## Use pose_img_url as flag for raw scene.
    # if file doesn't exist, generate it using openpose.body.Body
    if pose_img_url is None:
        base_img = read_PILimg(base_img_url)
        # super res if base img too small
        if base_img.width < 1500 or base_img.height < 1500:
            resize = 1500 / base_img.width
            if resize > 1.2:
                rst = api.extra_single_image(base_img, upscaler_1=webuiapi.Upscaler.ESRGAN_4x, upscaling_resize=resize)
                base_img = rst.image
                write_PILimg(base_img, base_img_url)
                logging.info(f"Base image super-res by {resize}, saved to {base_img_url}.")
            else:
                logging.info(f"Resize < 1.2, skip super-res.")
        pose_img_url = f'source/pose/{scene_id}.png'
        base_img_cv2 = pil_to_cv2(base_img)
        candidate, subset = body_estimate(base_img_cv2)
        # draw pose map on blank image
        pose_map = np.zeros(base_img_cv2.shape).astype('uint8')
        pose_map = draw_bodypose(pose_map, candidate, subset)
        # save pose map
        write_cv2img(pose_map, pose_img_url)

        scene = models.Scene.query.get(scene_id)
        scene.update_pose_img(pose_img_url)

        logging.info(f"Pose map generated and saved to {pose_img_url}.")
    else:
        logging.info(f"Pose map already exists, skip generating.")

    # Generate ROI list
    if models.Scene.query.get(scene_id).roi_list:
        logging.info(f"ROI list already exists, skip generating.")
    else:
        prepare_scene_roi_list(scene_id)

    return True

def prepare_scene_roi_list(scene_id):
    scene = models.Scene.query.get(scene_id)
    base_img_url = scene.base_img_key
    base_img = read_PILimg(base_img_url)
    cv2_base_image = cv2.cvtColor(np.array(base_img), cv2.COLOR_RGB2BGR)

    # detect face and human
    mask_list = face_mask.get_face_mask(base_img, expand_face=1.5)
    [candidates, subset] = body_estimate(cv2_base_image)

    if len(mask_list) != len(subset):
        raise Exception("Face mask and Human count mismatch!")

    roi_list = []  # List to store bounding boxes
    for i in range(len(mask_list)):
        upper_body_landmarks = [0, 1, 14, 15, 16, 17]  # Landmark indices for upper body
        upper_body_coords = [(candidates[int(subset[i][k])][0], candidates[int(subset[i][k])][1]) for k in upper_body_landmarks if subset[i][k] != -1]
        # calculate foread
        nose_x, nose_y = candidates[int(subset[i][0])][0], candidates[int(subset[i][0])][1]
        left_eye_x, left_eye_y = candidates[int(subset[i][15])][0], candidates[int(subset[i][15])][1]
        right_eye_x, right_eye_y = candidates[int(subset[i][16])][0], candidates[int(subset[i][16])][1]
        # Calculate the midpoint between the eyes
        # Calculate the vectors from the nose to the left eye and from the nose to the right eye
        nose_to_left_eye = (left_eye_x - nose_x, left_eye_y - nose_y)
        nose_to_right_eye = (right_eye_x - nose_x, right_eye_y - nose_y)

        # Calculate the linear combination of the vectors
        combination_factor = 2.5
        forehead_x = nose_x + (nose_to_left_eye[0] + nose_to_right_eye[0]) / 2 * combination_factor
        forehead_y = nose_y + (nose_to_left_eye[1] + nose_to_right_eye[1]) / 2 * combination_factor

        upper_body_coords.append((forehead_x, forehead_y))

        cropped_base_img, bb = pose_detect.crop_image(cv2_base_image, upper_body_coords, enlarge=2.6)
        # bb = (x_min, y_min, width, height)
        rst = get_face_analysis().get(cropped_base_img)
        person_gender = 'girl' if rst[0]['gender'] == 0 else 'boy'
        roi_list.append({'bb': bb, 'sex': person_gender})

    # Store the roi_list in the Scene model
    scene.roi_list = roi_list
    db.session.commit()


if __name__ == "__main__":
    # args:
    # --scene, list of multiple scene id
    # --collection
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--scene', nargs='+', help='scene id')
    argparser.add_argument('--collection', help='collection id')
    # must have one of scene or collection
    args = argparser.parse_args()
    assert args.scene or args.collection, "Must have one of arguments: scene or collection"

    app.app_context().push()
    if args.scene:
        scene_id_list = args.scene
    elif args.collection:
        scene_id_list = [scene.scene_id for scene in models.Scene.query.filter(models.Scene.collection_name == args.collection).all()]

    logging.info(f"Start preparing scene: {scene_id_list}")

    for scene_id in scene_id_list:
        try:
            prepare_scene(scene_id)
            models.Scene.query.get(scene_id).update_setup_status('finish')
        except Exception as e:
            logging.exception(f"Error processing scene [{scene_id}]: {e}")

