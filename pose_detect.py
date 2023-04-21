import cv2
import mediapipe as mp
import numpy as np
import PIL
import logging
import typing
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_pose = mp.solutions.pose


# Define the OpenPose colors
OPENPOSE_COLORS = [
    (255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0),
    (85, 255, 0), (0, 255, 0), (0, 255, 85), (0, 255, 170), (0, 255, 255),
    (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255), (170, 0, 255),
    (255, 0, 255), (255, 0, 170), (255, 0, 85)
]

# Define the OpenPose connections
OPENPOSE_CONNECTIONS = [
    (0, 1), (0, 2), (3, 1), (4, 2)
]

# Keypoints: [nose, left eye, right eye, left ear, right ear]
keypoints = [
    (100, 100),
    (90, 90),
    (110, 90),
    (80, 80),
    (120, 80)
]

def draw_openpose(img, keypoints, connections, point_radius=4, line_thickness=2):
    img_copy = img.copy()
    
    # Draw the connections
    for idx, connection in enumerate(connections):
        start_point, end_point = connection
        if keypoints[start_point] is not None and keypoints[end_point] is not None:
            x1, y1 = int(keypoints[start_point][0]), int(keypoints[start_point][1])
            x2, y2 = int(keypoints[end_point][0]), int(keypoints[end_point][1])
            cv2.line(img_copy, (x1, y1), (x2, y2), OPENPOSE_COLORS[idx % len(OPENPOSE_COLORS)], line_thickness)
    
    # Draw the keypoints
    for point in keypoints:
        x, y = int(point[0]), int(point[1])
        cv2.circle(img_copy, (x, y), point_radius, (255, 255, 255), -1)
    
    return img_copy


if __name__ == "__main__":
  # For static images:
  IMAGE_FILES = ["d:/sd/pipeline/tmp/00001-2560827185.png"]
  BG_COLOR = (192, 192, 192) # gray
  with mp_pose.Pose(
      static_image_mode=True,
      model_complexity=2,
      smooth_landmarks=True,
      enable_segmentation=True,
      min_detection_confidence=0.5) as pose:
    for idx, file in enumerate(IMAGE_FILES):
      image = cv2.imread(file)
      image_height, image_width, _ = image.shape
      # Convert the BGR image to RGB before processing.
      results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

      if not results.pose_landmarks:
        continue
      keypoints = [
        (results.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE.value].x,
         results.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE.value].y),
        (results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_EYE.value].x,
         results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_EYE.value].y),
        (results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_EYE.value].x,
         results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_EYE.value].y),
        (results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_EAR.value].x,
         results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_EAR.value].y),
        (results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_EAR.value].x,
         results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_EAR.value].y)
      ]
      keypoints = [(int(x * image_width), int(y * image_height)) for x, y in keypoints]

      annotated_image = image.copy()
      
      # Draw pose landmarks in OpenPost style
      image_with_keypoints = draw_openpose(image, keypoints, OPENPOSE_CONNECTIONS)

      cv2.imwrite('d:/sd/pipeline/tmp/annotated_image' + str(idx) + '.png', image_with_keypoints)
      
      # draw openpose on black canvas
      canvas = np.zeros((image_height, image_width, 3), dtype=np.uint8)
      canvas = draw_openpose(canvas, keypoints, OPENPOSE_CONNECTIONS)
      cv2.imwrite('d:/sd/pipeline/tmp/annotated_image_canvas' + str(idx) + '.png', canvas)


def crop_image(image: np.ndarray, landmark_points, enlarge=1.2) -> typing.Tuple[np.ndarray, typing.Tuple[int, int, int, int]]:
    x_coords, y_coords = zip(*landmark_points)
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)

    x_min_px, x_max_px = x_min, x_max
    y_min_px, y_max_px = y_min, y_max

    # Convert coordinates to pixels
    image_height, image_width, _ = image.shape

    # Enlarge the bounding box by 30% and make it square
    bb_width, bb_height = x_max_px - x_min_px, y_max_px - y_min_px

    # Adjust the bounding box coordinates to make it square
    bb_size = int(max(bb_width, bb_height) * enlarge)
    bb_center_x, bb_center_y = int(x_min_px + x_max_px) // 2, int(y_min_px + y_max_px) // 2
    x_min_sq, x_max_sq = bb_center_x - bb_size // 2, bb_center_x + bb_size // 2
    y_min_sq, y_max_sq = bb_center_y - bb_size // 2, bb_center_y + bb_size // 2

    # Pad the image if the bounding box is beyond the image boundaries
    pad_top, pad_bottom, pad_left, pad_right = 0, 0, 0, 0
    if x_min_sq < 0:
        pad_left = abs(x_min_sq)
        x_max_sq += abs(x_min_sq)
        x_min_sq = 0
    if x_max_sq > image_width:
        pad_right = x_max_sq - image_width
    if y_min_sq < 0:
        pad_top = abs(y_min_sq)
        y_max_sq += abs(y_min_sq)
        y_min_sq = 0
    if y_max_sq > image_height:
        pad_bottom = y_max_sq - image_height

    image = cv2.copyMakeBorder(image, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_CONSTANT, value=(255, 255, 255, 255))

    # Crop the image to the bounding box
    image = image[y_min_sq:y_max_sq, x_min_sq:x_max_sq]
    # Return the cropped image and bounding box coordinates
    # Return BB without padding. -25px possible.
    bb = (x_min_sq - pad_left, y_min_sq - pad_top, (x_max_sq - x_min_sq), (y_max_sq - y_min_sq))
    logging.debug(f"bounding box: (x_min, x_max), (y_min, y_max) = (({x_min_sq}, {x_max_sq}), ({y_min_sq}, {y_max_sq}))")
    logging.debug(f"Width and height: {x_max_sq - x_min_sq}, {y_max_sq - y_min_sq}")
    
    return image, bb


def crop_upper_body_img(image: PIL.Image, enlarge=1.2):
  with mp_pose.Pose(
      static_image_mode=True,
      model_complexity=2,
      smooth_landmarks=True,
      enable_segmentation=True,
      min_detection_confidence=0.5) as pose:
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Get pose landmarks
    pose_landmarks = pose.process(image_rgb)
    if not pose_landmarks.pose_landmarks:
       return None
    upper_body_landmarks = [0, 1, 2, 3, 4, 5, 6, 11, 12]  # Landmark indices for upper body
    upper_body_coords = [(landmark.x * image.shape[1], landmark.y * image.shape[0]) for i, landmark in enumerate(pose_landmarks.pose_landmarks.landmark) if i in upper_body_landmarks and landmark.visibility > 0.5]

    if upper_body_coords:
        # Crop the image to the bounding box
        image, bb = crop_image(image, upper_body_coords, enlarge=enlarge)

    return image, bb
