######################
# data structure
######################
# 
# 1. Scene
#  - id
#  - name
#  - base_img_key
#  - hint_img_list
#     - id
#     - hint_img_key
#  - ROI_list
#     - id
#     - type: [man_head, woman_head, pet]
#     - bbox (x, y, w, h)
#     - mask_img_key
#  - model_name
#  - promp
#  - negative_prompt
#  - params
#
# 2. Person
#  - id
#  - name
#  - model_type # lora for now.
#  - model_file_key
#  - sex
#
# 3. Task
#  - id
#  - person_id
#  - scene_id
#  - status
#  - result_img_key
#  - debug_img[1..10]
#


import conf
import train_lora
import render
from resource_manager import ResourceMgr, ResourceType, bucket
from pathlib import Path
from backend import models
import templates
import json
import logging


# Train LORA model

def task_train_lora(person_id, train_img_list):
    # save to local
    dataset_path = Path(ResourceMgr.get_resource_path(ResourceType.TRAIN_DATASET, person_id))
    img_train_path = dataset_path / "img_train"
    img_raw_path = dataset_path / "img_raw"
    for path in [img_train_path, img_raw_path]:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
    # enumerate train_img_list with index
    for i, img_url in enumerate(train_img_list):
        # download img using oss2
        bucket.get_object_to_file(img_url, str(img_raw_path / f"{i}.png"))
        
    # read img list from img_path
    train_lora.detect_subject_and_crop(dataset_path, remove_bg=conf.TRAIN_PARAMS['REMOVE_BACKGROUND'], enlarge=conf.TRAIN_PARAMS['ENLARGE_FACE'])

    ## 2. Captioning
    #
    logging.info("=== start captioning")
    train_lora.captioning(img_train_path,  remove_bg=conf.TRAIN_PARAMS['REMOVE_BACKGROUND'])

    ## 3. Train LORA model
    #
    logging.info(f"=== start training LORA model {person_id}")
    train_lora(dataset_path, person_id, 'girl')

    # TODO: save to db @fengyi
    # model file local path: ResourceMgr.get_resource_path(ResourceType.LORA_MODEL, person_id)


def task_render_scene(task_id):
    # scene_base_img, lora_file_list, hint_img_list, ROI_list[mask_img_list, bbox], prompt, negative_prompt, debug_list[1..10]
    task = models.Task.query.get(task_id)
    scene = models.Scene.query.get(task.scene_id)
    person = models.Person.query.get(task.person_id)
    # Download person lora
    lora_file_path = ResourceMgr.get_resource_path(ResourceType.LORA_MODEL, person.id)
    bucket.get_object_to_file(person.model_file_key, lora_file_path)

    lora_inpaint_params = templates.LORA_INPAINT_PARAMS
    if scene.params:
        lora_inpaint_params.update(json.loads(scene.params))
    task_dict = {
        'task_id': task.id,
        'scene_id': task.scene_id,
        'lora_list': [str(person.id)],
        'prompt': scene.prompt,
        'params': lora_inpaint_params
    }
    render.run_lora_on_base_img(task_dict)

# main script
if __name__ == '__main__':
    task_train_lora(0, ['source/meizi/0/d95b7c8648e55e04ab015bf4b7628462.png', 'source/meizi/0/552b77aaad3d2e878d610163de058729.png'])
    task_render_scene('1')