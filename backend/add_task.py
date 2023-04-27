from backend.models import *
from backend.extensions import db, app
from core import celery_worker

app.app_context().push()


### Collection name X user -> task

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



from core.resource_manager import *
person_id = 6
bucket.get_object_to_file(
    ResourceMgr.get_resource_oss_url(ResourceType.LORA_MODEL, person_id),
    ResourceMgr.get_resource_local_path(ResourceType.LORA_MODEL, person_id)
)





task_range = (606, 614)  # Diana, user_10

task_range = (615, 623)  # WZ, user_9
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
