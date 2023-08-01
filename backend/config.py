# 阿里云MySQL和OSS相关配置
DB_HOST = 'rm-wz9e5292roauu423g6o.mysql.rds.aliyuncs.com'
DB_USER = 'jarvis_root'
DB_PASSWORD = 'Jarvis123!!'
DB_NAME = 'photolab'

OSS_ACCESS_KEY_ID = 'LTAINBTpPolLKWoX'
OSS_ACCESS_KEY_SECRET = '1oQVQkxt7VlqB0fO7r7JEforkPgwOw'
OSS_BUCKET_NAME = 'photolab-test'
OSS_ENDPOINT = 'oss-cn-shenzhen.aliyuncs.com'

CELERY_CONFIG = {
    'CELERY_BROKER_URL': 'redis://:Yzkj8888!@r-wz9d9mt4zsofl3s0pnpd.redis.rds.aliyuncs.com/0',
    'CELERY_RESULT_BACKEND': 'redis://:Yzkj8888!@r-wz9d9mt4zsofl3s0pnpd.redis.rds.aliyuncs.com/0'
}

IAP_SHARED_PASSWORD = '09a0d8af2b224ba38a925210edf94d2b'

import os

mysql_uri = 'mysql+pymysql://jarvis_root:Jarvis123!!@rm-wz9e5292roauu423g6o.mysql.rds.aliyuncs.com/photolab_dev?charset=utf8'

wait_status = 'wait'
dev_mode = os.environ.get('DEV_MODE') == 'true'
is_industry = False
user_group = 1  # 3 for is_inudstry
min_image_num = 15

if dev_mode:
    mysql_uri = 'mysql+pymysql://jarvis_root:Jarvis123!!@rm-wz9e5292roauu423g6o.mysql.rds.aliyuncs.com/photolab_dev?charset=utf8mb4'
    wait_status = 'dev_wait'
else:
    mysql_uri = 'mysql+pymysql://jarvis_root:Jarvis123!!@rm-wz9e5292roauu423g6o.mysql.rds.aliyuncs.com/photolab?charset=utf8mb4'
    wait_status = 'wait'

BD_CONVERSION_POST_URL = 'https://analytics.oceanengine.com/api/v2/conversion'

print(f'config: ', mysql_uri)

COMPLETE_PACK_MIN_PICS = 30

# 每个pack未解锁前，可以预览的图片数量，超过该数量设为模糊
PREVIEW_CLEAR_IMG_NUM = 5

# 解锁照片需要的点券面额
UNLOCK_PHOTO_DIAMOND = 75

# 小程序的appid
appid='wxd92770660bc5d9cb'
# 小程序的appsecret
appsecret='1f5968f1572ee04e9d5d18a8a7dbd6b6'

# 图片生成后提醒的模板id
PHOTO_GENERATE_TEMPLATE_ID='MaJhNCrgV0FzdQgGPNNxfZ3LCQlTM0f1aDpM_5OqLUs'

# 邀请和被邀请奖励的点券
INVITED_ADD_DIAMOND=100

# 初始的点券
INIT_DIAMOND=100


# 微信支付appid
WECHAT_PAY_APPID='wx8704366ddba782a3'

# 微信支付mchid
WECHAT_PAY_MCHID='1640872063'

# 微信回调地址
WECHAT_PAY_NOTIFY_URL ='https://photolab.aichatjarvis.com:8003/api/wechat/pay_callback'

# 微信支付正式序列号
WECHAT_PAY_CERT_SERIAL='221FBF6FFB2C48737C652FBD40DA298F9C7808E8'

# 微信支付apikey
WECHAT_PAY_API_KEY='yuzhiHoiuasr7098qw3709AWwq342312'

# 人民币和点券的汇率
MONEY_DIAMOND_RATE=100

# 人脸比对的正确率阈值
FACE_COMPARE_CONFIDENCE=60