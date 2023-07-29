import hashlib
import json
import argparse
import requests
import time
import logging
from . import models
from backend.models import *
from backend.extensions import app, db
from backend import config

def create_friend(open_id, friend_open_id):
    if open_id == friend_open_id:
        logging.info(f'open_id 等于friend_open_id')
        return
    friend = models.Friends.query.filter_by(open_id = open_id, friend_open_id= friend_open_id).first()
    if not friend:
        new_friend = models.Friends(open_id=open_id, friend_open_id = friend_open_id)
        db.session.add(new_friend)
        db.session.commit()
    your_friend = models.Friends.query.filter_by(open_id = friend_open_id, friend_open_id = open_id).first()
    if not your_friend:
        new_your_friend = models.Friends(open_id=friend_open_id, friend_open_id = open_id)
        db.session.add(new_your_friend)
        db.session.commit()