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
import webuiapi
import numpy as np
import typing
import argparse
from backend import models
from backend.extensions import db, app
from core.resource_manager import ResourceMgr, ResourceType, oss2buf, str2oss, read_cv2img, read_PILimg, write_PILimg, bucket


# create API client with custom host, port
options = {}
options['sd_model_checkpoint'] = 'chilloutmix_NiPrunedFp16Fix.safetensors [59ffe2243a]'
api = webuiapi.WebUIApi(host='127.0.0.1', port=7890)
api.set_options(options)

"""
Remove logo on position
1. left top; 2. right top; 3. left bottom; 4. right bottom; 5. middle top; 6. middle bottom
"""
def remove_logo_from_image(img: Image, location: int, length: int=600, width: int=100) -> Image:
    img_size = img.size
    # render_size = conf.LORA_ROI_RENDERING_SETTINGS['size']  # Replace with your desired render size
    render_size = (1800, 512)

    # crop image covering logo area, of size rendering_size
    if location == 1:  # left top
        partial_img = img.crop((0, 0, render_size[0], render_size[1]))
        logo_coords = (0, 0, length, width)
    elif location == 2:  # right top
        partial_img = img.crop((img_size[0] - render_size[0], 0, img_size[0], render_size[1]))
        logo_coords = (render_size[0] - length, 0, render_size[0], width)
    elif location == 3:  # left bottom
        partial_img = img.crop((0, img_size[1] - render_size[1], render_size[0], img_size[1]))
        logo_coords = (0, render_size[1] - width, length, render_size[1])
    elif location == 4:  # right bottom
        partial_img = img.crop((img_size[0] - render_size[0], img_size[1] - render_size[1], img_size[0], img_size[1]))
        logo_coords = (render_size[0] - length, render_size[1] - width, render_size[0], render_size[1])
    elif location == 5:  # middle top
        partial_img = img.crop((img_size[0]//2 - render_size[0]//2, 0, img_size[0]//2 + render_size[0]//2, render_size[1]))
        logo_coords = (render_size[0]//2 - length//2, 0, render_size[0]//2 + length//2, width)
    elif location == 6:  # middle bottom
        partial_img = img.crop((img_size[0]//2 - render_size[0]//2, img_size[1] - render_size[1], img_size[0]//2 + render_size[0]//2, img_size[1]))
        logo_coords = (render_size[0]//2 - length//2, render_size[1] - width, render_size[0]//2 + length//2, render_size[1])
    else:
        raise Exception('Invalid location')

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
        mask_blur=20,
        inpaint_full_res=0,
        inpainting_fill=0,
        inpaint_full_res_padding=20,
        denoising_strength=0.7,
        sampler_name="DPM++ SDE Karras"
    ).images[0]

    # paste inpainted image back to original image
    if location == 1:  # left top
        img.paste(inpaint_partial_img, (0, 0))
    elif location == 2:  # right top
        img.paste(inpaint_partial_img, (img_size[0] - render_size[0], 0))
    elif location == 3:  # left bottom
        img.paste(inpaint_partial_img, (0, img_size[1] - render_size[1]))
    elif location == 4:  # right bottom
        img.paste(inpaint_partial_img, (img_size[0] - render_size[0], img_size[1] - render_size[1]))
    elif location == 5:  # middle top
        img.paste(inpaint_partial_img, (img_size[0]//2 - render_size[0]//2, 0))
    elif location == 6:  # middle bottom
        img.paste(inpaint_partial_img, (img_size[0]//2 - render_size[0]//2, img_size[1] - render_size[1]))

    return img

def remove_scene_logo(scene_id, location, length=None, width=None):
    app.app_context().push()
    oss_url = ResourceMgr.get_resource_oss_url(ResourceType.BASE_IMG, scene_id)
    # add _bck to the end of the url before file extension, split by .
    backup_oss_url = '.'.join(oss_url.split('.')[:-1]) + '_bck.' + oss_url.split('.')[-1]
    # copy file to backup url
    if not bucket.object_exists(backup_oss_url):
        bucket.copy_object(bucket.bucket_name, oss_url, backup_oss_url)

    img = read_PILimg(backup_oss_url)
    img_rst = remove_logo_from_image(img, location, length=length, width=width)
    img_rst.save('test_remove_logo.png')
    write_PILimg(img_rst, oss_url)
    db.session.close()


if __name__ == "__main__":
    from backend.extensions import app, db
    
    # take scene from argparser
    argparser = argparse.ArgumentParser()
    # read scenes, list of int
    argparser.add_argument("--scene", type=int, nargs='+', required=True, help="scene id")
    argparser.add_argument("--location", type=int, required=True, help="logo location, range from 1 to 6, 1: left top; 2: right top; 3: left bottom; 4: right bottom; 5: middle top; 6: middle bottom")
    # read length and width from argparser
    argparser.add_argument("--length", type=int, help="logo length", default=600)
    argparser.add_argument("--width", type=int, help="logo width", default=100)

    args = argparser.parse_args()
    scene = args.scene
    location = args.location

    print(f"scene_id: {scene}, location: {location}, length: {args.length}, width: {args.width}")
    for scene_id in scene:
        remove_scene_logo(scene_id, location, length=args.length, width=args.width)

    db.session.close()