import os
import time
import datetime
import unittest
import requests
import json
from backend import app
from backend import extensions
from backend.models import db, Payment, Pack
from backend import models

class AppTest(unittest.TestCase):
    def setUp(self):
        self.app = app.app
        self.client = requests.Session()
        
    def tearDown(self):
        pass  # Add code here to delete test data in database if necessary

    def test_upload_payment(self):
        # Read the test data from a JSON file, relative path
        with open(os.path.join(os.path.dirname(__file__), 'data/payment2.json')) as f:
            test_data = json.load(f)
        test_data['subscribe_until'] = int(time.time()) + 3600 * 24 * 30
        response = self.client.post('http://photolab.aichatjarvis.com/api/upload_payment', json=test_data)
        self.assertEqual(response.status_code, 200)

        # Check the response message
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['msg'], "Payment successful and pack unlocked")
        self.assertEqual(data['code'], 0)

        # Verify the payment is recorded in the database
        extensions.app.app_context().push()
        payment = Payment.query.filter_by(user_id=test_data['user_id'], product_id=test_data['product_id']).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.payment_amount, test_data['payment_amount'])

        # Verify the pack status is updated
        pack = Pack.query.get(test_data['pack_id'])
        self.assertIsNotNone(pack)
        self.assertEqual(pack.is_unlock, 1)
        self.assertTrue(pack.unlock_num > int(test_data['unlock_num']))

        # Remove the test data from the database
        db.session.delete(payment)
        db.session.commit()


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

    """
    @app.route('/api/contact', methods=['POST'])
    def submit_contact_form():
        name = request.form.get('name')
        phone = request.form.get('phone')
        wechat = request.form.get('wechat')
        message = request.form.get('message')
    """
    def test_submit_contact_form(self):
        # query with get params: user_id: Dt47AzFi73
        response = self.client.post('http://photolab.aichatjarvis.com/api/contact', data={'name': 'test_name', 'user_id': 'test_user_id', 'phone': 'test_phone', 'wechat': 'test_wechat', 'message': 'test_msg'})
        # assert response content can be parsed as a dict (json)
        self.assertTrue(isinstance(response.json(), dict))
        self.assertEqual(response.status_code, 200)

    def test_promo_code(self):
        user_id = 'test_promo_code_user_id'
        code = 'test_promo_code'
        # populate test data
        extensions.app.app_context().push()
        user = models.User.query.filter_by(user_id=user_id).first()
        promo_code = models.PromoCode.query.filter_by(code=code).first()
        if user:
            db.session.delete(user)
        if promo_code:
            db.session.delete(promo_code)
        db.session.commit()
        user = models.User(user_id=user_id)
        db.session.add(user)
        promo_code = models.PromoCode(code=code, type=models.PromoCode.Type.subscribe_week, expire_time=datetime.datetime.now() + datetime.timedelta(days=7))
        db.session.add(promo_code)
        db.session.commit()

        # Test web request
        response = self.client.post('http://photolab.aichatjarvis.com/api/use_promo_code', json={'user_id': user_id, 'code': code})
        # assert response content can be parsed as a dict (json)
        self.assertTrue(isinstance(response.json(), dict))
        self.assertEqual(response.status_code, 200)
        # assert user's subscribe_until is updated
        user = models.User.query.filter_by(user_id=user_id).first()
        self.assertTrue(user.subscribe_until > datetime.datetime.now())

        # Use again and will return invalid code error
        response = self.client.post('http://photolab.aichatjarvis.com/api/use_promo_code', json={'user_id': user_id, 'code': code})
        self.assertTrue(isinstance(response.json(), dict))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 1)
        self.assertEqual(response.json()['msg'], 'error')
        self.assertEqual(response.json()['data']['message'], 'Invalid code')

        # delete test data
        db.session.delete(user)
        db.session.delete(promo_code)
        db.session.commit()
        

if __name__ == '__main__':
    unittest.main()
