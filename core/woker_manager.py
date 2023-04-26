import sys
import time
import logging
import json
from backend import app, extensions, models
from sqlalchemy.orm import sessionmaker

from core import worker

# train status:             null -> wait -> processing -> finish
# task render status:       null -> wait -> processing -> finish
# scene setup status:       null -> wait -> processing -> finish 
# 
# Lifecycle:
#   - null -> wait:         user interaction. from FE.
#   - wait -> processing:   worker_manager. keep running.
#   - processing -> finish: task specific handlers.

def train(Session):
    session = Session()
    session.begin()

    person = None
    try:
        person = session.query(models.Person).filter(models.Person.lora_train_status == 'wait').with_for_update().first()
        if person:
            person.lora_train_status = 'processing'
        session.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

    if person:
        logging.info(f"======= Task: training LORA model: person_id={person.id}")
        sources = models.Source.query.filter(models.Source.person_id == person.id, models.Source.base_img_key != None).all()
        worker.task_train_lora(person.id, [source.base_img_key for source in sources])

def render(Session):
    session = Session()
    session.begin()

    todo_task_id_list = []
    try:
        tasks = session.query(models.Task).filter(models.Task.status == 'wait').with_for_update().limit(20).all()
        for task in tasks:
            flag = True
            for person_id in json.loads(task.person_id_list):
                person = session.query(models.Person).filter(models.Person.id == person_id).first()
                if person.lora_train_status != 'finish':
                    flag = False
                    break
            if flag:
                todo_task_id_list.append(task.id)
                task.status = 'processing'
        session.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

    for id in todo_task_id_list:
        logging.info(f"======= Task: render task: task_id={id}")
        worker.task_render_scene(id)

def setup_scene(Session):
    session = Session()
    session.begin()

    scene_id_list = []
    try:
        scenes = session.query(models.Scene).filter(models.Scene.hint_status == None).with_for_update().limit(30).all()
        for scene in scenes:
            scene_id_list.append(scene.id)
            scene.hint_status = 'processing'
        session.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

    for id in scene_id_list:
        worker.set_up_scene(id)

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
            train(Session)
            time.sleep(10)
    elif argument == 'render':
        while True:
            render(Session)
            time.sleep(10)
    elif argument == 'hint':
        while True:
            setup_scene(Session)
            time.sleep(10)
    elif argument == 'all':
        while True:
            train(Session)
            render(Session)
            setup_scene(Session)
            time.sleep(10)
    else:
        print("Usage: python script_name.py <arg>")
        sys.exit(1)
