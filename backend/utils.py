import pymysql
import oss2
import requests
import urllib
import time
from io import BytesIO
from PIL import Image

# 阿里云MySQL和OSS相关配置
DB_HOST = 'rm-wz9e5292roauu423g6o.mysql.rds.aliyuncs.com'
DB_USER = 'jarvis_root'
DB_PASSWORD = 'Jarvis123!!'
DB_NAME = 'photolab'

OSS_ACCESS_KEY_ID = 'LTAINBTpPolLKWoX'
OSS_ACCESS_KEY_SECRET = '1oQVQkxt7VlqB0fO7r7JEforkPgwOw'
OSS_BUCKET_NAME = 'photolab-test'
OSS_ENDPOINT = 'oss-cn-shenzhen.aliyuncs.com'

AKOOL_URL = 'https://faceswap.akool.com/api/v1/faceswap/highquality/specifyimage'
AKOOL_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY0MjZiNDU3NzczNTM2MDE2MDU1Nzk0NCIsInVpZCI6MTcwNTk1LCJ0eXBlIjoidXNlciIsImlhdCI6MTY4NDcyMjEwOSwiZXhwIjoxNjg3MzE0MTA5fQ.k0P3W4ejFjDr5cLCWsuz3CEMcrDOevV1N6lv0RgYJzY'
# 创建数据库连接
def create_db_conn():
    return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)

# 创建OSS连接
def create_oss_client():
    return oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)

def get_bucket():
    return oss2.Bucket(create_oss_client(), OSS_ENDPOINT, OSS_BUCKET_NAME)

# def get_db_scenes(img_type, action_type):
#     db_conn = create_db_conn()
#     cursor = db_conn.cursor(pymysql.cursors.DictCursor)
    
#     query = "SELECT * FROM scenes WHERE img_type=%s AND action_type=%s"
#     cursor.execute(query, (img_type, action_type))
#     scenes = cursor.fetchall()
#     return scenes

def db_get(query, values):
    db_conn = create_db_conn()
    cursor = db_conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute(query, values)
    return cursor.fetchall()

# deprecated, explore time validation in the future
# def get_signed_url(img_key, is_shuiyin = False, is_yasuo = False):
#      # 获取图片signed URL
#     params = {'x-oss-process': 'image/auto-orient,1/quality,q_90/format,jpg'}
#     bucket = oss2.Bucket(create_oss_client(), OSS_ENDPOINT, OSS_BUCKET_NAME, )
#     if is_shuiyin:
#         params = {'x-oss-process': 'image/auto-orient,1/quality,q_95/format,jpg/watermark,text_UGljIE1hZ2ljICAgICAgIA,color_c4c3c3,size_150,rotate_30,fill_1,shadow_20,g_se,t_20,x_30,y_30'}
#     if is_yasuo:
#         params = {'x-oss-process': 'image/auto-orient,1/resize,p_46/quality,q_50/format,jpg'}
#     return bucket.sign_url('GET', img_key, 3600, params=params) # 设置一个小时的有效期

def get_signed_url(img_key, is_shuiyin = False, is_yasuo = False, is_mohu = False):
    value = 'image/auto-orient,1/quality,q_90/format,jpg'

    if is_shuiyin:
        value += '/watermark,text_UGljIE1hZ2ljICAgICAgIA,color_ffffff,size_250,rotate_30,fill_1,shadow_100,g_se,t_78,x_30,y_30'
    if is_yasuo:
        value += '/resize,m_lfit,w_400'
    if is_mohu:
        value += '/blur,r_20,s_20'
    oss_domain = f"http://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}"

    return oss_domain + '/' + urllib.parse.quote(img_key.encode('utf-8')) + '?&x-oss-process=' + value

# def download_image(url):
#     for i in range(20):
#         response = requests.get(url)
#         if response.status_code == 200:
#             return BytesIO(response.content)
#         else:
#             print(f"Error downloading image: {response.status_code}")
#         time.sleep(1)
#     return None

def akool_reface(source_image, target_image, modify_image):
    headers = {
        'Authorization': f'Bearer {AKOOL_TOKEN}',
    }

    files = {
        'sourceImage': ('source.jpg', source_image, 'image/jpeg'),
        'targetImage': ('target.jpg', target_image, 'image/jpeg'),
        'modifyImage': ('modify.jpg', modify_image, 'image/jpeg'),
    }

    response = requests.post(AKOOL_URL, headers=headers, files=files)

    if response.status_code == 200:
        print("Files uploaded successfully")
    else:
        print(f"Error uploading files: {response.status_code}")

    return response

def oss_put(key, value):
    # 上传图片到OSS
    bucket = get_bucket()
    bucket.put_object(key, value)

def oss_get(key):
    bucket = get_bucket()
    return bucket.get_object(key).read()

def oss_source_get(key):
    bucket = oss2.Bucket(create_oss_client(), OSS_ENDPOINT, 'photolab-sources')
    return bucket.get_object(key).read()

# 数据库存储操作
def db_execute(query, values):
    # 将图片信息存入数据库
    db_conn = create_db_conn()
    cursor = db_conn.cursor()
    cursor.execute(query, values)
    db_conn.commit()
    return cursor.lastrowid

def convert_to_png_bytes(image_file):
    try:
        image = Image.open(image_file)
        output = BytesIO()
        image.save(output, "PNG")
        png_bytes = output.getvalue()
        return png_bytes
    except Exception as e:
        print(f"Error while converting image to PNG: {e}")
        raise

def convert_to_jpg_bytes(png_bytes):
    # 从 bytes 数据中加载 PNG 图像
    png_image = Image.open(BytesIO(png_bytes))
    
    # 创建一个 bytes 流来保存 JPG 图像
    jpg_image_io = BytesIO()
    
    # 将图像转换为 'RGB' 模式以确保不会有 alpha 通道，然后保存为 JPG 格式
    png_image.convert('RGB').save(jpg_image_io, format='JPEG')
    
    # 获取 JPG 图像的 bytes 数据
    jpg_bytes = jpg_image_io.getvalue()

    return jpg_bytes

def get_image_size(img_url):
    response = requests.get(img_url)
    img = Image.open(BytesIO(response.content))
    return img.height, img.width

def get_oss_image_size(img_key):
    params = {'x-oss-process': 'image/info'}
    bucket = oss2.Bucket(create_oss_client(), OSS_ENDPOINT, OSS_BUCKET_NAME, )
    url = bucket.sign_url('GET', img_key, 3600, params=params)
    response = requests.get(url)
    img_info = response.json()
    return img_info['ImageHeight']['value'], img_info['ImageWidth']['value']

# Validate IAP receipt
def validate_IAP_receipt(receipt):
    url = 'https://buy.itunes.apple.com/verifyReceipt'
    data = {'receipt-data': receipt}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        rst = response.json()
        return len(rst['receipt']['in_app']) > 0 and rst['status'] == 0
    else:
        print(f"Error validating IAP receipt: {response.status_code}")
        return False