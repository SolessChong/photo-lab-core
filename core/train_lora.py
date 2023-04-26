# use PIL to import images in the folder
from PIL import Image
import os
import rembg
import cv2
import subprocess
import logging
from core import conf
import re
import math
import shutil
from pathlib import Path
from core import face_mask
from core import pose_detect
from core.resource_manager import ResourceMgr, ResourceType

import sys
import io

# read command line arguments
import argparse
parser = argparse.ArgumentParser(
    prog="train lora", 
    description="train lora model"
)
parser.add_argument("dataset_path", help="path to the folder containing the dataset")
parser.add_argument("subject_name", help="subject name")
parser.add_argument("class_name", help="subject id")

# parse cli arguments


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# function to crop 512 image according to face location, and remove background
def detect_subject_and_crop(dataset_path, size=512, remove_bg=True, enlarge=1.2):
    img_raw_path = Path(dataset_path) / "img_raw"
    img_train_path = Path(dataset_path) / "img_train"
    img_list = os.listdir(img_raw_path)

    # clear folder if already exists
    if os.path.exists(img_train_path):
        shutil.rmtree(img_train_path)        
    os.makedirs(img_train_path)

    # log the number of images
    logging.info(f"number of images: {len(img_list)}")

    # # iterate over the list
    for img_fn in img_list:
        try:
            logging.debug(f"processing image: {img_fn}")
            image = cv2.imread(str(Path(img_raw_path) / img_fn))
            
            # use face to crop, HAAR cascade. Poor
            # subj_img = face_mask.crop_face_img(image, enlarge=enlarge)
            # use pose estimation by MediaPipe. Better
            if image is None:
                continue
            subj_img, _ = pose_detect.crop_upper_body_img(image, enlarge=enlarge)
            if subj_img is None:
                continue

            # remove background using rembg
            if remove_bg:
                subj_img = rembg.remove(subj_img, bgcolor=(255, 255, 255, 255))

            subj_img = cv2.resize(subj_img, (size, size), interpolation=cv2.INTER_LANCZOS4)
            # save image
            cv2.imwrite(str(Path(img_train_path) / img_fn), subj_img)
        except Exception as e:
            logging.error(f"error processing image: {img_fn}")

    return len(img_list)

# function calling BLIP 
def captioning(img_path, remove_bg=True):
    # Change dir to train_utils
    os.chdir(conf.TRAIN_UTILS_ROOT)

    # Path to the Python executable inside the virtual environment
    venv_python_executable = os.path.join(conf.TRAIN_UTILS_ROOT, "venv/bin/python")

    # Path to the Python script you want to run
    #   join conf.TRAIN_UTILS_ROOT to the path
    script_to_run = os.path.join(conf.TRAIN_UTILS_ROOT, "finetune/make_captions.py")

    # Define the arguments you want to pass to the script
    arguments = [
        "--batch_size", "4",
        "--num_beams", "1",
        "--top_p", "0.9",
        "--max_length", "75",
        "--min_length", "5",
        "--beam_search",
        "--caption_extension", ".txt",
        str(img_path),
        "--caption_weights", "https://storage.googleapis.com/sfr-vision-language-research/BLIP/models/model_large_caption.pth"
    ]

    logging.info("captioning image: " + str(img_path))
    # Run the script using the Python executable from the virtual environment and pass the arguments
    with open('my-stdout.txt', 'w') as fp: 
        subprocess.run(
            ' '.join([venv_python_executable, script_to_run] + arguments), 
            stdout=fp, stderr=fp, 
            shell=True, text=True, encoding='utf-8', 
        )

    # Replace subject name
    # Get all files ending in ".txt"
    txt_files = [f for f in os.listdir(img_path) if f.endswith(".txt")]
    for txt_file in txt_files:
        # Read the file
        with open(os.path.join(img_path, txt_file), "r") as f:
            txt = f.read()
        # Replace subject name
        # Create a regular expression pattern to match the phrases
        pattern = r'\b(?:a woman|a man|a girl|a boy)\b'

        # Replace the matched phrases with "MA_TRAINING_SUBJECT"
        processed_text = re.sub(pattern, f"a close-up photo of {conf.SUBJECT_PLACEHOLDER} person", txt)
        if remove_bg:
            processed_text =  processed_text + ", pure white background"

        # Write the file
        with open(os.path.join(img_path, txt_file), "w") as f:
            f.write(processed_text)

