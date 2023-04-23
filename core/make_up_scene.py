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
from core.resource_manager import ResourceMgr, ResourceType, oss2buf, str2oss, oss2str

body_estimate = Body()

app.app_context().push()

def prepare_scene(scene_id):
    # download base_img
    base_img_url = ResourceMgr.get_resource_local_path( ResourceType.BASE_IMG, scene_id)
    if base_img_url is None:
        return False
    # # raise if base doesn't exist
    # if not os.path.exists(base_img_path):
    #     raise Exception(f"Base image not found! {base_img_path}")

    # generate pose_img if not exist
    pose_img_url = ResourceMgr.get_resource_local_path(ResourceType.POSE_IMG, scene_id)
    # if file doesn't exist, generate it using openpose.body.Body
    if pose_img_url is None:
        pose_img_url = f'source/pose/{scene_id}.png'
        base_img = cv2.imdecode(np.frombuffer(oss2str(base_img_url), np.uint8), 1)
        candidate, subset = body_estimate(base_img)
        # draw pose map on blank image
        pose_map = np.zeros(base_img.shape)
        pose_map = draw_bodypose(pose_map, candidate, subset)
        # save pose map
        is_success, buffer = cv2.imencode(".png", pose_map)
        io_buf = io.BytesIO(buffer)
        str2oss(io_buf, pose_img_url)

        scene = models.Scene.query.get(scene_id)
        scene.update_pose_img(pose_img_url)

        logging.info(f"Pose map generated and saved to {pose_img_url}.")

    return True


def main():
    for i in range(557, 569):
        prepare_scene(i)

if __name__ == "__main__":
    main()