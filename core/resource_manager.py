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
import json
import numpy as np
import cv2
from PIL import Image

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
                    return str(root / FILE_CONF['LORA_MODEL'] / ('user_' + str(id) + '.safetensors'))
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
                    scene = models.Scene.query.get(id)
                    if scene.hint_img_list is None:
                        return None
                    else:
                        return scene.hint_img_list[0]
                case ResourceType.BASE_IMG:
                    scene = models.Scene.query.get(id)
                    if scene is None:
                        return None
                    else:
                        return scene.base_img_key
                case ResourceType.OUTPUT:
                    task = models.Task.query.get(id)
                    return task.result_img_key
                case ResourceType.TMP_OUTPUT:
                    return str(root / FILE_CONF['TMP_OUTPUT'] / (str(id) + '.png'))
        else:
            raise Exception("Unknown FILE_STORAGE: " + FILE_STORAGE)


def oss2buf(url):
    content_str = bucket.get_object(url)
    buf = io.BytesIO()
    buf.write(content_str.read())
    buf.seek(0)
    return buf

def str2oss(buf, url):
    return bucket.put_object(url, buf)

def oss2str(url):
    return bucket.get_object(url).read()

def read_cv2img(url):
    buf = oss2buf(url)
    img = cv2.imdecode(np.frombuffer(buf.read(), np.uint8), cv2.IMREAD_COLOR)
    return img

def read_PILimg(url):
    buf = oss2buf(url)
    img = Image.open(buf).convert('RGB')
    return img

def write_PILimage(img, url):
    # img_bytes = io.BytesIO()
    # image.save(img_bytes)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    str2oss(buf.getvalue(), url)