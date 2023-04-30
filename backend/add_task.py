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


def LEGACY():
        # collection_name = 'Sam-part1'
    # collection_name = 'xuejing'
    # collection_name = "SatoruAkiba"
    collection_name = "tingyuan"

    person_id = 8

    scenes = Scene.query.filter(Scene.collection_name==collection_name).all()
    for scene in scenes:
        task = Task(scene_id=scene.scene_id, person_id_list = f'[{person_id}]')
        db.session.add(task)
        db.session.commit()
        celery_worker.task_render_scene.delay(task.id)


    ### Setup scene
    collection_name = 'Sam-part1'
    scenes = Scene.query.filter(Scene.collection_name==collection_name).all()
    for scene in scenes:
        celery_worker.task_set_up_scene.delay(scene.scene_id)



    ### Download model
    person_id = 6
    bucket.get_object_to_file(
        ResourceMgr.get_resource_oss_url(ResourceType.LORA_MODEL, person_id),
        ResourceMgr.get_resource_local_path(ResourceType.LORA_MODEL, person_id)
    )





    task_range = (606, 614)  # Diana, user_10

    task_range = (2384, 2894)  # WZ, user_9
    for i in range(*task_range):
        celery_worker.task_render_scene.delay(i)

    # setup for scenes.
    for s in Scene.query.filter(Scene.collection_name=='ShuntoSato').all():
        celery_worker.task_set_up_scene.delay(s.scene_id)


    ## Test all persons x scenes
    for p in (1, 6, 8, 10):
        collection_name = 'SatoruAkiba'
        scenes = Scene.query.filter(Scene.collection_name==collection_name).all()
        for scene in scenes:
            task = Task(scene_id=scene.scene_id, person_id_list = f'[{p}]')
            db.session.add(task)
            db.session.commit()
            celery_worker.task_render_scene.delay(task.id)

def render_person_on_scenes(person_id, scene_list):
    task_id_list = []
    for scene in scene_list:
        task = Task(scene_id=scene.scene_id, person_id_list = [person_id])
        db.session.add(task)
        db.session.commit()
        task_id_list.append(task.id)
    ch = chain(
        group([signature('set_up_scene', (scene.scene_id,)) for scene in scene_list]),
        group([signature('render_scene', (task_id,), immutable=True) for task_id in task_id_list])
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
    parser.add_argument('cmd', type=str, choices=['render_all_wait', 'collection_prefix', 'collection_name'], help='Command to execute.')
    parser.add_argument('-n', '--name', type=str, help='Name of collection or prefix of collection name.')
    parser.add_argument('-p', '--person_list', type=int, nargs='+', required=True, help='Person id list.')

    args = parser.parse_args()
    logging.info(f'args: {args}')

    # exit if no cmd
    if not args.cmd:
        logging.error('No cmd specified.')
        exit()

    cmd = args.cmd

    if cmd == 'render_all_wait':
        # celery task for all 'wait' Task in db
        task_list = Task.query.filter(Task.status=='wait').all()
        task_id_list = [task.id for task in task_list]
        print(len(task_id_list))
        for id in task_id_list:
            celery.send_task('render_scene', (id,), immutable=True)
    elif cmd == 'collection_prefix':
        collection_prefix = args.name
        logging.info(f'collection_name_prefix: {collection_prefix}')
        scene_list = Scene.query.filter(Scene.collection_name.startswith(collection_prefix.replace('\\', '\\\\'))).all()
        for person in args.person_list:
            render_person_on_scenes(person, scene_list)
    elif cmd == 'collection_name':
        collection_name = args.name
        logging.info(f'collection_name: {collection_name}')
        scene_list = Scene.query.filter(Scene.collection_name==collection_name).all()
        logging.info(f'Found {len(scene_list)} scenes.')
        for person in args.person_list:
            render_person_on_scenes(person, scene_list)

    # ### Collection name X user -> task
    # collection_name_prefix_list = [
    #     u'古风摄影师作品合集\\七奈Nanako\\2021\\夏日炎炎下的可爱子', 
    #     u'古风摄影师作品合集\\七奈Nanako\\2021\\响当当的大铭', 
    #     u'古风摄影师作品合集\\七奈Nanako\\2021\\云知笑 3', 
    #     u'古风摄影师作品合集\\七奈Nanako\\2021\\云知笑 @王楚Dino',
    #     u'古风摄影师作品合集\\七奈Nanako\\2021\\Shirley-Dan花祀',
    #     u'古风摄影师作品合集\\七奈Nanako\\2021\\云知笑',
    #     u'古风摄影师作品合集\\七奈Nanako\\2021\\lulusmile露露斯麦尔',
    #     u'古风摄影师作品合集\\七奈Nanako\\2021\\lolita',
    #     u'古风摄影师作品合集\\七奈Nanako\\2021\\Elpress',
    #     u'古风摄影师作品合集\\七奈Nanako\\2021\\#恋上冬日#',
    #     u'古风摄影师作品合集\\七奈Nanako\\2020\\风霖',
    # ]
    # collection_name_prefix_list = [
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\#好想看你穿制服的样子#',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\#花儿和少年#',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\#阴阳师手游#',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\HiKarii光酱',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\Madmoiselle',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\Makiyamy',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\shio___',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\WinkyWinky88',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\一个漏刀狂魔',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\一盘饮料',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\佳茗w',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\修老虎',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\六月遇见温柔的你',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\化 桀',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\十井源子',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\向音Yuny',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\夏日 蓝天 草莓味的你',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\多芒小yico',
    #     u'古风摄影师作品合集\\七奈Nanako\\2017\\婀娜少女羞，岁月无忧愁。',
    # ]
    # collection_name_prefix_list = [u'古风摄影师作品合集\\七奈Nanako\\2017\\#好想看你穿制服的样子#', u'古风摄影师作品合集\\七奈Nanako\\2017\\#花儿和少年#']
    # ch = chain(
    #         group([
    #             signature('set_up_scene', (830,)), 
    #             signature('set_up_scene', (832,))
    #         ]),
    #         group([
    #             signature('render_scene', (2395,), immutable=True), 
    #             signature('render_scene', (2397,), immutable=True)
    #         ]))
    # ch.apply_async()

    
    # for collection_name_prefix in collection_name_prefix_list:
    #     logging.info(f'collection_name_prefix: {collection_name_prefix}')
    #     scene_list = Scene.query.filter(Scene.collection_name.startswith(collection_name_prefix.replace('\\', '\\\\'))).all()
    #     task_id_list = []
    #     for scene in scene_list:
    #         for person_id in [10]:
    #             task = Task(scene_id=scene.scene_id, person_id_list = f'[{person_id}]')
    #             db.session.add(task)
    #             db.session.commit()
    #             task_id_list.append(task.id)

    #     ch = chain(
    #             group([signature('set_up_scene', (scene.scene_id,)) for scene in scene_list]),
    #             group([signature('render_scene', (task_id,), immutable=True) for task_id in task_id_list])
    #     )
    #     ch.apply_async()


    # for collection_name_prefix in collection_name_prefix_list:
    #     scene_list = Scene.query.filter(Scene.collection_name.startswith(collection_name_prefix.replace('\\', '\\\\'))).all()
    #     person_id = 17
    #     for scene in scene_list:
    #         task = Task(scene_id=scene.scene_id, person_id_list =[person_id], status='wait')
    #         db.session.add(task)
    #     db.session.commit()

