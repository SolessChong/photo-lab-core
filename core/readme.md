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
1. Monitoring
celery --broker=redis://user:pass@39.108.222.9:6379 flower --port=5566