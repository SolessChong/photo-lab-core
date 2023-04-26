import secrets
import time

import logging
from . import discord_util
from . import utils
import requests
from . import extensions
from . import models
import random

logging.basicConfig(level=logging.INFO)

# 使用 __name__ 作为 logger 名称
logger = logging.getLogger(__name__)

# 启动异步生成图片任务，传入参数为person_id、category、pack_id、user_id
# 首先获取person_id对应的所有sources， 然后获取对应type的所有mj scene
# 双重循环遍历scene和source， 分别获得scene和source对应的oss中的图片内容，scene的prompt，source图片的可访问oss地址
# 然后在generated_images表中生成mj 任务
def generate_mj_task(person_id, category, pack_id, user_id):
    logger.info("start generate_mj_task")

    
    sources = models.Source.query.filter_by(person_id=person_id).all()
    scenes = models.Scene.query.filter_by(img_type=category, action_type='mj').all()

    new_combinations = []
    for scene in scenes:
        for source in sources:
            if not models.GeneratedImage.query.filter_by(scene_id=scene.scene_id, source_id=source.source_id).first():
                new_combinations.append((scene, source))
    random.shuffle(new_combinations)
    new_combinations = new_combinations[:10]

    for scene, source in new_combinations:
        logger.info('start mj generete for scene id %d,  source_id: %d', scene.scene_id, source.source_id)
        
        new_image = models.GeneratedImage(scene_id=scene.scene_id, source_id=source.source_id, pack_id=pack_id, user_id=user_id, type=scene.action_type, prompt=scene.prompt, status = 'init')

        extensions.db.session.add(new_image)
        extensions.db.session.commit()

    return len(new_combinations)

        # image_id = new_image.id        

        # response = discord_util.PassPromptToSelfBot(utils.get_signed_url(source.base_img_key) + ' ' + scene.prompt)
        # for i in range(240):
        #     updated_new_image = models.GeneratedImage.query.get(image_id)
        #     if updated_new_image.img_url:
        #         logger.info('get mj image successfully @ time %d for source id: %d, scene id: %d' % (i, source_id, scene.scene_id))
        #         break
        #     time.sleep(1)
        # updated_new_image = models.GeneratedImage.query.get(image_id)
        # if updated_new_image.img_url == None:
        #     logger.info("failed to get mj for source id: %s, scene id: %d" % (source_id, scene.scene_id))