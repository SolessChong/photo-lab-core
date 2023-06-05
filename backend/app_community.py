from backend import config
from backend import bd_conversion_utils
from urllib.parse import urlparse, parse_qs

from datetime import datetime
import json
from flask import Flask, request, jsonify, render_template
from celery import group, Celery, chain, chord
import logging
import requests
from .config import wait_status
from sqlalchemy import Table, select, and_, desc
from sqlalchemy.orm import joinedload, aliased
from collections import defaultdict

from backend.extensions import  app, db
from backend.models import *
from backend import utils
from datetime import datetime
from flask import jsonify, request
from flask import Blueprint

app_community = Blueprint('app_community', __name__)

@app.route('/api/upload_note', methods=['POST'])
def upload_note():
    '''
    upload note
    images: [{'img_key': 'xxx', 'height': 100, 'width': 100}]
    '''
    data = request.get_json()

    name = data.get('name')
    user_id = data.get('user_id')
    images = data.get('images')
    text = data.get('text')
    rate = data.get('rate')

    note = Note(name=name, user_id=user_id, images=images, text=text, rate=rate)
    db.session.add(note)
    db.session.commit()

    # relay img to oss
    for image in images:
        data = utils.oss_source_get(image['img_key'])
        utils.oss_put(image['img_key'], data)

    response = {
        'code': 0,
        'msg': 'success',
        'data': note.to_dict()
    }

    return jsonify(response), 201


@app.route('/api/get_all_notes', methods=['GET'])
def get_all_notes():
    '''
    get all notes
    response_data: [{'id': 1, 'name': 'xxx', 'user_id': 'xxx', 'images': [{'img_key': 'xxx', 'img_url': 'http://xxx', 'height': 100, 'width': 100}], 'text': 'xxx', 'rate': 5, 'create_time': 'xxx'}]
    '''
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    rate = int(request.args.get('rate', 5))
    sort_type = request.args.get('sort_type', 'create_time')
    logging.info(f'page: {page}, per_page: {per_page}, rate: {rate}, sort_type: {sort_type}')

    if sort_type == 'rate':
        sort_field = Note.rate
    elif sort_type == 'create_time':
        sort_field = Note.create_time
    else:
        return jsonify({'error': 'Invalid sort_type'}), 400

    # return empty list if wrong page number
    # filter by Note.rate > rate
    notes = Note.query.filter(Note.rate >= rate).order_by(sort_field.desc()).paginate(page=page, per_page=per_page, error_out=False)

    note_data = [note.to_dict() for note in notes.items]
    response_data = []
    for note in note_data:
        for image in note['images']:
            img_url = utils.get_signed_url(image['img_key'])
            image['img_url'] = img_url
        response_data.append(note)

    response = {
        'code': 0,
        'msg': 'success',
        'data': response_data,
    }
    return jsonify(response)


@app.route('/api/add_note_from_task', methods=['POST'])
def add_note_from_task():
    data = request.get_json()
    task_id = data.get('task_id')

    # Retrieve the task and its result image
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    result_image = task.result_img_key

    img_url = utils.get_signed_url(result_image)
    [h, w] = utils.get_image_size(img_url)
    images_data = [{'img_key': task.result_img_key, 'height': h, 'width': w}]

    # Create a new note with the result image and other fields blank
    note = Note(images=images_data, name='', user_id=task.user_id, scene_id=task.scene_id, text='', rate=None)
    db.session.add(note)
    db.session.commit()

    response = {
        'code': 0,
        'msg': 'success',
        'data': note.to_dict()
    }

    return jsonify(response), 201

@app.route('/api/update_note_rate', methods=['POST'])
def update_note_rate():
    note_id = request.form.get('note_id')
    new_rate = request.form.get('new_rate')

    note = Note.query.get(note_id)
    if note is None:
        return jsonify({'error': 'Note not found'}), 404

    note.rate = new_rate
    db.session.commit()

    return jsonify({'success': True}), 200
