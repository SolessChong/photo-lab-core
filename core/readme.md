## Scene
- Params
    - 'model': model name
    - 'char_attentions': char attentions (a girl_userxx: X)
    - 'lora_upscaler': lora upscaler

## Workflow: 

1. Train lora:
Run main script in `train_lora.py`

2. Render:
Run main script in `render.py`



## Celery
1. Run worker
celery -A tasks worker -P eventlet
Windows:
`celery -A core.celery_worker.celery worker -P eventlet -l INFO`
Linux:
`celery -A core.celery_worker.celery worker -l INFO`

For queues
`celery -A core.celery_worker.celery worker -l INFO -P eventlet -n train_worker -Q train_queue`
`celery -A core.celery_worker.celery worker -l INFO -P eventlet -n render_worker -Q render_queue`
1. Monitoring
celery --broker=redis://:'Yzkj8888!'@r-wz9d9mt4zsofl3s0pnpd.redis.rds.aliyuncs.com/0 flower --port=5566
celery -A core.celery_worker.celery events
celery -A core.celery_worker.celery inspect reserved

redis-cli -u redis://'default':'Yzkj8888!'@r-wz9d9mt4zsofl3s0pnpd.redis.rds.aliyuncs.com/0 llen train_queue

# Chord for Train and Render:

chord(
        (
            celery_worker.celery.signature(
                "train_lora", 
                args=(3, ['source/yi/2/d5010894d2fd8cbd3518e39c79c0a8df.png', 'source/yi/2/e5f14ff6cafafcf7e1760e4e81fad001.png', 'source/yi/2/68c136564e896d81c36d3f5e54cea386.png', 'source/yi/2/95b6a8ed4d9380f847cedd7a1adcd63d.png', 'source/yi/2/2f0dc8065b5887f59d957513956fd5cb.png', 'source/yi/2/faf7371bb8003b595913e041e3500c6d.png'], 1
                )
            ),
            celery_worker.celery.signature(
                "train_lora", 
                args=(2, ['source/yi/2/d5010894d2fd8cbd3518e39c79c0a8df.png', 'source/yi/2/e5f14ff6cafafcf7e1760e4e81fad001.png', 'source/yi/2/68c136564e896d81c36d3f5e54cea386.png', 'source/yi/2/95b6a8ed4d9380f847cedd7a1adcd63d.png', 'source/yi/2/2f0dc8065b5887f59d957513956fd5cb.png', 'source/yi/2/faf7371bb8003b595913e041e3500c6d.png'], 1
                )
            )
        ),
        group(
            celery_worker.celery.signature(
                "render_scene", args=(18,), immutable=True
            ),
            celery_worker.celery.signature(
                "render_scene", args=(19,), immutable=True
            ),
            celery_worker.celery.signature(
                "render_scene", args=(20,), immutable=True
            )
        )
).apply_async()


chord(celery_worker.task_train_lora.s(3, ['source/yi/2/d5010894d2fd8cbd3518e39c79c0a8df.png', 'source/yi/2/e5f14ff6cafafcf7e1760e4e81fad001.png', 'source/yi/2/68c136564e896d81c36d3f5e54cea386.png', 'source/yi/2/95b6a8ed4d9380f847cedd7a1adcd63d.png', 'source/yi/2/2f0dc8065b5887f59d957513956fd5cb.png', 'source/yi/2/faf7371bb8003b595913e041e3500c6d.png'], epoch=1), celery_worker.task_render_scene.si(18)).apply_async()