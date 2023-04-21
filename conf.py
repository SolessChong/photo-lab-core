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

