######################
# data structure
# 
# 1. Scene
######################
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
import os
import time
from core import conf
from core import train_lora
from core import set_up_scene
from core import render
from core.resource_manager import ResourceMgr, ResourceType, bucket, str2oss, oss2buf, write_PILimg
from pathlib import Path
from backend import models
from core import templates
import shutil
import json
import logging
from backend.extensions import app, db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Train LORA model
# test case, 
# person_id=0
# train_img_list = ['source/meizi/0/d95b7c8648e55e04ab015bf4b7628462.png', 'source/meizi/0/552b77aaad3d2e878d610163de058729.png']
def task_train_lora(person_id, train_img_list, epoch=5):
    logging.info(f"======= Task: training LORA model {person_id}")
    # save to local
    dataset_path = Path(ResourceMgr.get_resource_local_path(ResourceType.TRAIN_DATASET, person_id))
    img_train_path = dataset_path / "img_train"
    img_raw_path = dataset_path / "img_raw"
    for path in [img_train_path, img_raw_path]:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
    # enumerate train_img_list with index
    for i, img_url in enumerate(train_img_list):
        # download img using oss2
        bucket.get_object_to_file(img_url, str(img_raw_path / f"{i}.png"))
        
    # read img list from img_path
    train_lora.detect_subject_and_crop(dataset_path, remove_bg=conf.TRAIN_PARAMS['REMOVE_BACKGROUND'], enlarge=conf.TRAIN_PARAMS['ENLARGE_FACE'])

    ## 2. Captioning
    #
    logging.info("  === start captioning")
    train_lora.captioning(img_train_path,  remove_bg=conf.TRAIN_PARAMS['REMOVE_BACKGROUND'])

    ## 3. Train LORA model
    #
    logging.info(f"  === start training LORA model {person_id}")
    train_lora.train_lora(dataset_path, person_id, 'girl', epoch=epoch)

    # TODO: save to db @fengyi. Re: 爸爸替你写了
    person = models.Person.query.get(person_id)
    # model file local path: ResourceMgr.get_resource_path(ResourceType.LORA_MODEL, person_id)
    model_path = ResourceMgr.get_resource_local_path(ResourceType.LORA_MODEL, person_id)

    db.session.close()
    if not os.path.exists(model_path):
        logging.error(f"  --- LORA model {person_id} not found")
        return -1
    else:
        url = ResourceMgr.get_resource_oss_url(ResourceType.LORA_MODEL, person_id)
        bucket.put_object_from_file(url, model_path)
        person.lora_train_status = "success"
        person.update_model_file(url)
        logging.info(f"  --- LORA model {person_id} Success")
        return 0

# test case,
# scene_id = 557
# persion_id_list = [0]
def task_render_scene(task_id):
    # scene_base_img, lora_file_list, hint_img_list, ROI_list[mask_img_list, bbox], prompt, negative_prompt, debug_list[1..10]
    task = models.Task.query.get(task_id)
    scene = models.Scene.query.get(task.scene_id)
    # person_list = models.Person.query.filter(models.Person.id.in_(person_id_list)).all()
    person_id_list = task.get_person_id_list()
    person_list = [models.Person.query.get(person_id) for person_id in person_id_list]

    logging.info(f"======= Task: rendering scene: task_id={task_id}, scene_id={task.scene_id}, person_id_list={person_id_list}")
    # Download person lora
    logging.info(f"  === Prepare local person lora")
    for person in person_list:
        # if not exists, download
        lora_file_path = ResourceMgr.get_resource_local_path(ResourceType.LORA_MODEL, person.id)
        # check lora file exists
        if os.path.exists(lora_file_path):
            # Has lora file but no complete flag: some other process is downloading
            # TODO: if the process is dead, or HTTP timeout, the worker process will hang forever causing task congestion.
            if not os.path.exists(lora_file_path + '.0'):
                time.sleep(10)
        # No lora file, download
        else:
            logging.info(f"  --- Downloading person lora {person.id}")
            bucket.get_object_to_file(person.model_file_key, lora_file_path)
            Path(lora_file_path + '.0').touch()
    logging.info(f"  --- Local person lora finished")

    try:
        rst_img = render.render_lora_on_base_img(task)
        # compose rst_img_key
        rst_img_key = ResourceMgr.get_resource_oss_url(ResourceType.RESULT_IMG, task.id)
        task.update_result_img_key(rst_img_key)
        write_PILimg(rst_img, task.result_img_key)
        logging.info(f"--- Render scene success.  save to oss: {task.result_img_key}")
    except Exception as e:
        logging.exception(f"  --- ❌ Render scene failed. {e}")
        task.task_fail()

    db.session.close()
    return 0

def task_set_up_scene(scene_id):
    logging.info(f"======= Task: set up scene: scene_id={scene_id}")
    set_up_scene.prepare_scene(scene_id)
    scene = models.Scene.query.get(scene_id)
    scene.update_setup_status('finish')
    logging.info(f"--- Set up scene success. scene_id={scene_id}")
    db.session.close()
    return 0