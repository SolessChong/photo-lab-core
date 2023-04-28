import discord
from discord.ext import commands
import requests
from . import utils
import re
import secrets
discord_token = "MTA5MTc2Mzg4NzQ1MzUwNzcwNA.GfpMQC.5-t04GUh5lz9ptaOFHuEsplPwrY1rkmuOYa1RA"

client = commands.Bot(command_prefix="*", intents=discord.Intents.all())

# directory = os.getcwd()
# def split_image(image_file):
#     with Image.open(image_file) as im:
#         # Get the width and height of the original image
#         width, height = im.size
#         # Calculate the middle points along the horizontal and vertical axes
#         mid_x = width // 2
#         mid_y = height // 2
#         # Split the image into four equal parts
#         top_left = im.crop((0, 0, mid_x, mid_y))
#         top_right = im.crop((mid_x, 0, width, mid_y))
#         bottom_left = im.crop((0, mid_y, mid_x, height))
#         bottom_right = im.crop((mid_x, mid_y, width, height))

#         return top_left, top_right, bottom_left, bottom_right

# async def download_image(url, filename):
#     response = requests.get(url)
#     if response.status_code == 200:

#         # Define the input and output folder paths
#         input_folder = "input"
#         output_folder = "output"

#         # Check if the output folder exists, and create it if necessary
#         if not os.path.exists(output_folder):
#             os.makedirs(output_folder)
#         # Check if the input folder exists, and create it if necessary
#         if not os.path.exists(input_folder):
#             os.makedirs(input_folder)

#         with open(f"{directory}/{input_folder}/{filename}", "wb") as f:
#             f.write(response.content)
#         print(f"Image downloaded: {filename}")

#         input_file = os.path.join(input_folder, filename)

#         if "UPSCALED_" not in filename:
#             file_prefix = os.path.splitext(filename)[0]
#             # Split the image
#             top_left, top_right, bottom_left, bottom_right = split_image(input_file)
#             # Save the output images with dynamic names in the output folder
#             top_left.save(os.path.join(output_folder, file_prefix + "_top_left.jpg"))
#             top_right.save(os.path.join(output_folder, file_prefix + "_top_right.jpg"))
#             bottom_left.save(os.path.join(output_folder, file_prefix + "_bottom_left.jpg"))
#             bottom_right.save(os.path.join(output_folder, file_prefix + "_bottom_right.jpg"))

#         else:
#             os.rename(f"{directory}/{input_folder}/{filename}", f"{directory}/{output_folder}/{filename}")
#         # Delete the input file
#         os.remove(f"{directory}/{input_folder}/{filename}")

def get_match_value(text, pattern):
    if not text:
        return None
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None

@client.event
async def on_ready():
    print("Bot connected")

import Levenshtein
from .extensions import app, db
import logging
from .discord_util import get_processing_images 
# 收到message以后，如果有attachment, 获得所有状态为processing的GeneratedImage
# 然后计算与收到prompt的相似度，更新最像的那GenerateImage
@client.event
async def on_message(message):
    print('content: ', message.content)
    
    prompt = get_match_value(message.content, r'\*\*(.*?)\*\*')
    if not prompt:
        return
    
    prompt = prompt[prompt.find(' ')+1:]

    
    for attachment in message.attachments:
        if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
            response = requests.get(attachment.url)
            img_url = 'mj/' + secrets.token_hex(16) + '.png'
            utils.oss_put(img_url, response.content)
            
            imgs = get_processing_images()
            min_dis = 1e8
            min_img = None
            for img in imgs:
                dis = Levenshtein.distance(img.prompt, prompt) 
                if dis < min_dis:
                    min_dis = dis
                    min_img = img

            if min_img:
                min_img.status = 'finish'
                min_img.img_url = img_url
                db.session.commit()
                logging.info(f'GeneratedImage #{min_img.id} is finished.')

def main():
    app.app_context().push()
    client.run(discord_token)

if __name__ == "__main__":
    main()
