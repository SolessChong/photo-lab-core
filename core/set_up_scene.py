from PIL import Image
import os
import io
import rembg
import cv2
import subprocess
import logging
from core import conf
import re
import math
import shutil
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

def prepare_scene(scene_id):
    # download base_img
    base_img_url = models.Scene.query.get(scene_id).base_img_key
    if base_img_url is None:
        raise Exception(f"Base image not found! Scene: {scene_id}")
    # raise if base doesn't exist
    # if not os.path.exists(base_img_path):
    #     raise Exception(f"Base image not found! {base_img_path}")

    # generate pose_img if not exist
    pose_img_url = models.Scene.query.get(scene_id).get_pose_img()
        
    ## Use pose_img_url as flag for raw scene.
    # if file doesn't exist, generate it using openpose.body.Body
    if pose_img_url is None:
        base_img = read_PILimg(base_img_url)
        # super res if base img too small
        if base_img.width < 1500 or base_img.height < 1500:
            resize = 2048 / base_img.width
            rst = api.extra_single_image(base_img, upscaler_1=webuiapi.Upscaler.ESRGAN_4x, upscaling_resize=resize)
            base_img = rst.image
            write_PILimg(base_img, base_img_url)
            logging.info(f"Base image super-res by {resize}, saved to {base_img_url}.")
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

    return True


def main():
    app.app_context().push()
    for i in range(557, 569):
        prepare_scene(i)

if __name__ == "__main__":
    main()