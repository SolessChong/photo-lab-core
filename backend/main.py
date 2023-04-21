import requests
import utils
from io import BytesIO
from utils import(create_db_conn, create_oss_client, get_db_scenes, get_signed_url, get_bucket, oss_put, download_image)


if __name__ == "__main__":
    source_image = download_image(get_signed_url("scenes/微信图片_20230405094331.jpg"))
    target_image = download_image(get_signed_url("scenes/192323.png"))
    modify_image = download_image(get_signed_url("scenes/192323.png"))

    result = utils.akool_reface(source_image, target_image, modify_image)

    # if source_image and target_image and modify_image:
        # result = upload_files(your_url, your_token, source_image, target_image, modify_image)
