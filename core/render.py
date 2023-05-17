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
import argparse
from backend import models
from core.libs.openpose.util import draw_bodypose
from core.resource_manager import ResourceMgr, ResourceType, oss2buf, str2oss, read_cv2img, read_PILimg, write_cv2img, write_PILimg

# create API client with custom host, port

api = None
def get_api_instance(port=7890):
    global api
    if api is None:
        api = webuiapi.WebUIApi(host='127.0.0.1', port=port)
    return api

body_estimate = Body()

# Logging to stdout
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# prepare task, download base_img, generate pose, download lora.
def prepare_task(task):
    # download base_img
    base_img_url = ResourceMgr.get_resource_oss_url(ResourceType.BASE_IMG, task.scene_id)
    pose_img_url = ResourceMgr.get_resource_oss_url(ResourceType.POSE_IMG, task.scene_id)
    base_img = read_PILimg(base_img_url)
    pose_map = read_PILimg(pose_img_url)

    return base_img, pose_map

def generate_prompt_with_lora(prompt, lora, params=None):
    if not prompt:
        prompt = ''
    char_attention = params.get('char_attention', templates.PROMPT_PARAMS['CHAR_ATTENTION'])
    prompt_with_lora = prompt + f",<lora:{lora}:1>, (a close-up photo of a {conf.SUBJECT_PLACEHOLDER} person:{char_attention})"
    logging.info(f"prompt_with_lora: {prompt_with_lora}")
    # replace person with subject name using regex
    pattern = r'\b(?:a woman|a man|a girl|a boy)\b'
    prompt_with_lora = re.sub(pattern, f"photo of a {conf.SUBJECT_PLACEHOLDER}, {templates.PROMPT_PHOTO}", prompt_with_lora)
    return prompt_with_lora

"""
Render LORA on Task with prompt, using t2i method.
Typically for comic style.
- task: task dict
    - task_id
    - scene_id
    - lora_list: list of lora name, e.g. user_1, user_2. <list>
    - prompt: override default prompt. <str>
    - params: overwrite default params, task specific params. <dict>
"""
def render_lora_on_prompt(task) -> Image:
    scene = models.Scene.query.get(task.scene_id)
    assert scene.prompt is not None, "  -- ❌ Prompt is required for t2i method."
    logging.info(f"Running task {task.id}, scene: {task.scene_id}, lora: {task.person_id_list}")

    lora_list = [ResourceMgr.get_lora_name_by_person_id(person_id) for person_id in task.person_id_list]
    assert len(lora_list) == 1, "  -- ❌ Multi-person scene not implemented."
    t2i_args = templates.LORA_T2I_PARAMS
    if scene.params:
        t2i_args.update(scene.params)
    
    prompt_with_lora = generate_prompt_with_lora(scene.prompt, lora_list[0])
    logging.info(f"prompt_with_lora: {prompt_with_lora}, t2i_args: {t2i_args}")

    interpret_params(t2i_args)
    rst = get_api_instance().txt2img(
        prompt=prompt_with_lora,
        **t2i_args
    ).images[0]

    return rst


