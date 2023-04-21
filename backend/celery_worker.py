import secrets
from celery import Celery
from flask import Flask
import time

import logging
import discord_util
import utils
import requests
import models
from extensions import app, db

# 设置日志格式
logging.basicConfig(level=logging.INFO)

# 使用 __name__ 作为 logger 名称
logger = logging.getLogger(__name__)


def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379'
)
celery = make_celery(app)

# 启动异步生成图片任务，传入参数为source 和 scenes (一个包含所有scene的数组)
# 遍历scenes中的每个scene, 分别获得scene和source对应的oss中的图片内容，scene的prompt，source图片的可访问oss地址
# 然后判断scene的action_type为
# 1） reface， 调用reface相应代码（不需要gpt实现）
# 2） mj， 调用mj相应代码 （不需要gpt实现）
@celery.task()
def generate_images_task(source_id, scene_ids, pack_id, user_id):
    source = models.Source.query.filter_by(source_id=source_id).first()
    logger.info("start generate_images_task")
     # Iterate through all the scenes
    for scene_id in scene_ids:
        scene = models.Scene().query.filter_by(scene_id=scene_id).first()
        
        logger.info('start generete for scene id %d,  action_type: %s', scene_id, scene.action_type)
        
        new_image = models.GeneratedImage(scene_id=scene_id, source_id=source.source_id, pack_id=pack_id, user_id=user_id, type=scene.action_type, prompt=scene.prompt, img_url=None)
        db.session.add(new_image)
        db.session.commit()
        image_id = new_image.id
        

        # Check the action_type and call the corresponding function
        if scene.action_type == 'reface':
            source_image = utils.oss_get(source.img_url)
            target_image = utils.oss_get(scene.img_url)
            modify_image = utils.oss_get(scene.img_url)
            akool_response = utils.akool_reface(source_image, target_image, modify_image)
            result_image = None
            for i in range(20):
                response = requests.get(akool_response.json()['url'])
                if response.status_code == 200:
                    result_image = response.content
                    break
                time.sleep(1)

            if result_image:
                # after we get result from akool, update img_url in database
                new_image.img_url = 'generated/' + secrets.token_hex(16) + '.png'
                utils.oss_put(new_image.img_url, result_image)
                db.session.commit()
                logger.info('get akool reface successfully @time %d for source id: %s, scene id: %d' % (i, source_id, scene.scene_id))
            else:
                logger.info("failed to get akool reface for source id: %s, scene id: %d" % (source_id, scene.scene_id))
    

        elif scene.action_type == 'mj':
            response = discord_util.PassPromptToSelfBot(utils.get_signed_url(source.img_url) + ' ' + scene.prompt)
            for i in range(240):
                updated_new_image = models.GeneratedImage.query.get(image_id)
                if updated_new_image.img_url:
                    logger.info('get mj image successfully @ time %d for source id: %d, scene id: %d' % (i, source_id, scene.scene_id))
                    break
                time.sleep(1)
            updated_new_image = models.GeneratedImage.query.get(image_id)
            if updated_new_image.img_url == None:
                logger.info("failed to get mj for source id: %s, scene id: %d" % (source_id, scene.scene_id))
    