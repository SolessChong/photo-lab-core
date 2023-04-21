import cv2
from mtcnn import MTCNN
import matplotlib.pyplot as plt
import os

from retinaface import RetinaFace

# Initialize the MTCNN model
mtcnn = MTCNN()

# Read the image
for fn in os.listdir("D:\\sd\\pipeline\\data\\base_img\\qsmx"):
    image = cv2.imread(os.path.join("D:\\sd\\pipeline\\data\\base_img\\qsmx", fn))
    resp = RetinaFace.detect_faces(image)

    print(resp)