"""
Render lora on Task with base_img, using i2i method.
- task: task dict
    - task_id
    - scene_id
    - lora_list: list of lora name, e.g. user_1, user_2. <list>
    - prompt: override default prompt. <str>
    - params: overwrite default params, task specific params. <dict>
- return: rendered image, <PIL Image>
"""
def render_lora_on_base_img(task) -> Image:
    logging.info(f"Running task {task.id}, scene: {task.scene_id}, lora: {task.person_id_list}")
    scene = models.Scene.query.get(task.scene_id)
    base_img, pose_img = prepare_task(task)

    # e.g. lora_list[0] = 'user_1', --> <lora:user_1:1> in prompt.
    lora_list = [ResourceMgr.get_lora_name_by_person_id(person_id) for person_id in task.person_id_list]
    prompt = scene.prompt

    # Extract config
    lora_upscaler_params = scene.params.get("lora_upscaler_params", templates.UPSCALER_DEFAULT)
    i2i_params = templates.LORA_INPAINT_PARAMS
    if scene.params and scene.params.get("i2i_params"):
        i2i_params.update(scene.params.get("i2i_params"))

    options = {'sd_model_checkpoint': scene.params.get('model')}
    get_api_instance().set_options(options)
    logging.info(f"    ---- 🔄 Switching to model: {options['sd_model_checkpoint']}")

    scene_id = task.scene_id
    image = base_img.copy()

    for i, person_id in enumerate(task.person_id_list):
        # Get the bounding box for the current person from the Scene model
        bb = scene.roi_list[i]

        prompt_with_lora = generate_prompt_with_lora(prompt, lora_list[i], scene.params)
        
        char_base_img = image.crop((bb[0], bb[1], bb[0] + bb[2], bb[1] + bb[3]))
        char_pose_img = pose_img.copy().crop((bb[0], bb[1], bb[0] + bb[2], bb[1] + bb[3]))

        # detect face and draw mask on cropped image
        char_base_cv_img = cv2.cvtColor(np.array(char_base_img), cv2.COLOR_RGB2BGR)
        mask_list = face_mask.get_face_mask(char_base_cv_img, expand_face=1.5)
        if len(mask_list) != 1:
            raise Exception("Face mask count mismatch!")
        char_mask_img = mask_list[0]

        # Resize PIL.Image char_base_img, char_pose_img, char_mask_img to 512x512
        render_size = (512, 512)
        char_base_img = char_base_img.resize(render_size, resample=Image.LANCZOS) 
        char_pose_img = char_pose_img.resize(render_size, resample=Image.LANCZOS)
        char_mask_img = char_mask_img.resize(render_size, resample=Image.NEAREST)  # to ensure binary

        ### Save tmp image for debug
        if conf.DEBUG:
            # create path if not exist
            output_dir = os.path.dirname(ResourceMgr.get_resource_local_path(ResourceType.TMP_OUTPUT, scene_id))
            char_base_img.save(ResourceMgr.get_resource_local_path(ResourceType.TMP_OUTPUT, f"{scene_id}_char_base_img_{i}"))
            char_pose_img.save(ResourceMgr.get_resource_local_path(ResourceType.TMP_OUTPUT, f"{scene_id}_char_pose_img_{i}"))
            char_mask_img.save(ResourceMgr.get_resource_local_path(ResourceType.TMP_OUTPUT, f"{scene_id}_char_mask_img_{i}"))
            # linearly blend between pose and base image
            blended_img = Image.blend(char_base_img, char_pose_img, 0.5)
            blended_img.save(ResourceMgr.get_resource_local_path(ResourceType.TMP_OUTPUT, f"{scene_id}_blended_img_{i}"))

        char_controlnet_units = [webuiapi.ControlNetUnit(input_image=char_pose_img, model="control_sd15_openpose [fef5e48e]", resize_mode="Inner Fit (Scale to Fit)", guidance=0.9, guidance_end=0.7)]
        # log params
        logging.info(f"prompt_with_lora: {prompt_with_lora}, i2i_args: {i2i_params}")

        char_lora_img = get_api_instance().img2img(
            prompt=prompt_with_lora, 
            images=[char_base_img],
            controlnet_units=char_controlnet_units,
            mask_image=char_mask_img,
            mask_blur=10,
            **i2i_params
            ).images[0]

        # resize to original size and paste to final image
        char_lora_img = char_lora_img.convert("RGBA")
        if bb[2] < char_lora_img.width:
            char_lora_img_enlarge = char_lora_img.resize((bb[2], bb[3]))      
        else:
            char_lora_img_enlarge = get_api_instance().extra_single_image(
                char_lora_img,
                resize_mode=1,
                upscaling_resize_w=bb[2],
                upscaling_resize_h=bb[3],
                **lora_upscaler_params,
            ).images[0]
        image.paste(char_lora_img_enlarge, (bb[0], bb[1]))
        
        # char_lora_img = char_lora_img.convert("RGBA")
        # char_lora_img = char_lora_img.resize((bb[2], bb[3]))        
        # image.paste(char_lora_img, (bb[0], bb[1]))
        

        ### Save tmp image for debug
        if conf.DEBUG:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            char_lora_img.save(ResourceMgr.get_resource_local_path(ResourceType.TMP_OUTPUT, f"{scene_id}_lora_{i}.png"))
            image.save(ResourceMgr.get_resource_local_path(ResourceType.TMP_OUTPUT, f"{scene_id}_result_{i}.png"))

    # Log success
    logging.info(f"    ----  ✅ Task {task.id}, Scene {scene_id} finished successfully.")
    return image


# main program
if __name__ == "__main__":
    # Argument 'task'
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", help="task id")
    # Argument 'person', list of int
    parser.add_argument("--person", nargs='+', type=int, help="person id list")
    # Argument 'scene'
    parser.add_argument("--scene", help="scene id")

    args = parser.parse_args()
    task_id = args.task
    person_id_list = args.person
    scene_id = args.scene
    # Should have task, or (person and scene)
    assert task_id or (person_id_list and scene_id), "  -- ❌ Task id or (person id and scene id) is required."

    if task_id:
        task = models.Task.query.get(task_id)
        img = render_lora_on_base_img(task)
        write_PILimg(img, ResourceMgr.get_resource_oss_url(ResourceType.RESULT_IMG, task.id))
        db.session.add(task)
        db.session.commit()
    elif person_id_list and scene_id:
        from backend.extensions import db, app
        app.app_context().push()
        task = models.Task(scene_id=scene_id, person_id_list=person_id_list)
        db.session.add(task)
        img = render_lora_on_base_img(task)
        task.result_img_key = ResourceMgr.get_resource_oss_url(ResourceType.RESULT_IMG, task.id)
        write_PILimg(img, task.result_img_key)
        db.session.commit()


    # prompt = """
    # (8k, best quality, masterpiece:1.2), (realistic, photo-realistic:1.5),a girl, , dating,(smile:1.15),  small breasts, beautiful detailed eyes, ,full body, , ,
    # """

    # for i in range(10, 16):
    #     for fn in os.listdir(f"pipeline/data/base_img/{i}/"):
    #         if fn.endswith(".png"):
    #             try:
    #                 # filename without extension
    #                 fn = os.path.splitext(fn)[0]
    #                 task = {
    #                     'task_id': '0000001',
    #                     'scene_id': f'{i}/{fn}',
    #                     'lora_list': ['zheng-girl-r-2-000009'],
    #                     'prompt': prompt,
    #                     'params':{
    #                         "negative_prompt": "EasyNegative, paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, glans,extra fingers,fewer fingers,strange fingers,bad hand",
    #                         "inpainting_fill": 1,
    #                         "inpaint_full_res": False,
    #                         "seed": -1,
    #                         "sampler_name": "DPM++ SDE Karras",
    #                         "restore_faces": True,
    #                         "width": conf.LORA_ROI_RENDERING_SETTINGS['size'][0],
    #                         "height": conf.LORA_ROI_RENDERING_SETTINGS['size'][1],
    #                         "cfg_scale": 7,
    #                         "steps": 40,
    #                         "denoising_strength": 0.4
    #                     }
    #                 }
                    
    #                 render_lora_on_base_img(task)
    #             except Exception as e:
    #                 logging.error(f" ❌ ERROR: {fn}, {e}")
    #                 continue