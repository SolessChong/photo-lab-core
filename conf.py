import os

TRAIN_UTILS_ROOT = "D:/sd/kohya_ss/"
# SUBJECT_PLACEHOLDER = "person_MYDEARUSERXX"
SUBJECT_PLACEHOLDER = "girl_userxx"

DEBUG = True

# Image rendering settings
RENDERING_SETTINGS = {
    "size": (512, 512),
}

FILE_CONF = {
    # Define root as conf.py file loction
    'ROOT': os.path.dirname(os.path.abspath(__file__)),
    'LORA': '',
    'POSE_IMG': 'data/pose_img',
    'BASE_IMG': 'data/base_img',
    'OUTPUT': 'data/output',
    'TMP_OUTPUT': 'data/output/tmp',
}

MODEL_RESOURCES = {
    'CM.ST': 'D:/sd/stable-diffusion-webui/models/Stable-diffusion/chilloutmix_NiPrunedFp16Fix.safetensors',
}

DATA_RESOURCES = {
    'REG.WOMEN': 'D:/sd/data/regularization/Stable-Diffusion-Regularization-Images-color_photo_of_a_woman_ddim',
}

TRAIN_PARAMS = {
    'ENLARGE_FACE': 2,
    'REMOVE_BACKGROUND': True,
}