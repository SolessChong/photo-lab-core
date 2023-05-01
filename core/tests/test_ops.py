import unittest
from backend import models
from backend.extensions import app, db
from core import render
from core.resource_manager import *
from core.ops import remove_logo

from core.ops import *

class TestOps(unittest.TestCase):
    def setUp(self) -> None:
        app.app_context().push()
        return super().setUp()
    
    def test_remove_logo(self):
        scene = models.Scene.query.get(3579)
        img = read_PILimg(ResourceMgr.get_resource_oss_url(ResourceType.BASE_IMG, scene.scene_id))
        img_rst = remove_logo.remove_logo_from_image(img, 3, length=1200)
        img_rst.save('test_remove_logo.png')
        self.assertTrue(img_rst is not None)
