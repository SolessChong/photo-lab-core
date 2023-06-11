## Scene
- Params
    - 'model': model name
    - 'char_attentions': char attentions (a girl_userxx: X)
    - 'i2i_params': i2i params dict
    - 'lora_upscaler_params': lora upscaler params dict

e.g.
    Scene.params = {
        "model": "dreamshaper_4BakedVaeFp16",
        "i2i_params":{
            "sampler_name": "Euler a"
        },
        "lora_upscaler_params":{
            "upscaler_1": "ESRGAN_4x",
            "upscaler_2": "R-ESRGAN 4x+ Anime6B",
            "extras_upscaler_2_visibility": 0.6,
        }
    }

    Scene.params = {
        "model": "chilloutmix_NiPrunedFp16Fix", 
        "i2i_params":{
            "sampler_name": "DPM++ SDE Karras"
        },
    }

    // head minimalist
    {
        "i2i_params": {
            "sampler_name": "Euler a",
            "denoising_strength": 0.7,
            "steps": 30
        },
        "model": "chilloutmix_NiPrunedFp16Fix",
        "lora_upscaler_params": {
            "upscaler_1": "ESRGAN_4x",
            "upscaler_2": "R-ESRGAN 4x+",
            "extras_upscaler_2_visibility": 0.5
        }
    }

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


# Training cases
- 137 15p YML, 10 epoch * (2500+1500) -> 40k iter
- 140 50p YML, 10 epoch * (2500+1500) -> 40k iter
- 154 10p 代理, 20 epoch * (2500+1500) -> 80k iter
- 153 15p YML, 20 epoch * (2500+1500) -> 80k iter
- 185 8p 胖姐, 20 epoch * (2500+1500) -> 80k iter
- 204 10p 小妹妹
- 206 10p qian ge 
- 226 10p 努力妞
- 233 10p 冯二妹妹 原始
- 263 10p 冯一妹妹 10 epoch * (2500+1500) -> 40k iter
- 264 25p 网红2 10 epoch * (2500+1500) -> 40k iter
- 265 25p 网红2 10 epoch * (2500+1500) -> 40k iter
- 216 10p 韬哥妹妹 
- 293 20p Ins姐 
- 299 20p Ins姐 Train v0.2.0
- 301 10p 韬哥妹妹 color, flip aug.
- 340 10p 冯一妹妹 color, flip aug, rot aug, rembg
- 344 10p 台湾发型师 color, flip aug, rot aug, rembg
- 346 10p 冯一妹妹 color, flip aug, rot aug, enlarge aug, no rembg
- 348 10p 努力妞 color, flip aug, rot aug, enlarge aug, no rembg
- 354 10p Diana, Train v0.2.0
- 358 30p 网红2, Train v0.2.0
- 366 20p 杨幂 Train v0.2.0
- 384 50p Taylor Swift Train v0.2.0
- 400 30p zihan Train v0.2.0
- 1152 20p shanghai Train v0.2.0
- 1208 20p 好看的小姐姐 Train v0.2.0    
- 1337 20p 好看小姐姐 上海 Train v0.2.0
- 1607 20p 网红，上海 Train v0.2.0  
- 1761 30p Diana zZxQFqhc6t Train v0.2.0