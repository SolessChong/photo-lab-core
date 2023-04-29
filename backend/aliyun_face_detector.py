import io
from PIL import Image
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


def aliyun_face_detect(img):
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
        
    except Exception as error:
        print("Error:", error)
        print("Error code:", error.code)
    
    return response

# 检测png图片中的人脸
def detect_face(img):
    return aliyun_face_detect(img).body.data.face_count

def get_face_coordinates(img):
    return aliyun_face_detect(img).body.data.face_rectangles[:4]

def crop_face_pil(image_data, face_coordinates):
    # 从二进制数据创建一个PIL图像对象
    img = Image.open(io.BytesIO(image_data))

    # 获取人脸坐标
    if face_coordinates and len(face_coordinates) == 4:
        x, y, width, height = face_coordinates
    else:
        x, y, width, height = 0, 0, img.width, img.height

    # 增加高度为原来的30%
    new_height = int(height * 1.3)
    
    # 将宽度设置为与新高度相同
    new_width = new_height

    # 计算截取区域的中心点
    center_x = x + width // 2
    center_y = y + height // 2

    # 计算新的截取区域的左上角和右下角坐标
    left = center_x - new_width // 2
    top = center_y - new_height // 2
    right = center_x + new_width // 2
    bottom = center_y + new_height // 2

    # 处理超出原图大小的情况
    left = max(0, left)
    top = max(0, top)
    right = min(img.width, right)
    bottom = min(img.height, bottom)

    # 截取图像中的人脸区域
    cropped_face = img.crop((left, top, right, bottom))

    # 将截取后的图像转换为字节对象
    cropped_face_bytes = io.BytesIO()
    cropped_face.save(cropped_face_bytes, format='JPEG')
    cropped_face_bytes = cropped_face_bytes.getvalue()

    return cropped_face_bytes

def crop_16_9_pil(image_data, face_coordinates):
    # 从二进制数据创建一个PIL图像对象

    img = Image.open(io.BytesIO(image_data))

    # 获取人脸坐标
    if face_coordinates and len(face_coordinates) == 4:
        x, y, width, height = face_coordinates
    else:
        x, y, width, height = 0, 0, img.width, img.height
    center_y = y + height // 2

    # 计算新的截取区域的宽度和高度
    new_width = img.width
    new_height = int(new_width * 9 / 16)

    # 计算新的截取区域的左上角和右下角坐标
    left = 0
    top = center_y - new_height // 2
    right = new_width
    bottom = center_y + new_height // 2

    # 处理超出原图大小的情况
    if top < 0:
        bottom -= top
        top = 0
    if bottom > img.height:
        top -= (bottom - img.height)
        bottom = img.height
    top = max(0, top)

    # 截取图像中的指定区域
    cropped_image = img.crop((left, top, right, bottom))

    # 将截取后的图像转换为字节对象
    cropped_image_bytes = io.BytesIO()
    cropped_image.save(cropped_image_bytes, format='JPEG')
    cropped_image_bytes = cropped_image_bytes.getvalue()

    return cropped_image_bytes