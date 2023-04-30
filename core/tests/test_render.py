import unittest
from backend import models
from backend.extensions import app, db
from core import render


class TestRender(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        app.app_context().push()

    def test_render(self):
        self.test_render_lora_on_prompt()

    def test_render_lora_on_prompt(self):
        self.scene = models.Scene(
            prompt="3d render, cgi, symetrical, octane render, 35mm, intricate details, hdr, intricate details, hyperdetailed, natural skin texture, hyperrealism, sharp,a girl , portrait, looking up, solo, (full body:0.6), detailed background, brown eyes, light blonde textured hair, detailed face, robin hood, dynamic pose, medieval fantasy setting, high fantasy, green leather clothes, capelet, puch, straps, belt, serene forest, bushes, ivy, roots, moss, falling leaves, flowers, birds, feathers, arrows in quiver, crossbow, sunshine, mist,",
            negative_prompt="3d, cartoon, anime, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, bad anatomy, girl, loli, young, large breasts, red eyes, muscular, (cross-eye:1.3), (strange eyes:1.3), easynegative, (more than 5 fingers),",
            action_type="sd",
            img_type="girl",
            model_name="cartoon",
            params={
                'model': 'lyriel_v14 [f1b08b30f8]',
                'sampler_name': 'Euler a',
            },
            collection_name='test_marvel_1',
        )
        db.session.add(self.scene)
        db.session.commit()
        self.task = models.Task(
            person_id_list=[8],
            scene_id=self.scene.scene_id,
        )
        db.session.add(self.task)
        db.session.commit()
        
        rst_img = render.render_lora_on_prompt(self.task)
        self.assertTrue(rst_img is not None)

    def tearDown(self) -> None:
        db.session.delete(self.scene)
        db.session.delete(self.task)
        db.session.commit()
        return super().tearDown()