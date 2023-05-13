# Author: ChatGPT v4.0. Prompter: the humble Solesschong
import os
import oss2
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from backend.extensions import  app, db
from flask_cors import CORS
import json
from PIL import Image
from core.resource_manager import *
from backend.models import User, Source, Person, GeneratedImage, Pack, Scene, Task, Payment
from celery import Celery, chain, chord, group, signature
from backend.config import CELERY_CONFIG
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from werkzeug.datastructures import FileStorage
from io import BytesIO

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

#####################
## Scene Tab
@app.route('/list_scenes', methods=['GET'])
def list_scenes():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    collection_name_filter = request.args.get('collection_name_filter', '', type=str)

    # Filter scenes based on the collection_name_filter if it's not empty
    if collection_name_filter:
        scenes_pagination = Scene.query.filter(Scene.collection_name.contains(collection_name_filter.replace('\\', '\\\\'))).order_by(Scene.scene_id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    else:
        scenes_pagination = Scene.query.order_by(Scene.scene_id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    scenes = scenes_pagination.items
    total_pages = scenes_pagination.pages

    scene_list = [scene.to_dict() for scene in scenes]

    return jsonify({'scenes': scene_list, 'total_pages': total_pages})



@app.route('/api/scene/<int:scene_id>/update_params', methods=['POST'])
def update_scene_params(scene_id):
    data = request.get_json()  # Get JSON data from request
    updated_params = data.get('params')  # Get params from JSON data
    scene = Scene.query.get(scene_id)

    if scene is None:
        return jsonify({"error": "Scene not found"}), 404

    if updated_params == "":
        scene.params = None
    else:
        try:
            scene.params = json.loads(updated_params)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON"}), 400

    db.session.commit()
    return jsonify({"success": True, "params": scene.params})

@app.route('/update_scene_rate', methods=['POST'])
def update_scene_rate():
    scene_id = request.json.get('scene_id')
    action = request.json.get('action')

    scene = Scene.query.get(scene_id)

    if not scene:
        return jsonify({'error': 'Scene not found'}), 404

    if scene.rate is None:
        scene.rate = 0
    if action == 'add':
        scene.rate += 1
    elif action == 'minus':
        scene.rate -= 1
    else:
        return jsonify({'error': 'Invalid action'}), 400

    db.session.commit()
    return jsonify({'success': True, 'rate': scene.rate})

@app.route('/api/scene/<int:scene_id>/update_prompt', methods=['POST'])
def update_scene_prompt(scene_id):
    updated_prompt = request.form.get('prompt')
    scene = Scene.query.get(scene_id)

    if scene is None:
        return jsonify({"error": "Scene not found"}), 404

    scene.prompt = updated_prompt
    db.session.commit()
    return jsonify({"success": True, "prompt": scene.prompt})

@app.route('/list_tasks/<int:scene_id>', methods=['GET'])
def list_tasks_filtered(scene_id):
    tasks = Task.query.filter_by(scene_id=scene_id).all()
    task_list = [{'task_id': task.id, 'result_img_key': f'https://photolab-test.oss-cn-shenzhen.aliyuncs.com/{task.result_img_key}'} for task in tasks]
    return jsonify(task_list)


#####################
## Task Tab 
@app.route('/list_tasks', methods=['GET'])
def list_tasks():
    tasks = Task.query.all()
    task_list = [{'task_id': task.id, 'result_img_key': f'https://photolab-test.oss-cn-shenzhen.aliyuncs.com/{task.result_img_key}'} for task in tasks]
    return jsonify(task_list)

@app.route('/get_tasks', methods=['GET'])
def get_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = 100

    collection_name_filter = request.args.get('collection_name', None)
    person_id_filter = request.args.get('person_id', None, type=int)

    tasks_query = Task.query.filter(Task.result_img_key != None)

    if collection_name_filter:
        tasks_query = tasks_query.join(Scene, Task.scene_id == Scene.scene_id).filter(Scene.collection_name == collection_name_filter)

    if person_id_filter:
        tasks_query = tasks_query.filter(func.JSON_CONTAINS(Task.person_id_list, str(person_id_filter)))

    tasks_pagination = tasks_query.order_by(Task.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
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
    persons = Person.query.with_entities(Person.id, Person.name).order_by(Person.id.desc()).all()
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
    person_id_list = [person_id]

    # Filter all scenes with collection_name
    scene_list = Scene.query.filter_by(collection_name=collection_name).all()

    # Create tasks with person_id and collection_name
    task_id_list = []
    for scene in scene_list:
        task = Task(scene_id=scene.scene_id, person_id_list=person_id_list, status='wait')
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

####################
### Stats tab
@app.route('/get_task_stats', methods=['GET'])
def task_stats():
    stats = ['wait', 'finish', 'fail']
    task_counts = {}
    for stat in stats:
        task_counts[stat] = Task.query.filter(Task.status == stat).count()
    return jsonify(task_counts)

@app.route('/get_scene_stats', methods=['GET'])
def scene_stats():
    setup_statuses = ['wait', 'finish', 'fail']
    scene_counts = {}
    for status in setup_statuses:
        scene_counts[status] = Scene.query.filter(Scene.setup_status == status).count()
    return jsonify(scene_counts)

@app.route('/get_payment_stats', methods=['GET'])
def payment_stats():
    payments = Payment.query.order_by((Payment.id.desc())).limit(10).all()
    payment_stats = []
    for payment in payments:
        payment_stats.append({
            'id': payment.id,
            'user_id': payment.user_id,
            'payment_amount': payment.payment_amount,
            'pack_id': payment.pack_id,
            'product_id': payment.product_id
        })
    return jsonify(payment_stats)

####################
### Person Tab
@app.route('/list_persons', methods=['GET'])
def list_persons():
    persons = db.session.query(Person, User.ip).join(User, Person.user_id == User.user_id).order_by(Person.id.desc()).limit(100)
    persons_data = [{'id': p.id, 'name': p.name, 'user_id': p.user_id, 'ip': ip, 'lora_train_status': p.lora_train_status, 'dataset_quality': p.dataset_quality} for p, ip in persons]
    return jsonify(persons_data)



@app.route('/list_sources', methods=['GET'])
def list_sources():
    person_id = request.args.get('person_id', type=int)
    sources = Source.query.filter(Source.person_id == person_id).all()
    sources_data = [{'base_img_key': s.base_img_key} for s in sources]
    return jsonify(sources_data)

@app.route('/get_all_user', methods=['GET'])
def get_all_user():
    users = User.query.order_by(User.id.desc()).all()
    user_ids = [user.user_id for user in users]
    return jsonify({"data": {"user_ids": user_ids}})

# Other endpoints remain the same...

####################
### Create Scene Tab
@app.route('/api/create_scene', methods=['POST'])
def create_scene():
    form_data = request.form
    img_file: FileStorage = request.files.get('base_img_key')

    if img_file:
        img = Image.open(BytesIO(img_file.read()))
        img_key = 'path/to/oss/folder/' + form_data['collection_name'] + '/' + img_file.filename
        img_key = img_key.split('.')[0] + '.png'
        write_PILimg(img, img_key)

        scene = Scene(
            base_img_key=img_key,
            prompt=form_data['prompt'],
            action_type=form_data['action_type'],
            img_type=form_data['img_type'],
            negative_prompt=form_data['negative_prompt'],
            params=json.loads(form_data['params']) if form_data['params'] else None,
            collection_name=form_data['collection_name'],
            setup_status="wait",
        )

        db.session.add(scene)
        db.session.commit()

        return jsonify({'scene_id': scene.scene_id})
    else:
        return jsonify({'error': 'No image file provided'}), 400
    
@app.route('/api/get_scene', methods=['GET'])
def get_scene():
    scene_id = request.args.get('scene_id', type=int)
    if not scene_id:
        return jsonify({'error': 'No scene ID provided'}), 400

    scene = Scene.query.filter_by(scene_id=scene_id).first()

    if scene:
        return jsonify(scene.to_dict())
    else:
        return jsonify({'error': 'Scene not found'}), 404



if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5000)