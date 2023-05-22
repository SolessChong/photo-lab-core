import json
import logging
from backend.models import *
from backend.extensions import db, app
from backend.config import CELERY_CONFIG
from celery import Celery, chord, group, signature, chain

app.app_context().push()


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

def set_up_for_collection(collection_name):
    scenes = Scene.query.filter(Scene.collection_name==collection_name).all()
    for scene in scenes:
        celery.send_task('set_up_scene', scene.scene_id)

def render_person_on_scenes(person_id, scene_list, pack_id=None):
    task_list = []
    for scene in scene_list:
        task = Task(scene_id=scene.scene_id, person_id_list = person_id, status="wait", pack_id=pack_id)
        db.session.add(task)
        task_list.append(task)
    db.session.commit()
    
    ch = chain(
        group([signature('set_up_scene', (scene.scene_id,)) for scene in scene_list]),
        group([signature('render_scene', (task.id,), immutable=True) for task in task_list])
    )
    ch.apply_async()

# main script
if __name__ == "__main__":
    # Arg parser for arg 'cmd', options: ['render_all_wait', 'collection_prefix', 'collection_name', 'scene_id']
    # Arg parser for arg 'name', '-n' for short, string.
    # Arg parser for arg 'person_list', '-p', type=list, required=True, help='Person id list.'
    # when cmd is ['collection_prefix', 'collection_name'], arg 'name' is required.
    import argparse
    parser = argparse.ArgumentParser(description='Add task to Celery srender queue.')
    parser.add_argument('--cmd', type=str, choices=['render_all_wait', 'collection_prefix', 'collection_name', 'rate', 'scene'], help='Command to execute.')
    parser.add_argument('-c', '--collection', type=str, help='Name of collection or prefix of collection name.')
    parser.add_argument('-p', '--person', type=int, nargs='+', help='Person id list.')
    parser.add_argument('--person_list_json', type=str, help='Person id list in json format.')
    parser.add_argument('--rate', type=int)
    parser.add_argument('--scene', type=int, nargs='+', help='Scene id list.')
    parser.add_argument('--pack_id', type=int)
    parser.add_argument('--collection_prefix', type=str, help='Prefix of collection name.')

    args = parser.parse_args()
    logging.info(f'args: {args}')

    cmd = args.cmd

    # parse person as json. list of list of int
    if args.person:
        person_list = [[p] for p in args.person]
    elif args.person_list_json:
        person_list = json.loads(args.person_list_json)
    else:
        raise Exception('No person list provided. Use --person or --person_list_json.')

    if cmd == 'render_all_wait':
        # celery task for all 'wait' Task in db
        task_list = Task.query.filter(Task.status=='wait').all()
        task_id_list = [task.id for task in task_list]
        print(len(task_id_list))
        for id in task_id_list:
            celery.send_task('render_scene', (id,), immutable=True)
    elif args.collection_prefix:
        collection_prefix = args.collection_prefix
        logging.info(f'collection_name_prefix: {collection_prefix}')
        scene_list = Scene.query.filter(Scene.collection_name.startswith(collection_prefix.replace('\\', '\\\\'))).all()
        logging.info(f'Found {len(scene_list)} scenes.')
        for person in person_list:
            render_person_on_scenes(person, scene_list, args.pack_id)
    elif args.collection:
        collection_name = args.collection
        logging.info(f'collection_name: {collection_name}')
        scene_list = Scene.query.filter(Scene.collection_name==collection_name).all()
        logging.info(f'Found {len(scene_list)} scenes.')
        for person in person_list:
            render_person_on_scenes(person, scene_list, args.pack_id)
    elif args.rate:
        scene_list = Scene.query.filter(Scene.rate >= args.rate).filter(Scene.scene_id > 500).all()
        logging.info(f'Found {len(scene_list)} scenes.')
        for person in person_list:
            render_person_on_scenes(person, scene_list, args.pack_id)
    elif args.scene:
        scene_list = Scene.query.filter(Scene.scene_id.in_(args.scene)).all()
        logging.info(f'Found {len(scene_list)} scenes.')
        for person in person_list:
            render_person_on_scenes(person, scene_list, args.pack_id)

