# -*- coding: utf-8 -*-
import sys
import oss2
import os
# Add pipeline folder to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from conf import FILE_CONF
from pathlib import Path
from enum import Enum

bucket = None
# endpoint = 'http://oss-cn-hangzhou.aliyuncs.com' # Suppose that your bucket is in the Hangzhou region.
# auth = oss2.Auth('<Your AccessKeyID>', '<Your AccessKeySecret>')
# bucket = oss2.Bucket(auth, endpoint, '<your bucket name>')

# Enum for resource type
class ResourceType(Enum):
    LORA_MODEL = 0
    TRAIN_DATASET = 1
    POSE_IMG = 2
    BASE_IMG = 3
    OUTPUT = 4
    TMP_OUTPUT = 5

class ResourceMgr:

    def __init__(self):
        pass

    # Get resource for different type. Not the id is different for different types
    @staticmethod
    def get_resource_path(resource_type, id):
        root = Path(FILE_CONF['ROOT'])
        # switch resource_type
        match resource_type:
            case ResourceType.LORA_MODEL:
                return str(root / FILE_CONF['LORA_MODEL'] / (id + '.safetensors'))
            case ResourceType.TRAIN_DATASET:
                return str(root / FILE_CONF['TRAIN_DATASET'] / str(id))
            case ResourceType.POSE_IMG:
                return str(root / FILE_CONF['POSE_IMG'] / (id + '.png'))
            case ResourceType.BASE_IMG:
                return str(root / FILE_CONF['BASE_IMG'] / (id + '.png'))
            case ResourceType.OUTPUT:
                return str(root / FILE_CONF['OUTPUT'] / (id + '.png'))
            case ResourceType.TMP_OUTPUT:
                return str(root / FILE_CONF['TMP_OUTPUT'] / (id + '.png'))
            case _:
                raise Exception("Unknown resource type: " + str(resource_type))