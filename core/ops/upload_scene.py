import os
from PIL import Image
from backend import models
from backend.extensions import db, app
from core.resource_manager import *


app.app_context().push()

file_path = '/home/chong/downloads/2d-scenes/chong_snow_white_LY_0505'

collection_name = 'chong_snow_white_LY_0505'
prompt = """(masterpiece, best quality, high resolution:1.4), portrait, snow white, a girl, woman, smile, looking at viewer, (medieval dress, yellow skirt, long skirt, red hairband),
disney style, comic, cartoon, castle, forest, pink dress, animals, lens flare, pro lighting,
"""

params = {
    "model": "lyriel_v14", 
    "i2i_params": {
        "sampler_name": "Euler a"
    },
    "lora_upscaler_params": {
        "extras_upscaler_2_visibility": 0.7,
        "upscaler_1": "ESRGAN_4x",
        "upscaler_2": "R-ESRGAN 4x+ Anime6B"
    },
}
negative_prompt = '3nsfw, EasyNegative, badhandv4, (bad anatomy, worst quality, low quality:2), watermark, signature, username, patreon, monochrome, zombie, large breasts, cleavage, logo, earrings, long hair,'

# iterate over all files in file_path
# create scene
oss_path = 'scenes/sd_collection/'

def upload_new_scene(fn):
    if fn.endswith('.png'):
        img_key = oss_path + collection_name + '/' + fn
        img = Image.open(file_path + '/' + fn)
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
    upload_new_scene(fn)