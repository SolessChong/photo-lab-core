# 这是推荐照片算法的核心模块，故单独抽取出一个文件 
# v0.1 
#     输入category和person_id_list，根据scene的rate排序，将没有生成过的task加入collection加入结果队列，直到照片得到50张为止。
# v0.2
#     用户可以选择自己喜欢的collection，根据用户选择以及相似的tag排序得到前50张有效照片

import logging
from . import models
from sqlalchemy import and_, cast, String
from .extensions import db

def generate_sd_task(category, person_id_list, user_id, pack_id, limit=20, wait_status='wait'):
    #TODO: use new method to choose which scene to render
    
    # 1. Get all scenes with the same category
    scenes = models.Scene.query.filter(
        models.Scene.img_type==category, 
        models.Scene.action_type=='sd', 
        models.Scene.setup_status == 'finish'
    ).order_by(models.Scene.rate.desc()).limit(500).all()
    
    # 2. Check for existing tasks and calculate new combinations
    new_combinations = []
    for scene in scenes:
        # filtered_tasks = models.Task.query.filter_by(scene_id=scene.scene_id, user_id=user_id)
        # if not filtered_tasks.filter(
        #     cast(models.Task.person_id_list, String) == str(person_id_list)
        # ).first():
        
        # 修改为按照user_id过滤scene
        # 下一版本为为按照用户风格选择
        if not models.Task.query.filter_by(scene_id=scene.scene_id, user_id=user_id).first():
            new_combinations.append((scene.scene_id, person_id_list))
            
        if (len(new_combinations) >= limit):
            break
    new_combinations = new_combinations[:limit]
    m = len(new_combinations)
    logging.info(f'{user_id} has new_combinations: {new_combinations}')
    
    # 3. start train lora 
    for person_id in person_id_list:
        person = models.Person.query.filter(models.Person.id == person_id).first()
        if not person:
            return {"status": "error", "message": f"person_id {person_id} not found"}, 400
        if person and person.lora_train_status is None:
            person.lora_train_status = wait_status # 等待woker_manager启动训练任务
            db.session.commit()
            logging.info(f'{user_id} start to  train lora {person.id}')

    # 4. Add new render tasks
    for scene_id, person_id_list in new_combinations:
        task = models.Task(
            user_id=user_id,
            scene_id=scene_id,
            person_id_list=person_id_list,
            status=wait_status,
            pack_id=pack_id
        )
        db.session.add(task)
        db.session.commit()
    
    return m