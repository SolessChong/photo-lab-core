from . import models
from . import utils
from . import extensions
import requests, time, logging, secrets

# 每次从GeneratedImages中读取一个status为'wait'且action_type为'reface'的图片,
# status设为processing，
# 调用akool_reface函数，将结果上传到oss，然后更新GeneratedImages中的img_url和status

def work():
    
    task = models.GeneratedImage.query.filter_by(status='wait', type='reface').first()
    if not task:
        logging.info('no task to process')
        return
    
    try:
        source = models.Source.query.filter_by(source_id=task.source_id).first()
        scene = models.Scene.query.filter_by(scene_id=task.scene_id).first()

        source_image = utils.oss_get(source.base_img_key)
        target_image = utils.oss_get(scene.base_img_key)
        modify_image = utils.oss_get(scene.base_img_key)
        akool_response = utils.akool_reface(source_image, target_image, modify_image)    

        print(akool_response.json())
        
        result_image = None
        for i in range(20):
            response = requests.get(akool_response.json()['url'])
            if response.status_code == 200:
                result_image = response.content
                break
            time.sleep(1)

        if result_image:
            # after we get result from akool, update img_url in database
            task.img_oss_key = f'generated/{task.user_id}/{secrets.token_hex(4)}.png'

            utils.oss_put(task.img_oss_key, result_image)
            task.status = 'finish'
            logging.info('get akool reface successfully @time %d for source id: %s, scene id: %d' % (i, source.source_id, scene.scene_id))
        else:
            logging.info("failed to get akool reface for source id: %s, scene id: %d" % (source.source_id, scene.scene_id))
            task.status = 'fail'
    except Exception as e:
        logging.error(e)
        task.status = 'fail'
    finally:
        extensions.db.session.add(task)
        extensions.db.session.commit()

if __name__ == '__main__':
    extensions.app.app_context().push()
    while True:
        work()
        time.sleep(1)