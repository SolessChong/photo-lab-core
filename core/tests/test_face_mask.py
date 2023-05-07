import unittest
from PIL import Image
from backend import models
from backend.extensions import app, db
from core import render
from core.resource_manager import *
from core.face_mask import *

class TestOps(unittest.TestCase):
    def setUp(self) -> None:
        app.app_context().push()
        return super().setUp()
    
    def test_face_mask(self):
        rst = face_analysis.get( pil_to_cv2(Image.open('photo-lab-core/core/tests/dataset/1.png')))
        self.assertTrue(len(rst) > 0)