# function training LORA model
def train_lora(dataset_path, subject_name, class_name, epoch=5):
    # Change dir to train_utils
    os.chdir(conf.TRAIN_UTILS_ROOT)

    model_path = os.path.join(dataset_path, "model_lora")
    # rm dir if exists
    if os.path.exists(model_path):
        shutil.rmtree(model_path)
    os.mkdir(model_path)

    # TODO: optimize this step. Too ugly
    # Copy dataset into folder naming format required by training script
    img_count = len([f for f in os.listdir(os.path.join(dataset_path, "img_train")) if f.endswith(".txt")])
    repeats = math.floor(2500 / img_count)
    logging.info(f"{img_count} images found. Repeating dataset {repeats} times.")
    # remove tree if exists
    if os.path.exists(Path(dataset_path) /  f"img_train_n"):
        shutil.rmtree(Path(dataset_path) /  f"img_train_n")
    shutil.copytree(
        Path(dataset_path) /  "img_train",
        Path(dataset_path) / f"img_train_n/{repeats}_{conf.SUBJECT_PLACEHOLDER} {class_name}/"
    )

    print(os.path.join(conf.TRAIN_UTILS_ROOT, "venv/bin/accelerate"))

    # 2500 images with repeat
    cmd = f"""{os.path.join(conf.TRAIN_UTILS_ROOT, "venv/bin/accelerate")} \
        launch \
        --num_cpu_threads_per_process=2 \
        "{Path(conf.TRAIN_UTILS_ROOT) / "train_network.py"}" --enable_bucket \
        --pretrained_model_name_or_path={conf.MODEL_RESOURCES['CM.ST']} \
        --train_data_dir="{Path(dataset_path) / "img_train_n"}" \
        --reg_data_dir={conf.DATA_RESOURCES['REG.WOMEN']} \
        --resolution=512,512 \
        --output_dir="{Path(dataset_path) /  "model_lora"}" \
        --logging_dir="{Path(dataset_path) / "log"}" --network_alpha="256" \
        --save_model_as=safetensors \
        --network_module=networks.lora \
        --text_encoder_lr=5e-5 --unet_lr=0.0001 --network_dim=256 \
        --output_name="{subject_name}" \
        --lr_scheduler_num_cycles="10" --learning_rate="0.001" --lr_scheduler="cosine" \
        --lr_warmup_steps="70" --train_batch_size="12" \
        --max_train_epochs="{epoch}" \
        --save_every_n_epochs="1" --mixed_precision="fp16" --save_precision="fp16" \
        --optimizer_type="AdamW8bit" --max_data_loader_n_workers="0" --bucket_reso_steps=64 \
        --xformers --bucket_no_upscale --random_crop \
        > {Path(dataset_path) / "train.log"} 2>&1
        """
        # --max_train_steps="2"
        # > {os.path.join(dataset_path, "train.log")} 2>&1
        # --reg_data_dir={conf.DATA_RESOURCES['REG.WOMEN']} \
    print(cmd)

    os.environ['PYTHONIOENCODING'] =  'utf-8'
    subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
            shell=True, text=True, encoding='utf-8', 
    )

    
    # Copy model to model folder
    shutil.copyfile(
        str(Path(dataset_path) / "model_lora" / (str(subject_name) + ".safetensors")),
        ResourceMgr.get_resource_local_path(ResourceType.LORA_MODEL, subject_name)
    )
    logging.info("--- LORA model training finished")

# main function
def main():
    args = parser.parse_args()
    ## Flags
    remove_bg = True
    enlarge_face = 2
    ## 1. Prepare dataset
    #
    # Dir structure:
    #   - dataset_path
    #       - img_raw: png files as input
    #       - img_train: auto created
    #       - model_lora: auto created
    img_raw_path = Path(args.dataset_path) / "img_raw"
    img_train_path = Path(args.dataset_path) / "img_train"

    # read img list from img_path
    detect_subject_and_crop(args.dataset_path, remove_bg=remove_bg, enlarge=enlarge_face)

    ## 2. Captioning
    #
    logging.info("=== start captioning")
    captioning(img_train_path,  remove_bg=remove_bg)

    ## 3. Train LORA model
    #
    logging.info("=== start training LORA model")
    train_lora(args.dataset_path, conf.SUBJECT_PLACEHOLDER, 'girl')

# main program
if __name__ == "__main__":
    main()