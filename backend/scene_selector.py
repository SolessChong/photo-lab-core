# 这是推荐照片算法的核心模块，故单独抽取出一个文件 
# v0.1 
#     输入category和person_id_list，在本文件规定好collection的顺序，按照collection加入结果队列，直到照片得到50张为止。
# v0.2
#     用户可以选择自己喜欢的collection，根据用户选择以及相似的tag排序得到前50张有效照片

import models

def get_scene


    scenes = models.Scene.query.filter(models.Scene.img_type==category, models.Scene.action_type=='sd', models.Scene.hint_img_list != None).all()

    # 2. Check for existing tasks and calculate new combinations
    new_combinations = []
    for scene in scenes:
        if not models.Task.query.filter_by(scene_id=scene.scene_id, person_id_list=person_id_list, user_id=user_id).first():
            new_combinations.append((scene.scene_id, person_id_list))
    m = len(new_combinations)
    logger.info(f'{user_id} has new_combinations: {new_combinations}')
    
    # 3. If there are new combinations, handle them based on lora_train_status
    if m == 0:
        return jsonify({'code': 1, 'msg': 'no new task to start'})
    