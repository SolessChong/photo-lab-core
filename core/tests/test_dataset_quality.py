import unittest
from backend import models
from backend.extensions import app, db
from core import dataset_quality

class TestDatasetQuality(unittest.TestCase):
    def setUp(self) -> None:
        app.app_context().push()
        return super().setUp()
    
    """
    Example output:

    report:

    {'num_score': 0.48, 'background_variety': 0.7605350748697917, 'face_pose_variety': 1.6519066737248347, 'jpeg_compression': 0.6788361425408058, 'blurriness': 0.7557867511400702, 'lighting': 0.31394730673895943}
    
    comment:

    You have not uploaded enough photos.:
    - Upload at least 20 photos.
    - Try to take photos in different settings and environments.
    - Vary the settings and environments for your photos.
    - Use different props or decorations to add variety to the background.
    """
    def test_dataset_quality(self):
        # test analyze_person
        person_id = 299
        report, comment = dataset_quality.analyze_person(person_id)
        self.assertTrue(report is not None and comment is not None) 
