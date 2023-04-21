import os
import sys
# Add pipeline folder to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from conf import FILE_CONF
from pathlib import Path
from enum import Enum

# Enum for resource type
class ResourceType(Enum):
    LORA = 0
    POSE_IMG = 1
    BASE_IMG = 2
    OUTPUT = 3
    TMP_OUTPUT = 4

class ResourceMgr:

    def __init__(self):
        pass

    # Get resource for different type. Not the id is different for different types
    @staticmethod
    def get_resource_path(resource_type, id):
        root = Path(FILE_CONF['ROOT'])
        # switch resource_type
        match resource_type:
            case ResourceType.LORA:
                return str(root / FILE_CONF['LORA'] / (id + '.safetensors'))
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