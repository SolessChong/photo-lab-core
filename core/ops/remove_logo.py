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
import numpy as np
import typing
from backend import models
from core.libs.openpose.util import draw_bodypose
from core.resource_manager import ResourceMgr, ResourceType, oss2buf, str2oss, read_cv2img, read_PILimg


# create API client with custom host, port
options = {}
options['sd_model_checkpoint'] = 'chilloutmix_NiPrunedFp16Fix.safetensors [59ffe2243a]'
api = webuiapi.WebUIApi(host='127.0.0.1', port=7890)
api.set_options(options)

"""
Remove logo on position
1. left top; 2. right top; 3. left bottom; 4. right bottom; 5. middle top; 6. middle bottom
"""
def remove_logo(img: Image, position: int, length: int=600, width: int=100) -> Image:
    img_size = img.size
    # render_size = conf.LORA_ROI_RENDERING_SETTINGS['size']  # Replace with your desired render size
    render_size = (1800, 512)

    # crop image covering logo area, of size rendering_size
    if position == 1:  # left top
        partial_img = img.crop((0, 0, render_size[0], render_size[1]))
        logo_coords = (0, 0, length, width)
    elif position == 2:  # right top
        partial_img = img.crop((img_size[0] - render_size[0], 0, img_size[0], render_size[1]))
        logo_coords = (render_size[0] - length, 0, render_size[0], width)
    elif position == 3:  # left bottom
        partial_img = img.crop((0, img_size[1] - render_size[1], render_size[0], img_size[1]))
        logo_coords = (0, render_size[1] - width, length, render_size[1])
    elif position == 4:  # right bottom
        partial_img = img.crop((img_size[0] - render_size[0], img_size[1] - render_size[1], img_size[0], img_size[1]))
        logo_coords = (render_size[0] - length, render_size[1] - width, render_size[0], render_size[1])
    elif position == 5:  # middle top
        partial_img = img.crop((img_size[0]//2 - render_size[0]//2, 0, img_size[0]//2 + render_size[0]//2, render_size[1]))
        logo_coords = (render_size[0]//2 - length//2, 0, render_size[0]//2 + length//2, width)
    elif position == 6:  # middle bottom
        partial_img = img.crop((img_size[0]//2 - render_size[0]//2, img_size[1] - render_size[1], img_size[0]//2 + render_size[0]//2, img_size[1]))
        logo_coords = (render_size[0]//2 - length//2, render_size[1] - width, render_size[0]//2 + length//2, render_size[1])
    else:
        raise Exception('Invalid position')

    # create mask of size rendering_size, background(0,0,0), with logo area color (255,255,255)
    logo_mask = Image.new("RGB", render_size, (0, 0, 0))
    logo_rect = Image.new("RGB", (logo_coords[2] - logo_coords[0], logo_coords[3] - logo_coords[1]), (255, 255, 255))
    logo_mask.paste(logo_rect, (logo_coords[0], logo_coords[1]))

    # inpaint the cropped image
    inpaint_partial_img = api.img2img(
        prompt='', 
        images=[partial_img],
        mask_image=logo_mask,
        width=render_size[0],
        height=render_size[1],
        mask_blur=50,
        inpaint_full_res=0,
        inpainting_fill=1,
        inpaint_full_res_padding=20,
        denoising_strength=0.7,
        sampler_name="DPM++ SDE Karras"
    ).images[0]

    # paste inpainted image back to original image
    if position == 1:  # left top
        img.paste(inpaint_partial_img, (0, 0))
    elif position == 2:  # right top
        img.paste(inpaint_partial_img, (img_size[0] - render_size[0], 0))
    elif position == 3:  # left bottom
        img.paste(inpaint_partial_img, (0, img_size[1] - render_size[1]))
    elif position == 4:  # right bottom
        img.paste(inpaint_partial_img, (img_size[0] - render_size[0], img_size[1] - render_size[1]))
    elif position == 5:  # middle top
        img.paste(inpaint_partial_img, (img_size[0]//2 - render_size[0]//2, 0))
    elif position == 6:  # middle bottom
        img.paste(inpaint_partial_img, (img_size[0]//2 - render_size[0]//2, img_size[1] - render_size[1]))

    return img


if __name__ == "__main__":
    from backend.extensions import app, db
    app.app_context().push()
    scene = models.Scene.query.get(2885)
    img = read_PILimg(ResourceMgr.get_resource_oss_url(ResourceType.BASE_IMG, scene.scene_id))
    img_rst = remove_logo(img, 3, length=200, width=350)
    img_rst.save('test_remove_logo.png')