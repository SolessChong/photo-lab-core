import os
import logging
from PIL import Image
from backend import models
from backend.extensions import db, app
from core.resource_manager import *


app.app_context().push()

file_path = '/home/chong/downloads/zh-scene/girl2/'

collection_name = 'zh_movie_girl2_CM_0508'
prompt = """a girl, (8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1), film, cinematic lighting, 
 <lora:epi_noiseoffset2:0.8>,
"""

params_Anime = {
    "model": "chilloutmix_NiPrunedFp16Fix", 
    "i2i_params": {
        "sampler_name": "Euler a"
    },
    "lora_upscaler_params": {
        "extras_upscaler_2_visibility": 0.7,
        "upscaler_1": "ESRGAN_4x",
        "upscaler_2": "R-ESRGAN 4x+ Anime6B"
    },
}

params = {
    "model": "chilloutmix_NiPrunedFp16Fix", 
    "i2i_params": {
        "sampler_name": "DPM++ SDE Karras"
    },
    "lora_upscaler_params": {
        "extras_upscaler_2_visibility": 0.5,
        "upscaler_1": "ESRGAN_4x",
        "upscaler_2": "R-ESRGAN 4x+"
    },
}
negative_prompt = 'nsfw, EasyNegative, badhandv4, (bad anatomy, worst quality, low quality:2), watermark, signature, username, patreon, monochrome, zombie, large breasts, cleavage, logo, earrings, long hair,'

# iterate over all files in file_path
# create scene
oss_path = 'scenes/sd_collection/'

def upload_new_scene(fn):
    logging.info(f"Uploading {fn}")
    img = Image.open(file_path + '/' + fn)
    
    img_key = oss_path + collection_name + '/' + fn
    # change extension from any to .png
    img_key = img_key.split('.')[0] + '.png'

    write_PILimg(img, img_key)

    scene = models.Scene(
        base_img_key=img_key,
        prompt=prompt,
        action_type="sd",
        img_type="girl",
        negative_prompt=negative_prompt,
        params=params,
        collection_name=collection_name,
        setup_status="wait",
    )

    db.session.add(scene)
    db.session.commit()
    db.session.close()

for fn in os.listdir(file_path):
    # for all image files
    if fn.endswith('.jpg') or fn.endswith('.png') or fn.endswith('.jpeg') or fn.endswith('.webp'):
        upload_new_scene(fn)