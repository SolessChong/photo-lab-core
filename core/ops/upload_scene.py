import os
import logging
from PIL import Image
from backend import models
from backend.extensions import db, app
from core.resource_manager import *


app.app_context().push()

file_path = '/home/chong/downloads/chong_2d_girl_cyberpunk_0511'

collection_name = 'chong_2d_girl_cyberpunk_0511'
prompt = """
a girl, masterpiece, best quality,best quality,official art,extremely detailed CG unity 8k wallpaper, light particles,illustration, dreamy, realistic, intricate details, studio photography, cinematic light, chromatic aberration, RAW, ultra high res, high saturation, cowboy shot, (in the cyberpunk city:1.2),luminous eyes,shiny hair,red china dress,Two side up,Beige hair, white hair,
"""

params = {
    "model": "dreamshaper_4BakedVaeFp16", 
    "i2i_params": {
        "sampler_name": "DPM++ 2M Karras",
        "denoising_strength": 0.7,
    },
    "lora_upscaler_params": {
        "extras_upscaler_2_visibility": 0.7,
        "upscaler_1": "ESRGAN_4x",
        "upscaler_2": "R-ESRGAN 4x+ Anime6B"
    },
}

params_photo = {
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
negative_prompt = '(nsfw),(simple background),(ugly), (duplicate), (morbid), (mutilated), [out of frame], extra fingers, mutated hands, (poorly drawn hands), (poorly drawn face), (mutation), (deformed), (ugly), blurry, (bad anatomy), (bad proportions), (extra limbs), cloned face, (disfigured). out of frame, ugly, extra limbs, (bad anatomy), gross proportions, (malformed limbs), (missing arms), (missing legs), (extra arms), (extra legs), mutated hands, (fused fingers), (too many fingers), (long neck), signature, (bad face), (ugly face)'
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
        rate=1,
    )

    db.session.add(scene)
    db.session.commit()
    db.session.close()

for fn in os.listdir(file_path):
    # for all image files
    if fn.endswith('.jpg') or fn.endswith('.png') or fn.endswith('.jpeg') or fn.endswith('.webp'):
        upload_new_scene(fn)