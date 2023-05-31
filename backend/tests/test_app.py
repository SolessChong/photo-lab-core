import os
import unittest
import requests
import json
from backend import app
from backend.models import db, Payment, Pack

class AppTest(unittest.TestCase):
    def setUp(self):
        self.app = app.app
        self.client = requests.Session()
        
    def tearDown(self):
        pass  # Add code here to delete test data in database if necessary

    def test_upload_payment(self):
        return
        # Read the test data from a JSON file, relative path
        with open(os.path.join(os.path.dirname(__file__), 'data/payment.json')) as f:
            test_data = json.load(f)
        response = self.client.get('http://photolab.aichatjarvis.com/api/upload_payment', query_string=test_data)
        self.assertEqual(response.status_code, 200)

        # Check the response message
        data = json.loads(response.data)
        self.assertEqual(data['msg'], "Payment successful and pack unlocked")
        self.assertEqual(data['code'], 0)

        # Verify the payment is recorded in the database
        payment = Payment.query.filter_by(user_id=self.test_data['user_id']).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.payment_amount, self.test_data['payment_amount'])

        # Verify the pack status is updated
        pack = Pack.query.get(self.test_data['pack_id'])
        self.assertIsNotNone(pack)
        self.assertEqual(pack.is_unlock, 1)
        self.assertEqual(pack.unlock_num, self.test_data['unlock_num'])

    def test_global_config(self):
        response = self.client.get('http://photolab.aichatjarvis.com/api/global_config')
        # assert response content can be parsed as a dict (json)
        self.assertTrue(isinstance(response.json(), dict))
        self.assertEqual(response.status_code, 200)

    def test_get_example_2(self):
        response = self.client.get('http://photolab.aichatjarvis.com/api/get_example_2')
        # assert response content can be parsed as a dict (json)
        self.assertTrue(isinstance(response.json(), dict))
        self.assertEqual(response.status_code, 200)

    def test_get_generated_images(self):
        # query with get params: user_id: Dt47AzFi73
        response = self.client.get('http://photolab.aichatjarvis.com/api/get_generated_images' + '?user_id=Dt47AzFi73')
        # assert response content can be parsed as a dict (json)
        self.assertTrue(isinstance(response.json(), dict))
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
