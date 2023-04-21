import cv2
import numpy as np
import os
import insightface
from insightface.app import FaceAnalysis
from insightface.data import get_image as ins_get_image

if __name__ == '__main__':
    # points definition: https://github.com/nttstar/insightface-resources/blob/master/alignment/images/2d106markup.jpg
    app = FaceAnalysis(allowed_modules=['detection', 'landmark_2d_106'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    # Read the image
    for fn in os.listdir("D:\\sd\\pipeline\\data\\base_img\\qsmx"):
        img = cv2.imread(os.path.join("D:\\sd\\pipeline\\data\\base_img\\qsmx", fn))
        faces = app.get(img)
        tim = img.copy()
        color = (200, 160, 75)
        for face in faces:
            lmk = face.landmark_2d_106
            lmk = np.round(lmk).astype(np.int)
            for i in range(lmk.shape[0]):
                p = tuple(lmk[i])
                cv2.circle(tim, p, 1, color, 1, cv2.LINE_AA)
        cv2.imwrite('./test_out.jpg', tim)

    cv2.imwrite('output_mask.jpg', mask_out)