from core import celery_worker

celery_worker.task_render_scene.delay(0, 557, [1])
