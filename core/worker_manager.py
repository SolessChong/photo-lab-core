import sys
import time
import logging
import json
from backend import extensions, models
from backend.extensions import app, db, a_c_c
from sqlalchemy.orm import sessionmaker
import sys
import argparse
import multiprocessing as mp
from core.utils import rabbit_head_animation

from core import worker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create a logger
logger = logging.getLogger(__name__)

# train status:             null -> wait -> processing -> finish ( -> fail )
# task render status:       null -> wait -> processing -> finish ( -> fail )
# scene setup status:       null -> wait -> processing -> finish ( -> fail )
# 
# Lifecycle:
#   - null -> wait:         user interaction. from FE.
#   - wait -> processing:   worker_manager. keep running.
#   - processing -> finish: task specific handlers.

def train(Session):
    session = Session()
    session.begin()

    person = None
    person_id = None
    try:
        person = session.query(models.Person).filter(models.Person.lora_train_status == 'wait').with_for_update().first()
        if person:
            person.lora_train_status = 'processing'
            person_id = person.id
        session.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

    if person_id:
        logger.info(f"======= Task: training LORA model: person_id={person_id}")
        sources = models.Source.query.filter(models.Source.person_id == person_id, models.Source.base_img_key != None).all()
        worker.task_train_lora(person_id, [source.base_img_key for source in sources], epoch=10)

def render(Session):
    session = Session()
    session.begin()

    # TODO: page size 
    todo_task_id_list = []
    try:
        tasks = session.query(models.Task).filter(models.Task.status == 'wait').with_for_update().limit(20).all()
        if len(tasks) > 0:
            logger.info(f"======= Task: render task: waiting tasks number: {len(tasks)}, tasks: {tasks}")
        for task in tasks:
            flag = True
            for person_id in task.person_id_list:
                person = session.query(models.Person).filter(models.Person.id == person_id).first()
                logger.info(f"    ---- Task: render task: person_id={person_id}, person={person}, person.lora_train_status={person.lora_train_status}")
                if person.lora_train_status != 'finish':
                    flag = False
                    logger.info(f"    ---- 🙅‍♀️ Task: Not Ready: person_id={person_id}, person={person}, person.lora_train_status={person.lora_train_status}")
                    task.status = 'fail'
                    break
            scene = models.Scene.query.get(task.scene_id)
            if scene and scene.setup_status != 'finish':
                flag = False
                logger.info(f"    ---- 🙅‍♀️ Task: Not Ready: scene_id={task.scene_id}, scene={scene}, scene.setup_status={scene.setup_status}")
                task.status = 'fail'
            # Ready to render
            if flag:
                todo_task_id_list.append(task.id)
                task.status = 'processing'
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.commit()
        session.close()

    for id in todo_task_id_list:
        logger.info(f"     ------ Task: render task: task_id={id}")
        try:
            worker.task_render_scene(id)
        except Exception as e:
            print(f"Error: {e}")
            session = Session()
            session.begin()
            task = models.Task.query.get(id)
            task.status = 'fail'
            a_c_c(task, db)
            

def setup_scene(Session):
    session = Session()
    session.begin()

    scene_id_list = []
    try:
        scenes = session.query(models.Scene).filter(models.Scene.setup_status == 'wait', models.Scene.action_type == "sd").with_for_update().limit(30).all()
        if len(scenes) > 0:
            logger.info(f"======= Task: setup scene: waiting scenes number: {len(scenes)}, scenes: {scenes}")
        for scene in scenes:
            scene_id_list.append(scene.scene_id)
            scene.setup_status = 'processing'
        session.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

    for id in scene_id_list:
        try:
            worker.task_set_up_scene(id)
        except Exception as e:
            print(f"Error: {e}")
            scene = models.Scene.query.get(id)
            scene.setup_status = 'fail'
            a_c_c(scene, db)

def process(cmd):
    app.app_context().push()
    Session = sessionmaker(bind=extensions.engine)

    if cmd == 'train':
        logger.info(f"======= Worker Manager: Start TRAINING workers ========")
        while True:
            train(Session)
            rabbit_head_animation(10)
    elif cmd == 'render':
        logger.info(f"======= Worker Manager: Start RENDERING workers ========")
        while True:
            render(Session)
            rabbit_head_animation(10)
    elif cmd == 'set_up':
        logger.info(f"======= Worker Manager: Start SCENE SETUP workers ========")
        while True:
            setup_scene(Session)
            rabbit_head_animation(10)
    elif cmd == 'all':
        logger.info(f"======= Worker Manager: Start ALL workers ========")
        while True:
            train(Session)
            render(Session)
            setup_scene(Session)
            rabbit_head_animation(10)
    else:
        print("Usage: python script_name.py <arg>")
        sys.exit(1)

# main script
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('cmd', type=str, help='Jobs to run. Available jobs: train, render, set_up, all')
    parser.add_argument('-p', type=int, default=1, help='Process number')
    args = parser.parse_args()

    process(args.cmd)

