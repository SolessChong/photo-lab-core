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
        image = Image.open(os.path.join(os.path.dirname(__file__), 'dataset/1.png'))
        rst = get_face_mask(image)
        self.assertTrue(rst is not None)
        pass