from PIL import Image
import os

# specify the path where your images are located
path = "D:\\sd\\pipeline\\data\\base_img\\13\\"

# loop through all files in the path directory
for filename in os.listdir(path):
    # check if the file is an image
    if filename.endswith(".jpg") or filename.endswith(".jpeg"):
        # open the image using PIL
        with Image.open(os.path.join(path, filename)) as im:
            # convert the image to PNG and save it
            im.save(os.path.join(path, os.path.splitext(filename)[0] + ".png"))
        os.remove(os.path.join(path, filename))