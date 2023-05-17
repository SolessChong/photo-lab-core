import unittest
from backend import models
from backend.extensions import app, db
from core import set_up_scene


class TestSetUpScene(unittest.TestCase):
    def setUp(self) -> None:
        app.app_context().push()
        self.scene = models.Scene.query.get(6914)
        return super().setUp()
    
    def test_set_up_scene(self):
        set_up_scene.prepare_scene(self.scene.scene_id)
        self.assertTrue(self.scene.hint_img_list is not None)
        self.assertTrue(len(self.scene.roi_list) > 0)