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
import sys
import shutil
from core import conf
from core import train_lora
from core import set_up_scene
from core import render
from core import worker
from core.resource_manager import ResourceMgr, ResourceType, bucket, str2oss, oss2buf, write_PILimg
from pathlib import Path
from backend import models
from core import templates
import json
import logging
from backend.extensions import app, migrate, db
from backend.config import CELERY_CONFIG

import secrets
from celery import Celery
from flask import Flask


def make_celery(app):
    celery = Celery('pipeline.core.celery_worker', broker=app.config['CELERY_BROKER_URL'], backend=app.config['CELERY_RESULT_BACKEND'])

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

app.config.update(
    **CELERY_CONFIG
)
celery = make_celery(app)

# Train LORA model

# test case, 
# person_id=0
# train_img_list = ['source/meizi/0/d95b7c8648e55e04ab015bf4b7628462.png', 'source/meizi/0/552b77aaad3d2e878d610163de058729.png']
task_train_lora = celery.task(name="train_lora", queue="train_queue")(worker.task_train_lora)

# test case,
# scene_id = 557
# persion_id_list = [0]
task_render_scene = celery.task(name="render_scene", queue="render_queue")(worker.task_render_scene)

# Set up scene
task_set_up_scene = celery.task(name="set_up_scene", queue="render_queue")(worker.task_set_up_scene)

# main script
if __name__ == '__main__':
    # celery.send_task('pipeline.core.celery_worker.task_train_lora', args=[0, ['source/meizi/0/d95b7c8648e55e04ab015bf4b7628462.png', 'source/meizi/0/552b77aaad3d2e878d610163de058729.png']])
    celery.send_task('pipeline.core.celery_worker.print_hello')
    # celery.send_task('pipeline.core.celery_worker.task_render_scene', args=[0, 557, [0]])
    # task_render_scene.delay(0, 557, [0])
    
    # task_train_lora(0, ['source/meizi/0/d95b7c8648e55e04ab015bf4b7628462.png', 'source/meizi/0/552b77aaad3d2e878d610163de058729.png'])