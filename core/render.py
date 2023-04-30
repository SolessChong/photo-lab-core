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

body_estimate = Body()

# Logging to stdout
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# prepare task, download base_img, generate pose, download lora.
def prepare_task(task):
    # download base_img
    base_img_url = ResourceMgr.get_resource_oss_url(ResourceType.BASE_IMG, task.scene_id)
    pose_img_url = ResourceMgr.get_resource_oss_url(ResourceType.POSE_IMG, task.scene_id)
    base_img = read_cv2img(base_img_url)
    pose_map = read_cv2img(pose_img_url)

    return base_img, pose_map

"""
Process model info in params, and set model for API.
Delete model field from params to make it work for API args.
"""
def process_model(params: dict) -> int:
    if not 'model' in params:
        return 0
    else:
        options['sd_model_checkpoint'] = params.pop('model')
        api.set_options(options)
        return 1

def generate_prompt_with_lora(prompt, lora):
    if not prompt:
        prompt = ''
    prompt_with_lora = prompt + f",<lora:{lora}:1>, (a close-up photo of a {conf.SUBJECT_PLACEHOLDER} person:1)"
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
    process_model(t2i_args)
    prompt_with_lora = generate_prompt_with_lora(scene.prompt, lora_list[0])
    rst = api.txt2img(
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
    # load base_img
    base_img = read_PILimg(ResourceMgr.get_resource_oss_url(ResourceType.BASE_IMG, task.scene_id))
    pose_img = read_PILimg(ResourceMgr.get_resource_oss_url(ResourceType.POSE_IMG, task.scene_id))
    # e.g. lora_list[0] = 'user_1', --> <lora:user_1:1> in prompt.
    lora_list = [ResourceMgr.get_lora_name_by_person_id(person_id) for person_id in task.person_id_list]
    prompt = scene.prompt
    i2i_args = templates.LORA_INPAINT_PARAMS
    if scene.params:
        i2i_args.update(scene.params)
    scene_id = task.scene_id

    image = base_img.copy()
    # detect face and draw mask
    mask_list = face_mask.get_face_mask(base_img, expand_face=1.5)
    if len(mask_list) != len(lora_list):
        raise Exception("Lora and Face mask count mismatch!")
    # detect human and crop img
    cv2_base_image = cv2.cvtColor(np.array(base_img), cv2.COLOR_RGB2BGR)
    [candidates, subset] = body_estimate(cv2_base_image)
    if len(subset) != len(lora_list):
        raise Exception("Lora and Human count mismatch!")
    
    for i in range(len(mask_list)):
        prompt_with_lora =  generate_prompt_with_lora(prompt, lora_list[i])
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

        char_base_img, bb = pose_detect.crop_image(cv2_base_image, upper_body_coords, enlarge=3)
        ######## save char_base_img
        if conf.DEBUG:
            char_base_path = ResourceMgr.get_resource_local_path(ResourceType.TMP_OUTPUT, f"{scene_id}_char_base_img_{i}")
            if not os.path.exists(os.path.dirname(char_base_path)):
                os.makedirs(os.path.dirname(char_base_path))
            cv2.imwrite(char_base_path, char_base_img)

        char_pose_img = pose_img.copy().crop((bb[0], bb[1], bb[0] + bb[2], bb[1] + bb[3]))
        char_mask_img = mask_list[i].copy().crop((bb[0], bb[1], bb[0] + bb[2], bb[1] + bb[3]))

        logging.debug(f"bb(x, y, width, height): {bb}")

        # Resize PIL.Image char_base_img, char_pose_img, char_mask_img to 512x512
        render_size = (512, 512)
        char_base_img = Image.fromarray(cv2.cvtColor(char_base_img, cv2.COLOR_BGR2RGB)).resize(render_size, resample=Image.LANCZOS) 
        char_pose_img = char_pose_img.resize(render_size, resample=Image.LANCZOS)
        char_mask_img = char_mask_img.resize(render_size, resample=Image.NEAREST)        # to ensure binary

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
        logging.info(f"prompt_with_lora: {prompt_with_lora}, i2i_args: {i2i_args}")

        char_lora_img = api.img2img(
            prompt=prompt_with_lora, 
            images=[char_base_img],
            controlnet_units=char_controlnet_units,
            mask_image=char_mask_img,
            mask_blur=10,
            **i2i_args
            ).images[0]

        # resize to original size and paste to final image
        char_lora_img = char_lora_img.convert("RGBA")
        char_lora_img = char_lora_img.resize((bb[2], bb[3]))        
        image.paste(char_lora_img, (bb[0], bb[1]))
        
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

    prompt = """
    (8k, best quality, masterpiece:1.2), (realistic, photo-realistic:1.5),a girl, , dating,(smile:1.15),  small breasts, beautiful detailed eyes, ,full body, , ,
    """

    for i in range(10, 16):
        for fn in os.listdir(f"pipeline/data/base_img/{i}/"):
            if fn.endswith(".png"):
                try:
                    # filename without extension
                    fn = os.path.splitext(fn)[0]
                    task = {
                        'task_id': '0000001',
                        'scene_id': f'{i}/{fn}',
                        'lora_list': ['zheng-girl-r-2-000009'],
                        'prompt': prompt,
                        'params':{
                            "negative_prompt": "EasyNegative, paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, glans,extra fingers,fewer fingers,strange fingers,bad hand",
                            "inpainting_fill": 1,
                            "inpaint_full_res": False,
                            "seed": -1,
                            "sampler_name": "DPM++ SDE Karras",
                            "restore_faces": True,
                            "width": conf.LORA_ROI_RENDERING_SETTINGS['size'][0],
                            "height": conf.LORA_ROI_RENDERING_SETTINGS['size'][1],
                            "cfg_scale": 7,
                            "steps": 40,
                            "denoising_strength": 0.4
                        }
                    }
                    
                    render_lora_on_base_img(task)
                except Exception as e:
                    logging.error(f" ❌ ERROR: {fn}, {e}")
                    continue