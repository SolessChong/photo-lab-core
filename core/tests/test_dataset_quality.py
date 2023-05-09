import unittest
from backend import models
from backend.extensions import app, db
from core import dataset_quality

class TestDatasetQuality(unittest.TestCase):
    def setUp(self) -> None:
        app.app_context().push()
        return super().setUp()
    
    def test_dataset_quality(self):
        # test analyze_person
        person_id = 140
        report, comment = dataset_quality.analyze_person(person_id)
        self.assertTrue(report is not None and comment is not None) 