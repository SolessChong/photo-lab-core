from core import celery_worker

celery_worker.task_render_scene.delay(1)
