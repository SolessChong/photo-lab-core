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

import os

mysql_uri = 'mysql+pymysql://jarvis_root:Jarvis123!!@rm-wz9e5292roauu423g6o.mysql.rds.aliyuncs.com/photolab_dev?charset=utf8'

wait_status = 'wait'
dev_mode = os.environ.get('DEV_MODE') == 'true'
is_industry = False
user_group = 1  # 3 for is_inudstry
min_image_num = 15

if dev_mode:
    mysql_uri = 'mysql+pymysql://jarvis_root:Jarvis123!!@rm-wz9e5292roauu423g6o.mysql.rds.aliyuncs.com/photolab_dev?charset=utf8'
    wait_status = 'dev_wait'
else:
    mysql_uri = 'mysql+pymysql://jarvis_root:Jarvis123!!@rm-wz9e5292roauu423g6o.mysql.rds.aliyuncs.com/photolab?charset=utf8'
    wait_status = 'wait'

print(f'config: ', mysql_uri)
