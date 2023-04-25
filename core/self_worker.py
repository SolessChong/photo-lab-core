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

import os
from core import conf
from core import train_lora
from core import set_up_scene
from core import render
from core.resource_manager import ResourceMgr, ResourceType, bucket, str2oss, oss2buf, write_PILimage
from pathlib import Path
from backend import models
from core import templates
import json
import logging
from backend.extensions import app
from backend import extensions

import secrets
from celery import Celery
from flask import Flask
from sqlalchemy.orm import sessionmaker
import time
import sys


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
        if not os.path.exists(lora_file_path):
            logging.info(f"  --- Downloading person lora {person.id}")
            bucket.get_object_to_file(person.model_file_key, lora_file_path)
    logging.info(f"  --- Local person lora finished")
    lora_inpaint_params = templates.LORA_INPAINT_PARAMS
    if scene.params:
        lora_inpaint_params.update(json.loads(scene.params))
    task_dict = {
        'task_id': task.id,
        'scene_id': task.scene_id,
        'lora_list': ['user_' + str(person.id) for person in person_list],
        'prompt': scene.prompt,
        'params': lora_inpaint_params
    }
    logging.info(f"    ----\n    task_dict: {task_dict}\n  ----")
    rst_img = render.run_lora_on_base_img(task_dict)
    # compose rst_img_key
    rst_img_key = ResourceMgr.get_resource_oss_url(ResourceType.RESULT_IMG, task.id)
    task.update_result_img_key(rst_img_key)
    
    write_PILimage(rst_img, task.result_img_key)
    logging.info(f"  --- Render scene success.  save to oss: {task.result_img_key}")
    return 0

def task_set_up_scene(scene_id):
    set_up_scene.prepare_scene(scene_id)

# main script
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <arg>")
        sys.exit(1)

    argument = sys.argv[1]  # 获取命令行参数
    app.app_context().push()
    Session = sessionmaker(bind=extensions.engine)

    if argument == 'train':
        while True:
            # 为每个事务创建一个新的 session
            session = Session()
            session.begin()
            person = None
            try:
                person = session.query(models.Person).filter(models.Person.lora_train_status == 'wait').with_for_update().first()
                if person:
                    person.lora_train_status = 'training'
                session.commit()
            except Exception as e:
                print(f"Error: {e}")
            finally:
                session.close()

            if person:
                logging.info(f"======= Task: training LORA model: person_id={person.id}")
                sources = models.Source.query.filter(models.Source.person_id == person.id, models.Source.base_img_key != None).all()
                task_train_lora(person.id, [source.base_img_key for source in sources])
            time.sleep(10)
    else:
        while True:
            # 为每个事务创建一个新的 session
            session = Session()
            session.begin()
            todo_task_id_list = []
            try:
                tasks = session.query(models.Task).filter(models.Task.status == 'wait').with_for_update().limit(20).all()
                for task in tasks:
                    flag = True
                    for person_id in task.person_id_list:
                        person = session.query(models.Person).filter(models.Person.id == person_id).first()
                        if person.lora_train_status != 'finish':
                            flag = False
                            break
                    if flag:
                        todo_task_id_list.append(task.id)
                        task.status = 'rendering'
                session.commit()
            except Exception as e:
                print(f"Error: {e}")
            finally:
                session.close()
            for id in todo_task_id_list:
                logging.info(f"======= Task: render task: task_id={id}")
                task_render_scene(id)
            time.sleep(10)
        