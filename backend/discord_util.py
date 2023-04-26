#strings
DAVINCI_TOKEN = 'MTA5MTc2Mzg4NzQ1MzUwNzcwNA.GspQDe.qnWTlStz8jtf3Y9v-HtWRi6zCcfjAQ1gJHsxTE' #[Token of Discord bot]

SERVER_ID = '1091783093465128980' # [Server id here]

SALAI_TOKEN = 'OTAyNDY5MzcyNTYyNTM0NDEw.GzQhLp.PCerC9nXcbBlMktavcTXRhDLtYO4H5mBKtNTOg' #[Token of the Account from which you paid MidJourney ]

CHANNEL_ID = '1091783093465128983' #[Channel in which commands are sent]

#boolean
USE_MESSAGED_CHANNEL = False

#don't edit the following variable
MID_JOURNEY_ID = "936929561302675456"  #midjourney bot id
targetID       = ""
targetHash     = ""


import requests

def PassPromptToSelfBot(prompt : str):
    payload ={"type":2,"application_id":"936929561302675456","guild_id":SERVER_ID,
              "channel_id":CHANNEL_ID,"session_id":"2fb980f65e5c9a77c96ca01f2c242cf6",
              "data":{"version":"1077969938624553050","id":"938956540159881230","name":"imagine","type":1,"options":[{"type":3,"name":"prompt","value":prompt}],
                      "application_command":{"id":"938956540159881230",
                                             "application_id":"936929561302675456",
                                             "version":"1077969938624553050",
                                             "default_permission":True,
                                             "default_member_permissions":None,
                                             "type":1,"nsfw":False,"name":"imagine","description":"Create images with Midjourney",
                                             "dm_permission":True,
                                             "options":[{"type":3,"name":"prompt","description":"The prompt to imagine","required":True}]},
              "attachments":[]}}
    

    header = {
        'authorization' : SALAI_TOKEN
    }

    return requests.post("https://discord.com/api/v9/interactions", json = payload, headers = header)

import time
from datetime import datetime, timedelta
from .models import db, GeneratedImage
from . import utils
from . import models
# main.py

# GeneratedImage status: init -> processing -> finish
#                                           -> failed
# 一个轮询程序，
# 1） 从generated_image表中 读取当前所有status为processing的imgae， 如果运行时间超时（计算逻辑为当前时间减去create_time 超过3分钟），设为failed
# 2） 如果当前总计processing的image数量小于2，再读取一个status为init的GenerateImage，并把status设为processing，同时调用PassPromptToSelfBot，以启动discord mj 生成图片
# 3） 休息10秒
def get_processing_images():
    return GeneratedImage.query.filter(GeneratedImage.status == 'processing').all()

def get_init_image():
    return GeneratedImage.query.filter(GeneratedImage.status == 'init').first()

def set_image_failed(image):
    image.status = 'failed'
    db.session.commit()

def set_image_processing(image):
    image.status = 'processing'
    db.session.commit()


def main():
    while True:
        processing_images = get_processing_images()

        for image in processing_images:
            if datetime.utcnow() - image.create_time > timedelta(minutes=3):
                set_image_failed(image)

        if len(processing_images) < 2:
            init_image = get_init_image()
            if init_image:
                set_image_processing(init_image)
                base_img_key = models.Source.query.filter(models.Source.source_id == init_image.source_id).first().base_img_key
                PassPromptToSelfBot(utils.get_signed_url(base_img_key) + ' ' + init_image.prompt)

        time.sleep(10)

if __name__ == "__main__":
    main()
