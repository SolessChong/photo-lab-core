import io
from alibabacloud_facebody20191230.client import Client
from alibabacloud_facebody20191230.models import DetectFaceAdvanceRequest
from alibabacloud_tea_openapi.models import Config
from alibabacloud_tea_util.models import RuntimeOptions

# 阿里云API密钥
access_key_id = 'LTAINBTpPolLKWoX'
access_key_secret = '1oQVQkxt7VlqB0fO7r7JEforkPgwOw'

config = Config(
    access_key_id=access_key_id,
    access_key_secret=access_key_secret,
    endpoint='facebody.cn-shanghai.aliyuncs.com',
    region_id='cn-shanghai'
)

# 检测png图片中的人脸
def detect_face(img):
    detect_face_request = DetectFaceAdvanceRequest()
    detect_face_request.image_urlobject = io.BytesIO(img)
    detect_face_request.landmark = True
    detect_face_request.quality = True
    detect_face_request.pose = True
    detect_face_request.max_face_number = 10

    runtime = RuntimeOptions()

    try:
        # 初始化Client
        client = Client(config)
        response = client.detect_face_advance(detect_face_request, runtime)
        # 获取整体结果
        face_count = response.body.data.face_count

    except Exception as error:
        print("Error:", error)
        print("Error code:", error.code)
        face_count = -1

    return face_count
