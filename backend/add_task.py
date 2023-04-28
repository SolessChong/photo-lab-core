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

    task_range = (2384, 2394)  # WZ, user_9
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
    collection_name_list = [u'风摄影师作品合集\\疯子Charles\\2016\\暗香凉影']
    # collection_name_list = [u'风摄影师作品合集\\疯子Charles\\2016\\暗香凉影', u'古风摄影师作品合集\\七奈Nanako\\2017\\#好想看你穿制服的样子#', u'古 风摄影师作品合集\\七奈Nanako\\2017\\#花儿和少年#']
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

    for collection_name in collection_name_list:
        task_id_list = []
        for scene in Scene.query.filter(Scene.collection_name==collection_name).all():
            for person_id in [6, 8, 10]:
                task = Task(scene_id=scene.scene_id, person_id_list = f'[{person_id}]')
                db.session.add(task)
                db.session.commit()
                task_id_list.append(task.id)

        ch = chain(
                group([signature('set_up_scene', (scene.scene_id,)) for scene in Scene.query.filter(Scene.collection_name==collection_name).all()]),
                group([signature('render_scene', (task_id,), immutable=True) for task_id in task_id_list])
        )
        ch.apply_async()