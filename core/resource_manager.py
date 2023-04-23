# -*- coding: utf-8 -*-
import sys
import oss2
import os
# Add pipeline folder to path
from core.conf import FILE_CONF, FILE_STORAGE
from pathlib import Path
from enum import Enum
from backend import models
import io

OSS_ACCESS_KEY_ID = 'LTAINBTpPolLKWoX'
OSS_ACCESS_KEY_SECRET = '1oQVQkxt7VlqB0fO7r7JEforkPgwOw'
OSS_BUCKET_NAME = 'photolab-test'
OSS_ENDPOINT = 'oss-cn-shenzhen.aliyuncs.com'

endpoint = OSS_ENDPOINT
auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
bucket = oss2.Bucket(auth, endpoint, OSS_BUCKET_NAME)

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
        # For local file:
        if FILE_STORAGE == 'local':
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
        elif FILE_STORAGE == 'OSS':
            match resource_type:
                case ResourceType.LORA_MODEL:
                    return str(root / FILE_CONF['LORA_MODEL'] / (id + '.safetensors'))
                case ResourceType.TRAIN_DATASET:
                    return str(root / FILE_CONF['TRAIN_DATASET'] / str(id))
                case ResourceType.POSE_IMG:
                    '''
                    img_str = self._bucket.get_object(img_path)
                    img_buf = io.BytesIO()
                    img_buf.write(img_str.read())
                    img_buf.seek(0)
                    img = Image.open(img_buf).convert('RGB')
                    '''
                    scene = models.Scene.objects.get(id=id)
                    img_str = bucket.get_object(scene.pose_img_key)
                    img_buf = io.BytesIO()
                    img_buf.write(img_str.read())
                    img_buf.seek(0)
                    return img_buf
                case ResourceType.BASE_IMG:
                    scene = models.Scene.objects.get(id=id)
                    img_str = bucket.get_object(scene.base_img_key)
                    img_buf = io.BytesIO()
                    img_buf.write(img_str.read())
                    img_buf.seek(0)
                    return img_buf
                case ResourceType.OUTPUT:
                    task = models.Task.objects.get(id=id)
                    return task.result_img_key
                case ResourceType.TMP_OUTPUT:
                    pass
        else:
            raise Exception("Unknown FILE_STORAGE: " + FILE_STORAGE)