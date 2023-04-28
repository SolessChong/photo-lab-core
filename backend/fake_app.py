import os
import oss2
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from backend.extensions import  app, db
from flask_cors import CORS
from backend.models import User, Source, Person, GeneratedImage, Pack, Scene, Task
from celery import Celery, chain, chord, group, signature
from backend.config import CELERY_CONFIG

app.app_context().push()

OSS_ACCESS_KEY_ID = 'LTAINBTpPolLKWoX'
OSS_ACCESS_KEY_SECRET = '1oQVQkxt7VlqB0fO7r7JEforkPgwOw'
OSS_BUCKET_NAME = 'photolab-test'
OSS_ENDPOINT = 'oss-cn-shenzhen.aliyuncs.com'

auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)

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
celery.conf.task_routes = {'set_up_scene': {'queue': 'render_queue'}, 'render_scene': {'queue': 'render_queue'}}


class ResourceType:
    LORA_MODEL = 1
    TRAIN_DATASET = 2

PATH_CONF = {
    'TRAIN_DATASET': 'train_dataset/'
}

def get_resource_oss_url(resource_type, id):
    match resource_type:
        case ResourceType.LORA_MODEL:
            return str('/models/lora/' + str(id) + '.safetensors')
        case ResourceType.TRAIN_DATASET:
            return str(PATH_CONF['TRAIN_DATASET'] + str(id) + '/')
        

@app.route('/')
def index():
    return render_template('fake_index.html')

@app.route('/list_scenes', methods=['GET'])
def list_scenes():
    scenes = Scene.query.filter(Scene.action_type=='sd')
    scene_list = [{'scene_id': scene.scene_id, 'base_img': f'https://photolab-test.oss-cn-shenzhen.aliyuncs.com/{scene.base_img_key}', 'prompt': scene.prompt} for scene in scenes]
    return jsonify(scene_list)

@app.route('/list_tasks', methods=['GET'])
def list_tasks():
    tasks = Task.query.all()
    task_list = [{'task_id': task.id, 'result_img_key': f'https://photolab-test.oss-cn-shenzhen.aliyuncs.com/{task.result_img_key}'} for task in tasks]
    return jsonify(task_list)

@app.route('/get_tasks', methods=['GET'])
def get_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = 100

    tasks_pagination = Task.query.filter(Task.result_img_key != None).order_by(Task.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    tasks = tasks_pagination.items
    total_pages = tasks_pagination.pages

    tasks_data = [
        {
            "id": task.id,
            "scene_id": task.scene_id,
            "result_img_key": task.result_img_key,
            "person_id_list": task.get_person_id_list()
        }
        for task in tasks
    ]

    return jsonify({"tasks": tasks_data, "total_pages": total_pages})

@app.route('/get_collections', methods=['GET'])
def get_collections():
    collections = Scene.query.with_entities(Scene.collection_name).distinct().all()
    return jsonify([collection[0] for collection in collections])

@app.route('/get_persons', methods=['GET'])
def get_persons():
    persons = Person.query.with_entities(Person.id, Person.name).all()
    return jsonify([{"id": person[0], "name": person[1]} for person in persons])

@app.route('/generate_tasks', methods=['POST'])
def generate_tasks():

    app.config.update(
        **CELERY_CONFIG
    )
    celery = make_celery(app)
    celery.conf.task_routes = {'set_up_scene': {'queue': 'render_queue'}, 'render_scene': {'queue': 'render_queue'}}


    data = request.get_json()
    collection_name = data['collection_name']
    person_id = data['person_id']
    person_id_list = f'[{person_id}]'

    # Filter all scenes with collection_name
    scene_list = Scene.query.filter_by(collection_name=collection_name).all()

    # Create tasks with person_id and collection_name
    task_id_list = []
    for scene in scene_list:
        task = Task(scene_id=scene.scene_id, person_id_list=person_id_list)
        db.session.add(task)
        db.session.flush()
        task_id_list.append(task.id)
    db.session.commit()

    # Send out Celery tasks
    ch = chain(
        group([signature('set_up_scene', (scene.scene_id,)) for scene in scene_list]),
        group([signature('render_scene', (task_id,), immutable=True) for task_id in task_id_list])
    )
    ch.apply_async()

    return jsonify({"message": "Tasks generated and sent to the queue."})


@app.route('/create_person', methods=['POST'])
def create_person():
    celery = make_celery(app)
    celery.conf.task_routes = {'set_up_scene': {'queue': 'render_queue'}, 'render_scene': {'queue': 'render_queue'}}

    name = request.form.get('name')
    sex = request.form.get('sex')
    model_type = request.form.get('model_type')
    files = request.files.getlist('files')

    if not name or not sex or not files:
        return jsonify({"error": "Missing required fields"}), 400

    person = Person(name=name, sex=sex, model_type=model_type)
    db.session.add(person)
    db.session.commit()
    train_dataset_path = get_resource_oss_url(ResourceType.TRAIN_DATASET, person.id)

    training_img_keys = []
    for file in files:
        # Save the file to OSS and get the image_key
        oss_key = f'{train_dataset_path}{file.filename}'
        bucket.put_object(oss_key, file)
        training_img_keys.append(oss_key)

    person.training_img_key = training_img_keys
    db.session.commit()

    return jsonify({"success": "Person created successfully", "person_id": person.id}), 201

# Other endpoints remain the same...

if __name__ == '__main__':
    app.run(debug=True)
