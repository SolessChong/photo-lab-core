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