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



# main script
if __name__ == "__main__":

    ### Collection name X user -> task
    collection_name_prefix_list = [
        u'古风摄影师作品合集\\七奈Nanako\\2021\\夏日炎炎下的可爱子', 
        u'古风摄影师作品合集\\七奈Nanako\\2021\\响当当的大铭', 
        u'古风摄影师作品合集\\七奈Nanako\\2021\\云知笑 3', 
        u'古风摄影师作品合集\\七奈Nanako\\2021\\云知笑 @王楚Dino',
        u'古风摄影师作品合集\\七奈Nanako\\2021\\Shirley-Dan花祀',
        u'古风摄影师作品合集\\七奈Nanako\\2021\\云知笑',
        u'古风摄影师作品合集\\七奈Nanako\\2021\\lulusmile露露斯麦尔',
        u'古风摄影师作品合集\\七奈Nanako\\2021\\lolita',
        u'古风摄影师作品合集\\七奈Nanako\\2021\\Elpress',
    ]
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


    for collection_name_prefix in collection_name_prefix_list:
        scene_list = Scene.query.filter(Scene.collection_name.startswith(collection_name_prefix.replace('\\', '\\\\'))).all()
        person_id = 8
        for scene in scene_list:
            task = Task(scene_id=scene.scene_id, person_id_list =[person_id], status='wait')
            db.session.add(task)
        db.session.commit()
