import os
from PIL import Image
from backend import models
from backend.extensions import db, app
from core.resource_manager import *


app.app_context().push()

file_path = '/home/chong/downloads/2d-scenes/watercolor-head'

collection_name = 'DS_watercolor_head_0501'
prompt = '(watercolor:1.2), a girl, extremely luminous bright design, glowing, sparkling, lens flare,'
params = {
    "model": "dreamshaper_4BakedVaeFp16", 
    "sampler_name": "Euler a"
}
negative_prompt = '(deformed iris, deformed pupils, semi-realistic, cgi, 3d, render, sketch, cartoon, drawing, anime:1.4), text, close up, cropped, out of frame, worst quality, low quality, jpeg artifacts, ugly, duplicate, morbid, mutilated, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, blurry, dehydrated, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck'

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