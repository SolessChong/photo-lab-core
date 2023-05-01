import os

TRAIN_UTILS_ROOT = "/home/chong/photolab/kohya_ss/"
# SUBJECT_PLACEHOLDER = "person_MYDEARUSERXX"
SUBJECT_PLACEHOLDER = "girl_userxx"

DEBUG = True

FILE_STORAGE = 'OSS'   # ['OSS', 'LOCAL']

# Image rendering settings
LORA_ROI_RENDERING_SETTINGS = {
    "size": (512, 512),
}

DIRECT_RENDERING_SETTINGS = {
    "size": (512, 768),
}

PATH_CONF = {
    # Define root as conf.py file loction
    'ROOT': os.path.dirname(os.path.abspath(__file__)),
    'LORA_MODEL': 'train/models/lora/',
    'TRAIN_DATASET': 'data/train_dataset/',
    'POSE_IMG': 'data/pose_img',
    'BASE_IMG': 'data/base_img',
    'OUTPUT': 'data/output',
    'TMP_OUTPUT': 'data/output/tmp',
}

# create paths if not exists
path_to_create = ['train/models/lora', 'data']
for path in path_to_create:
    if not os.path.exists(os.path.join(PATH_CONF['ROOT'], path)):
        os.makedirs(os.path.join(PATH_CONF['ROOT'], path))

MODEL_RESOURCES = {
    'CM.ST': '/home/chong/photolab/stable-diffusion-webui/models/Stable-diffusion/chilloutmix_NiPrunedFp16Fix.safetensors',
}

DATA_RESOURCES = {
    'REG.WOMEN': '/home/chong/photolab/data/Stable-Diffusion-Regularization-Images-color_photo_of_a_woman_ddim',
}

TRAIN_PARAMS = {
    'ENLARGE_FACE': 2,
    'REMOVE_BACKGROUND': True,
}

