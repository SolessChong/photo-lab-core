from datetime import datetime
import json
from flask import Flask, request, jsonify, render_template
import secrets
import random
import string
from celery import group, Celery, chain, chord
import logging
import argparse

from backend.extensions import  app, db
from . import aliyun_face_detector
from . import web_function
from . import utils
from . import models
from . import selector_other


logger = logging.getLogger(__name__)


# 用于接受来自头条的点击数据
@app.route('/util/bd_click', methods=['GET'])
def bd_click():
    print(request.args)
    promotionid = request.args.get('promotionid', None)
    mid1 = request.args.get('mid1', None)
    idfa = request.args.get('idfa', None)
    mac = request.args.get('mac', None)
    os = request.args.get('os', None)
    timestamp = request.args.get('TIMESTAMP', None)
    callback = request.args.get('callbackUrl', None)
    ip = request.args.get('ip', None)
    ua = request.args.get('ua', None)

    if callback and ip:
        new_click = models.BdClick(
            ip=ip,
            ua=ua,
            callback=callback,
            idfa=idfa
        )

        db.session.add(new_click)
        db.session.commit()
        logging.info('New click saved: {}'.format(new_click))

        response = {
            'status': 'success',
            'message': 'Click data saved successfully.'
        }
        return jsonify(response), 200
    else:
        logging.error('Missing required parameters.')
        response = {
            'status': 'error',
            'message': 'Missing required parameters.'
        }
        return jsonify(response), 400

if __name__ == '__main__':
    # Add argument parser: -p: port
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=8000, help='port to listen on')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port, ssl_context=('photolab.aichatjarvis.com.pem', 'photolab.aichatjarvis.com.key'))
