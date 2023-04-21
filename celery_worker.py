######################
# data structure
######################
# 
# 1. Scene
#  - id
#  - name
#  - base_img_key
#  - hint_img_list
#     - id
#     - hint_img_key
#  - ROI_list
#     - id
#     - type: [man_head, woman_head, pet]
#     - bbox (x, y, w, h)
#     - mask_img_key
#  - model_name
#  - promp
#  - negative_prompt
#  - params
#
# 2. Person
#  - id
#  - name
#  - model_type # lora for now.
#  - model_file_key
#  - sex
#
# 3. Task
#  - id
#  - person_id
#  - scene_id
#  - status
#  - result_img_key
#  - debug_img[1..10]
#


import conf
from train_lora import *
from resource_manager import ResourceMgr, ResourceType

# Train LORA model
@app.task
def train_lora(person_id, train_img_list):
    # save to local


    img_train_path = Path(args.dataset_path) / "img_train"

    # read img list from img_path
    detect_subject_and_crop(args.dataset_path, remove_bg=conf.TRAIN_PARAMS['REMOVE_BACKGROUND'], enlarge=enlarge_face)

    ## 2. Captioning
    #
    logging.info("=== start captioning")
    captioning(img_train_path,  remove_bg=remove_bg)

    ## 3. Train LORA model
    #
    logging.info("=== start training LORA model")
    train_lora(args.dataset_path, conf.SUBJECT_PLACEHOLDER, 'girl')

    # TODO: save to db @fengyi
    # local path: ResourceMgr.get_resource_path(ResourceType.LORA_MODEL, person_id)


def render_scene(scene_id, person_id):
    # scene_base_img, lora_file_list, hint_img_list, ROI_list[mask_img_list, bbox], prompt, negative_prompt, debug_list[1..10]