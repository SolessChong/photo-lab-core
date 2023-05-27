import os
import unittest
import json
from backend import app
from backend.models import db, Payment, Pack

class AppTest(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

        # Read the test data from a JSON file, relative path
        with open(os.path.join(os.path.dirname(__file__), 'data/payment.json')) as f:
            self.test_data = json.load(f)


    def tearDown(self):
        pass  # Add code here to delete test data in database if necessary

    def test_upload_payment(self):
        response = self.client.get('/api/upload_payment', query_string=self.test_data)
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

if __name__ == '__main__':
    unittest.main()
