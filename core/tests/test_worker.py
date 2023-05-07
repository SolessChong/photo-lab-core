import unittest
from backend import models
from backend.extensions import app, db
from core.worker import *


class TestWorker(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        app.app_context().push()

    def test_worker_train(self):
        person_id = 6
        sources = models.Source.query.filter_by(person_id=person_id).all()
        task_train_lora(6, [source.base_img_key for source in sources])
        self.assertTrue(True)