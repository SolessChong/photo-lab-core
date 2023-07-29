from backend import config
import argparse
import time
import base64
import jwt
from backend import bd_conversion_utils
from urllib.parse import urlparse, parse_qs

from datetime import datetime, timedelta
import json
from flask import Flask, request, jsonify, render_template, url_for
import secrets
import random
import string
import hmac
import schedule
import threading
import time

from celery import group, Celery, chain, chord
import logging
import requests
from .config import wait_status
from sqlalchemy import func, Table, select, and_, desc
from sqlalchemy.orm import joinedload, aliased
from collections import defaultdict

from backend.extensions import  app, db
from . import aliyun_face_detector
from . import web_function
from . import utils
from . import models
from . import selector_other, selector_sd

from backend.notification_center import wechat_notify_complete_packs, wechat_notify_pack, send_wechat_notification

from backend.app_community import upload_note, get_all_notes, add_note_from_task, app_community

from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
# from wechatpy.pay import WeChatPay
# from wechatpy.pay.utils import check_signature

celery_app = Celery('myapp',
                    broker='redis://default:Yzkj8888!@r-wz9d9mt4zsofl3s0pn.redis.rds.aliyuncs.com:6379/0',
                    backend='redis://default:Yzkj8888!@r-wz9d9mt4zsofl3s0pn.redis.rds.aliyuncs.com:6379/0')

# Create the tasks as strings
task_train_lora_str = 'train_lora'
task_render_scene_str = 'render_scene'

from aliyunsdkcore.client import AcsClient
from aliyunsdksts.request.v20150401 import AssumeRoleRequest
client = AcsClient(config.OSS_ACCESS_KEY_ID, config.OSS_ACCESS_KEY_SECRET)

logger = logging.getLogger(__name__)

#############################################
## App Modules
#############################################
app.register_blueprint(app_community)


@app.route('/api/create_user', methods=['GET'])
def create_user():
    # Generate a random user_id with 10 characters
    user_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    # wechat login code
    code = request.args.get('code')
    invite_open_id = request.args.get('invite_open_id')

    # call wechat
    url = 'https://api.weixin.qq.com/sns/jscode2session'

    params={
        'appid': config.appid,
        'secret': config.appsecret,
        'js_code': code,
        'grant_type' : 'authorization_code'
    }
    response = requests.get(url, params=params)
    
    data = response.json()

    open_id = data.get('openid')
    error_msg = data.get('errmsg')

    logging.info(f'open_id is {open_id} errmsg={error_msg}')
    tip=''
    # get user by open_id
    if open_id:
        user = models.User.query.filter_by(open_id=open_id).first()
        if user:
            if invite_open_id:
                tip='不是新用户，无法领取邀请奖励'
            logging.info(f'user already exist by open_id={open_id}')
            # Create the response object with the specified format
            response = {
                "code": 0,
                "msg": "create user successfully",
                "data": {
                    "user_id": user.user_id,
                    "min_img_num": user.min_img_num,
                    "max_img_num": user.max_img_num,
                    "pay_group": user.dna.get('pay_group'),
                    "shot_num": 10,
                    "shot_seconds:" : 10,
                    "max_styles" : 1,
                    "diamond": user.diamond,
                    "received" : 0,
                    "open_id": user.open_id,
                    "tip": tip
                }
            }
            # Return the response object as a JSON response
            return jsonify(response)
    
    if 'X-Forwarded-For' in request.headers:
        user_ip = request.headers.getlist("X-Forwarded-For")[0].rpartition(' ')[-1]
    else:
        user_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    # return dummy result tJ0T5BcptE if user_agent contains 1.0.7 or 1.0.8
    if user_agent and ('1.1.4' in user_agent or '1.1.5' in user_agent):
        user_id = 'matTlTd5hz'
        user_ip = ''
        new_user = models.User.query.filter_by(user_id=user_id).first()
        logging.info(f'!!!! Dummy user for test, user_id is {user_id}, ua is {user_agent}')
    else:
        logging.info(f'create new user ip is {user_ip}, ua is {user_agent}')
        # Create a new user with the generated user_id
        pay_rand = random.randint(1, 100)
        if pay_rand < 25:   # 25%
            pay_group = 1
        elif pay_rand < 50: # 25%
            pay_group = 10
        else:               # 50%
            pay_group = 20
        dna = {
            'pay_group': pay_group,
            'pay_in_advance': random.randint(0,100) < 5,
        }
        diamond=config.INIT_DIAMOND
        received=0
        if open_id and invite_open_id and open_id != invite_open_id:
            logger.info(f'open_id not equal, open_id={open_id}, invite_open_id={invite_open_id}')
            # 邀请者
            invite_user = models.User.query.filter_by(open_id=invite_open_id).first()
            if invite_user:
                logger.info(f'invite exist, invite success')
                diamond = diamond+config.INVITED_ADD_DIAMOND
                received=1
                invite_user.diamond = invite_user.diamond + config.INVITED_ADD_DIAMOND
                new_invire_record=models.InviteRecord(open_id= open_id, invite_open_id = invite_open_id)
                tip='领取奖励成功'
                db.session.add(new_invire_record)
            else:
                tip='邀请者不存在，无法领取奖励'
        new_user = models.User(user_id=user_id, ip = user_ip, ua = user_agent, group = config.user_group, min_img_num = config.min_image_num, max_img_num = 50, dna=dna, diamond=diamond, open_id=open_id)

    # Add the new user to the database and commit the changes
    db.session.add(new_user)
    db.session.commit()

    # send active request to toutiao
    click = models.BdClick.query.filter(models.BdClick.ip == user_ip, models.BdClick.con_status==0).order_by(models.BdClick.id.desc()).first()
    if click:
        try:
            requests.get(click.callback)
            click.con_status = 1
            click.user_id = user_id
            db.session.add(click)
            db.session.commit()
            logging.info(f'update click {click.id} to user {user_id}')
        except Exception as e:
            logging.error(f'update click {click.id} to user {user_id} error: {e}')
    else:
        logging.error(f'no click for ip {user_ip}')


    # Create the response object with the specified format
    response = {
        "code": 0,
        "msg": "create user successfully",
        "data": {
            "user_id": new_user.user_id,
            "open_id": new_user.open_id,
            "min_img_num": new_user.min_img_num,
            "max_img_num": new_user.max_img_num,
            "pay_group": random.randint(1,3),
            "shot_num": 10,
            "shot_seconds:" : 10,
            "max_styles" : 1,
            "diamond": new_user.diamond,
            "received": received
        }
    }

    # Return the response object as a JSON response
    return jsonify(response)

@app.route('/api/get_order', methods=['GET'])
def get_order():
    order_id = request.args.get('order_id')
    # order_type 1-wechat 2-douyin
    order_type = request.args.get('order_type')
    if not order_id:
        return jsonify({"msg": "order_id is required", "code":-1}), 400
    if not order_type:
        return jsonify({"msg": "order_type is required", "coder": -1}), 400
    wechat_order = models.WechatPayOrder.query.filter_by(order_id=order_id).first()
    if not wechat_order:
        return jsonify({"msg": "order not found", "code": -1}), 400
    state=0
    if wechat_order.state ==2:
        state = 1
    if wechat_order.state ==3:
        state= 1
    response = {
        "data": {
            "state": state
        },
        "msg": "get order successfully",
        "code": 0
    }
    return jsonify(response), 200


@app.route('/api/get_user', methods=['GET'])
def get_user():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    user = models.User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"error": "user not found"}), 404

    persons = models.Person.query.filter_by(user_id=user_id).all()
    
    friend_persons=[]
    friend_open_ids = [record[0] for record in models.InviteRecord.query.filter_by(invite_open_id=user.open_id).with_entities(models.InviteRecord.open_id).all()]
    # invite me user 
    invite_record = models.InviteRecord.query.filter_by(open_id=user.open_id).first()
    if invite_record:
        friend_open_ids.append(invite_record.open_id)
    friend_open_ids= list(set(friend_open_ids))
    
    logging.info(f'friend_open_ids={friend_open_ids}') 
    if friend_open_ids:
        users = models.User.query.filter(models.User.open_id.in_(friend_open_ids)).all()
        if users:
            for temp_user in users:
                logging.info(f'temp_user={temp_user}')
                process_persons = models.Person.query.filter_by(user_id=temp_user.user_id).all()
                for process_person in process_persons:
                    if process_person.head_img_key:
                        head_img_url = utils.get_signed_url(process_person.head_img_key)
                    else:
                        head_img_url = None
                    
                    friend_persons.append({
                        "person_id": process_person.id,
                        "person_name": process_person.name,
                        "head_img_url": head_img_url,
                        "lora_train_status": process_person.lora_train_status,
                        "user_name": temp_user.name,
                        "user_icon": temp_user.icon
                        
                    })
    
                        
    logging.info(f'persons={persons}')

    result_persons = []

    for person in persons:
        if not person.head_img_key:
            person_source = models.Source.query.filter(models.Source.person_id==person.id, models.Source.base_img_key != None).first()

            if person_source:
                image_data = utils.oss_get(person_source.base_img_key)

                try:
                    face_coordinates = aliyun_face_detector.get_face_coordinates(image_data)
                    print(face_coordinates)
                    cropped_face = aliyun_face_detector.crop_face_pil(image_data, face_coordinates)
                except Exception as e:
                    logging.error(f'get face coordinates error: {e}')
                    cropped_face = image_data
                    continue
                
                person.head_img_key = f'head_img/{person.name}.jpg'
                utils.oss_put(person.head_img_key, cropped_face)

                db.session.commit()
        if person.head_img_key:
            head_img_url = utils.get_signed_url(person.head_img_key)
        else:
            head_img_url = None
        result_persons.append({
            "person_id": person.id,
            "person_name": person.name,
            "nickname": user.name,
            "head_img_url": head_img_url,
            "lora_train_status": person.lora_train_status,
        })
    
    is_subscribe = user.subscribe_until is not None and user.subscribe_until.timestamp() > int(time.time())
    # 邀请的数量
    invite_num = models.InviteRecord.query.filter_by(invite_open_id=user.open_id).count()
    # 被邀请的数量
    be_invite_num =models.InviteRecord.query.filter_by(open_id=user.open_id).count()
    if be_invite_num > 1:
        be_invite_num=1
    used_diamond = int(models.Payment.query.filter_by(user_id=user_id, pay_type=2).with_entities(func.sum(models.Payment.payment_amount)).scalar() or 0)
    icon_url=None
    if user.icon:
        icon_url = utils.get_signed_url(user.icon)
    response = {
        "data": {
            "persons": result_persons,
            "min_img_num": 10,
            "max_img_num": 20,
            "is_subscribe": is_subscribe,
            "dna": user.dna,
            "subscribe_until": user.subscribe_until.timestamp() if user.subscribe_until else None,
            "diamond" : user.diamond,
            "invited_num" : invite_num,
            "used_diamond" : used_diamond,
            "unlock_need_diamond": config.UNLOCK_PHOTO_DIAMOND,
            "open_id": user.open_id,
            "reward_diamond": (invite_num + be_invite_num) * config.INVITED_ADD_DIAMOND,
            "name": user.name,
            "icon": icon_url,
            "friend_persons": friend_persons 
        },
        "msg": "get user successfully",
        "code": 0
    }

    logging.info(f'get_user response = {response}')
    return jsonify(response), 200


@app.route('/api/update_user', methods=['POST'])
def update_user():
    logger.info(f'update_user args is {request.json}')
    args = dict(request.json)
    user_id= args.get('user_id')
    name = args.get('name')
    icon = args.get('icon')

    if not name and not icon:
        return jsonify({"msg": "name and icon都为空","code":-1}), 400
    
    if not user_id:
        return jsonify({"msg": "user_id不能为空","code":-1}), 400
    user = models.User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"msg": "user not found","code":-1}), 400
    if name:
        user.name=name
    if icon:
        data = utils.oss_source_get(icon)
        utils.oss_put(icon, data)
        user.icon=icon
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "update success","code":0}), 200



# todo get wechat server msg
@app.route('/api/get_wechat_msg', methods=['GET'])
def get_wechat_msg():
    
    response={
        "data":{
            
        }
    }

    return jsonify(response), 200

@app.route('/api/upload_payment', methods=['GET'])
def upload_payment():
    logger.info(f'upload_payment request args is {request.args}')
    # Create a mutable copy of request.args
    args = dict(request.args)
    # Handle the frontend parameter name mistake
    if args.get('uxser_id'):
        args['user_id'] = args['uxser_id']
        del args['uxser_id']
    missing_params = [param for param in ['user_id', 'payment_amount', 'receipt', 'pack_id', 'product_id']
                      if args.get(param) is None]
    if missing_params:
        logger.error(f'upload_payment missing params {missing_params}')
        return jsonify({"error": f"Missing parameters: {', '.join(missing_params)}"}), 400

    user_id = args.get('user_id')
    payment_amount = args.get('payment_amount')
    receipt = args.get('receipt')
    pack_id = args.get('pack_id')
    product_id = args.get('product_id')
    # get unlock_num. If not provided, set to infinite, for backward compatibility
    unlock_num = args.get('unlock_num', 9999)

    # Validate payment
    # 1. check receipt doesn't exist in payments
    payment = models.Payment.query.filter_by(receipt=receipt).first()
    if payment:
        logger.error(f'upload_payment receipt {receipt} already exists')
        return jsonify({"error": f"receipt {receipt} already exists"}), 400
    # 2. check receipt is valid
    validate_rst = utils.validate_IAP_receipt(receipt)
    if not validate_rst:
        logger.error(f'upload_payment receipt {receipt} is invalid')
        return jsonify({"error": f"receipt {receipt} is invalid"}), 400
    
    # Create a new payment
    new_payment = models.Payment(
        user_id=user_id, 
        payment_amount=int(payment_amount) if payment_amount else None, 
        receipt=receipt, 
        pack_id=int(pack_id) if pack_id else None, 
        product_id=product_id
    )
    db.session.add(new_payment)

    # Update is_unlock to 1 for the pack with the given pack_id
    pack = models.Pack.query.get(pack_id)
    if pack:
        pack.unlock_num += int(unlock_num)
        pack.is_unlock = pack.unlock_num >= pack.total_img_num
    else:
        return jsonify({"msg": "error: Pack not found", 'code': 1}), 404
    
    # Update subscribe using the first item in response['receipt']['in_app']
    if validate_rst[1][0].get('expires_date_ms'):
        user = models.User.query.filter_by(user_id=user_id).first()
        # store subscribe_until (timestamp) in user table 
        user.subscribe_until = datetime.fromtimestamp(int(validate_rst[1][0]['expires_date_ms']) / 1000)
        user.subscribe_info = validate_rst[1][0]

    # Commit the changes
    db.session.commit()
    
    ############################
    # send payment callback request to toutiao
    bd_conversion_utils.report_event(user_id, 'active_pay', payment_amount)

    ###########################
    # Notify
    url = 'https://maker.ifttt.com/trigger/PicPayment/json/with/key/kvpqNPLePMIVcUkAuZiGy'
    payload = {
        'msg': f'User {user_id} paid {payment_amount} for pack {pack_id}, at product_id {product_id}'
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        logging.error(f'notify ifttt error: {e}')

    return jsonify({"msg": "Payment successful and pack unlocked", 'code':0}), 200


@app.route('/api/upload_diamond_payment', methods=['GET'])
def upload_diamond_payment():
    logger.info(f'upload_payment request args is {request.args}')
    # Create a mutable copy of request.args
    args = dict(request.args)
    # Handle the frontend parameter name mistake
    if args.get('uxser_id'):
        args['user_id'] = args['uxser_id']
        del args['uxser_id']
    missing_params = [param for param in ['user_id', 'pack_id']
                      if args.get(param) is None]
    if missing_params:
        logger.error(f'upload_payment missing params {missing_params}')
        return jsonify({"error": f"Missing parameters: {', '.join(missing_params)}"}), 400

    user_id = args.get('user_id')
    pack_id = args.get('pack_id')
    product_id = args.get('product_id')
    # get unlock_num. If not provided, set to infinite, for backward compatibility
    unlock_num = args.get('unlock_num', 9999)

    # Validate payment
    # 1. check user diamond is enough
    # 1. get user
    user = models.User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"error": "user not found"}), 400
    
    if user.diamond < config.UNLOCK_PHOTO_DIAMOND:
        return jsonify({"error": "diamond not enough"}), 400
    # Create a new payment
    new_payment = models.Payment(
        user_id=user_id, 
        payment_amount=config.UNLOCK_PHOTO_DIAMOND, 
        receipt='', 
        pack_id=int(pack_id) if pack_id else None, 
        product_id=product_id,
        # 支付类型：点券支付
        pay_type=2
    )
    db.session.add(new_payment)

    # Update is_unlock to 1 for the pack with the given pack_id
    pack = models.Pack.query.get(pack_id)
    if pack:
        pack.unlock_num += int(unlock_num)
        pack.is_unlock = pack.unlock_num >= pack.total_img_num
    else:
        return jsonify({"msg": "error: Pack not found", 'code': 1}), 404

    user.diamond = user.diamond - config.UNLOCK_PHOTO_DIAMOND
    # Commit the changes
    db.session.commit()
    
    ############################
    # send payment callback request to toutiao
    bd_conversion_utils.report_event(user_id, 'active_pay', config.UNLOCK_PHOTO_DIAMOND)

    ###########################
    # Notify
    url = 'https://maker.ifttt.com/trigger/PicPayment/json/with/key/kvpqNPLePMIVcUkAuZiGy'
    payload = {
        'msg': f'User {user_id} paid {config.UNLOCK_PHOTO_DIAMOND} for pack {pack_id}, at product_id {product_id}'
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        logging.error(f'notify ifttt error: {e}')

    return jsonify({"msg": "Payment successful and pack unlocked", 'code':0}), 200


@app.route('/api/get_wechat_open_id', methods=['GET'])
def get_wechat_open_id():
    # Generate a random user_id with 10 characters
    user_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    if 'X-Forwarded-For' in request.headers:
        user_ip = request.headers.getlist("X-Forwarded-For")[0].rpartition(' ')[-1]
    else:
        user_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    # return dummy result tJ0T5BcptE if user_agent contains 1.0.7 or 1.0.8
    if user_agent and ('1.1.4' in user_agent or '1.1.5' in user_agent):
        user_id = 'matTlTd5hz'
        user_ip = ''
        new_user = models.User.query.filter_by(user_id=user_id).first()
        logging.info(f'!!!! Dummy user for test, user_id is {user_id}, ua is {user_agent}')
    else:
        logging.info(f'create new user ip is {user_ip}, ua is {user_agent}')
        # Create a new user with the generated user_id
        pay_rand = random.randint(1, 100)
        if pay_rand < 25:   # 25%
            pay_group = 1
        elif pay_rand < 50: # 25%
            pay_group = 10
        else:               # 50%
            pay_group = 20
        dna = {
            'pay_group': pay_group,
            'pay_in_advance': random.randint(0,100) < 5,
        }
        new_user = models.User(user_id=user_id, ip = user_ip, ua = user_agent, group = config.user_group, min_img_num = config.min_image_num, max_img_num = 50, dna=dna, diamond=100)

    # Add the new user to the database and commit the changes
    db.session.add(new_user)
    db.session.commit()

    # send active request to toutiao
    click = models.BdClick.query.filter(models.BdClick.ip == user_ip, models.BdClick.con_status==0).order_by(models.BdClick.id.desc()).first()
    if click:
        try:
            requests.get(click.callback)
            click.con_status = 1
            click.user_id = user_id
            db.session.add(click)
            db.session.commit()
            logging.info(f'update click {click.id} to user {user_id}')
        except Exception as e:
            logging.error(f'update click {click.id} to user {user_id} error: {e}')
    else:
        logging.error(f'no click for ip {user_ip}')


    # Create the response object with the specified format
    response = {
        "code": 0,
        "msg": "create user successfully",
        "data": {
            "user_id": user_id,
            "min_img_num": new_user.min_img_num,
            "max_img_num": new_user.max_img_num,
            "pay_group": random.randint(1,3),
            "shot_num": 10,
            "shot_seconds:" : 10,
            "max_styles" : 1
        }
    }

    # Return the response object as a JSON response
    return jsonify(response)

# Apple subscribe renew callback
@app.route('/api/subscribe_renew', methods=['POST'])
def subscribe_renew():
    logger.info(f'subscribe_renew request.')
    # save request to data file with timestamp
    with open(f'./tmp/subscribe_renew_{int(time.time())}.dat', 'w') as f:
        f.write(json.dumps(request.json))

    # JWT decode and validate
    signed_payload = request.json['signedPayload']
    payload = jwt.decode(signed_payload, options={"verify_signature": False})
    signed_renew_info = payload['data']['signedTransactionInfo']
    renew_info = jwt.decode(signed_renew_info, options={"verify_signature": False})
    
    # find user whos subscribe_info json_contains original_transaction_id
    original_transaction_id = renew_info['originalTransactionId']
    original_transaction_id_json = json.dumps({"original_transaction_id": original_transaction_id})
    user = models.User.query.filter(func.JSON_CONTAINS(models.User.subscribe_info, original_transaction_id_json)).first()

    if user:
        # determine new subscribe_until
        user.subscribe_until = datetime.fromtimestamp(int(renew_info['expiresDate']) / 1000)
        db.session.commit()
        logger.info(f'subscribe_renew user {user.user_id} renewed')
    return jsonify({"msg": "subscribe_renew successful", 'code':0}), 200


# wechat miniprogram pre order
@app.route('/api/wechat/pre_pay', methods=['POST'])
def wechat_pre_pay():
    logger.info(f'wechat_pre_pay args is {request.json}')
    args = dict(request.json)

    missing_params = [param for param in ['open_id', 'pay_config_id']
                      if args.get(param) is None]
                
    if missing_params:
        logger.error(f'upload_payment missing params {missing_params}')
        return return_error(f"Missing parameters: {', '.join(missing_params)}")

    # get config json
    with open('backend/pay_config.json', 'r') as f:
        data = json.load(f)
    
    pay_config_id = args.get('pay_config_id')

    # 在pay_config列表中查找匹配的数据
    matched_data = None
    for item in data['pay_config']:
        if item['id'] == pay_config_id:
            matched_data = item
            break

    # 判断是否找到匹配的数据
    if matched_data is not None:
        # 获取匹配数据的所有字段
        amount = matched_data['current_price']
    else:
        return jsonify({"msg": "支付类型不存在","code":-1}), 400
    
    diamond = matched_data['diamond']
    open_id = args.get('open_id')

    user = models.User.query.filter_by(open_id=open_id)
    if not user:
        return jsonify({"msg": "user not found","code":-1}), 400
    
    url = "https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi"
    parsed_url = urlparse(url)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    amount_json= {
        "total": amount,
        "currency": "CNY"
    }
    payer={
        "openid":open_id
    }
    with open('backend/apiclient_key.pem', 'r') as f:
       private_key = f.read()
    #    logging.info(f'private_key={private_key}')
    order_id = utils.generate_order_id()
    data = {
        "mchid": config.WECHAT_PAY_MCHID,
        "out_trade_no": order_id,
        "appid": config.appid,
        "description": '点券',
        "notify_url": config.WECHAT_PAY_NOTIFY_URL,
        "amount": amount_json,
        "payer": payer,
    }

    request_body = json.dumps(data)
    logging.info(f'{request_body}')
    token, timestamp, nonce = get_wechat_pay_token(config.WECHAT_PAY_MCHID, config.WECHAT_PAY_CERT_SERIAL, private_key, "POST", parsed_url.path, request_body)
    headers["Authorization"] = token
    wechat_response = requests.post(url, headers=headers, data=request_body)

    prepay_id = wechat_response.json()["prepay_id"]

    package = 'prepay_id='+prepay_id
    logging.info(f'package={package}')
    pay_sign = get_wechat_pay_sign(config.appid, timestamp, nonce, package, private_key)
    wechat_pay_order = models.WechatPayOrder.query.filter_by(order_id=order_id).first()
    
    if wechat_pay_order:
        return jsonify({"error": "order already exist"}), 400
    
    new_pay_order = models.WechatPayOrder(open_id=open_id, state=1, order_id=order_id, amount=amount, diamond = diamond)
    # create wechat order
    db.session.add(new_pay_order)
    db.session.commit()
    # logger.info(f'{pre_pay_id}')
    response={
        "code":0,
        "msg":"call wechat pre pay success",
        "data": {
            "prepay_id": prepay_id,
            "pay_sign": pay_sign,
            "timestamp": timestamp,
            "nonce": nonce,
            "sign_type":"RSA",
            "package": package,
            "order_id": order_id
            
        }
    }
    return jsonify(response)

# wechat miniprogram pay callback
@app.route('/api/wechat/pay_callback', methods=['POST'])
def wechat_pay_callback():
    logger.info(f'wechat_pre_pay args is {request.json}')
    data = request.json
    source = data.get("resource")
    nonce = source.get("nonce")
    ciphertext = source.get("ciphertext")
    associated_data = source.get("associated_data")
    aesgcm = AESGCM(config.WECHAT_PAY_API_KEY.encode())

    # 都需要转成bytes类型才能进行解密
    associated_data = associated_data.encode() if isinstance(associated_data, str) else associated_data
    nonce = nonce.encode() if isinstance(nonce, str) else nonce
    ciphertext = base64.b64decode(ciphertext)

    # 解密
    plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
    plaintext_decode = plaintext.decode()
    logging.info(f'plaintext={plaintext_decode}')
    plaintext_json = json.loads(plaintext_decode)
    # our order_id
    out_trade_no = plaintext_json.get("out_trade_no")
    # wechat order_id
    wechat_order_id = plaintext_json.get("transaction_id")
    trade_state = plaintext_json.get("trade_state")
    if trade_state =='SUCCESS':
        # for update lock data
        wechat_pay_order = models.WechatPayOrder.query.filter_by(order_id=out_trade_no, state=1).with_for_update().first()
        if not wechat_pay_order:
            logging.info(f'order_id={out_trade_no} order not found')
            return jsonify({"code": "FALI","message":"失败"}), 400
        open_id = wechat_pay_order.open_id
        amount = wechat_pay_order.amount
        diamond = wechat_pay_order.diamond
        user = models.User.query.filter_by(open_id=open_id).first()
        if not user:
            logging.info(f'open_idd={open_id} user not found')
            return jsonify({"code": "FALI","message":"失败"}), 400
        user.diamond = user.diamond + diamond
        wechat_pay_order.state=3
        wechat_pay_order.wechat_order_id = wechat_order_id
        wechat_pay_order.wechat_origin_text=plaintext_decode
        wechat_pay_order.update_time=datetime.now()
        # Commit the session to save changes
        db.session.commit()
        # pay success add diamond
    else:
        # pay fail
        return jsonify({"code": "FALI","message":"失败"}), 400

        

    # out_trade_no = plaintext_decode.get("out_trade_no")
    # return plaintext.decode()
    # notify_data = wechat_pay.parse_payment_result(data)

    return 'SUCCESS'
    

def get_wechat_pay_sign(appid, timestamp, nonce, package, private_key):
    message = '\n'.join([appid, timestamp, nonce, package, ''])
    logging.info(f'sign={message}')
    rsa_key = RSA.import_key(private_key)
    signer = pkcs1_15.new(rsa_key)
    hash_obj = SHA256.new(message.encode('utf-8'))
    pay_sign = base64.b64encode(signer.sign(hash_obj)).decode('utf-8')
    return pay_sign

def get_wechat_pay_token(mchid, serial_no, private_key, method, url, request_body):
    timestamp = str(int(time.time()))
    nonce = str(int(time.time() * 1000))
    message = '\n'.join([method, url, timestamp, nonce, request_body, ''])
    logging.info(f'sign={message}')

    rsa_key = RSA.import_key(private_key)
    signer = pkcs1_15.new(rsa_key)
    hash_obj = SHA256.new(message.encode('utf-8'))
    signature = base64.b64encode(signer.sign(hash_obj)).decode('utf-8')

    token = 'WECHATPAY2-SHA256-RSA2048 mchid="{}",nonce_str="{}",signature="{}",timestamp="{}",serial_no="{}"'.format(
        mchid, nonce, signature, timestamp, serial_no)
    logging.info(f'token={token}')
    return token, timestamp, nonce
    

# Post request for upload_payment
@app.route('/api/upload_payment', methods=['POST'])
def upload_payment_post():
    logger.info(f'upload_payment request args is {request.json}')
    # save request to data file with timestamp
    with open(f'./tmp/upload_payment_{int(time.time())}.dat', 'w') as f:
        f.write(json.dumps(request.json))

    # Get args from request post data
    args = dict(request.json)
    # Handle the frontend parameter name mistake
    if args.get('uxser_id'):
        args['user_id'] = args['uxser_id']
        del args['uxser_id']

    # Restore purchase
    if args.get('restored') == 1:
        receipt = args.get('receipt')
        # validate receipt, if valid, set user's subscribe_until to 
        validate_rst = utils.validate_IAP_receipt(receipt)
        if not validate_rst or len(validate_rst[1]) == 0:
            logger.error(f'upload_payment receipt {receipt} is invalid')
            return return_error(f"receipt {receipt} is invalid")
        expire_date = validate_rst[1][0].get('expires_date_ms')
        if not expire_date:
            logger.error(f'upload_payment receipt {receipt} no expire_date_ms field')
            return return_error(f"receipt {receipt} no expire_date_ms field")
        user = models.User.query.filter_by(user_id=args['user_id']).first()
        user.subscribe_until = datetime.fromtimestamp(int(expire_date) / 1000)

        db.session.commit()
        logger.info(f'upload_payment restore for user {args["user_id"]}')
        return return_success(f"restore user {args['user_id']} from {payment.user_id}")

    missing_params = [param for param in ['user_id', 'payment_amount', 'receipt', 'pack_id', 'product_id']
                      if args.get(param) is None]
    if missing_params:
        logger.error(f'upload_payment missing params {missing_params}')
        return return_error(f"Missing parameters: {', '.join(missing_params)}")

    user_id = args.get('user_id')
    payment_amount = args.get('payment_amount')
    receipt = args.get('receipt')
    pack_id = args.get('pack_id')
    product_id = args.get('product_id')
    # get unlock_num. If not provided, set to infinite, for backward compatibility
    unlock_num = args.get('unlock_num', 9999)
    subscribe_until = args.get('subscribe_until', None)

    # Validate payment
    # 1. check receipt doesn't exist in payments
    payment = models.Payment.query.filter_by(receipt=receipt).first()
    if payment:
        logger.error(f'upload_payment receipt {receipt} already exists')
        return return_error(f"receipt {receipt} already exists")
    # 2. check receipt is valid
    validate_rst = utils.validate_IAP_receipt(receipt)
    if not validate_rst:
        logger.error(f'upload_payment receipt {receipt} is invalid')
        return return_error(f"receipt {receipt} is invalid")
    if len(validate_rst[1]) == 0:
        logger.error(f'upload_payment receipt, empty "in_app" list')
        return return_error(f"receipt {receipt} is invalid")

    # Create a new payment
    new_payment = models.Payment(
        user_id=user_id, 
        payment_amount=int(payment_amount) if payment_amount else None, 
        receipt=receipt, 
        pack_id=int(pack_id) if pack_id else None, 
        product_id=product_id
    )
    db.session.add(new_payment)

    # Update is_unlock to 1 for the pack with the given pack_id
    pack = models.Pack.query.get(pack_id)
    if pack:
        pack.unlock_num += int(unlock_num)
        pack.is_unlock = pack.unlock_num >= pack.total_img_num
    else:
        return return_error(f"Pack not found")
    
    # Handle subscribe logics
    if subscribe_until:
        user = models.User.query.filter_by(user_id=user_id).first()
        # store subscribe_until (timestamp) in user table 
        user.subscribe_until = datetime.fromtimestamp(int(subscribe_until))
        logger.info(f'get subscribe_until from app. user {user_id} subscribe_until {user.subscribe_until}')

    # Update subscribe using the first item in response['receipt']['in_app']
    if validate_rst[1][0].get('expires_date_ms'):
        user = models.User.query.filter_by(user_id=user_id).first()
        # store subscribe_until (timestamp) in user table 
        user.subscribe_until = datetime.fromtimestamp(int(validate_rst[1][0]['expires_date_ms']) / 1000)
        user.subscribe_info = validate_rst[1][0]
        logger.info(f'get subscribe_until from receipt. user {user_id} subscribe_until {user.subscribe_until}')
    
    # Commit the changes
    db.session.commit()
    
    ############################
    # send payment callback request to toutiao
    bd_conversion_utils.report_event(user_id, 'active_pay', payment_amount)

    ###########################
    # Notify
    url = 'https://maker.ifttt.com/trigger/PicPayment/json/with/key/kvpqNPLePMIVcUkAuZiGy'
    payload = {
        'msg': f'User {user_id} paid {payment_amount} for pack {pack_id}, at product_id {product_id}'
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        logging.error(f'notify ifttt error: {e}')

    return jsonify({"msg": "Payment successful and pack unlocked", 'code':0}), 200


# Post request for upload_payment
@app.route('/api/upload_gp_payment', methods=['POST'])
def upload_gp_payment_post():
    logger.info(f'upload_payment request args is {request.json}')
    # save request to data file with timestamp
    with open(f'./tmp/upload_gp_payment_{int(time.time())}.dat', 'w') as f:
        f.write(json.dumps(request.json))

    # Get args from request post data
    args = dict(request.json)

    missing_params = [param for param in ['user_id', 'payment_amount', 'receipt', 'product_id']
                      if args.get(param) is None]
    if missing_params:
        logger.error(f'upload_payment missing params {missing_params}')
        return return_error(f"Missing parameters: {', '.join(missing_params)}")

    user_id = args.get('user_id')
    payment_amount = args.get('payment_amount')
    receipt = args.get('receipt')
    pack_id = args.get('pack_id', None)
    product_id = args.get('product_id')
    # get unlock_num. If not provided, set to infinite, for backward compatibility
    unlock_num = args.get('unlock_num', 9999)
    subscribe_until = args.get('subscribe_until', None)

    # Validate payment
    # 1. check receipt doesn't exist in payments
    payment = models.Payment.query.filter_by(receipt=receipt).first()
    if payment:
        logger.error(f'upload_payment receipt {receipt} already exists')
        return return_error(f"receipt {receipt} already exists")
    # 2. check receipt is valid
    # validate_rst = utils.validate_IAP_receipt(receipt)


    # Create a new payment
    new_payment = models.Payment(
        user_id=user_id, 
        payment_amount=int(payment_amount) if payment_amount else None, 
        receipt=receipt, 
        pack_id=int(pack_id) if pack_id else None, 
        product_id=product_id
    )
    db.session.add(new_payment)

    # Update is_unlock to 1 for the pack with the given pack_id
    if pack_id:
        pack = models.Pack.query.get(pack_id)
        if pack:
            pack.unlock_num += int(unlock_num)
            pack.is_unlock = pack.unlock_num >= pack.total_img_num
        else:
            return return_error(f"Pack not found")
        
    # Handle subscribe logics
    if subscribe_until:
        user = models.User.query.filter_by(user_id=user_id).first()
        # store subscribe_until (timestamp) in user table 
        user.subscribe_until = datetime.fromtimestamp(int(subscribe_until))
        logger.info(f'get subscribe_until from app. user {user_id} subscribe_until {user.subscribe_until}')

    # Commit the changes
    db.session.commit()
    
    ############################
    # send payment callback request to toutiao
    # bd_conversion_utils.report_event(user_id, 'active_pay', payment_amount)

    ###########################
    # Notify
    url = 'https://maker.ifttt.com/trigger/PicPayment/json/with/key/kvpqNPLePMIVcUkAuZiGy'
    payload = {
        'msg': f'User {user_id} paid {payment_amount} for pack {pack_id}, at product_id {product_id}'
    }
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        logging.error(f'notify ifttt error: {e}')

    return jsonify({"msg": "Payment successful and pack unlocked", 'code':0}), 200


@app.route('/api/get_example_2', methods=['GET'])
def get_example_2():
    lang = request.headers.get('language')

    examples = models.Example.query.all()

    result = {
        'before': [],
        'after': [],
        'bad': [],
        'styles': []
    }

    for example in examples:
        img_height, img_width = utils.get_oss_image_size(example.img_key)

        rs = {
            'img_url': utils.get_signed_url(example.img_key, is_yasuo=True),
            'img_height': img_height,
            'img_width': img_width,
            'style': example.style,
            'id': example.id,
        }
        if example.type == 0:
            result['before'].append(rs)
        elif example.type == 1:
            result['after'].append(rs)
        elif example.type == 2:
            result['bad'].append(rs)
    
    # Query the tags and filter out the ones you need
    tags = models.Tag.query.filter(models.Tag.img_key != None).filter(models.Tag.rate > 0).order_by(models.Tag.rate.desc()).all()

    # Extract all img_keys
    img_keys = [tag.img_key for tag in tags]

    # Fetch all image sizes concurrently
    image_sizes = utils.get_image_sizes(img_keys)

    # Iterate over the tags and create the result dictionary using pre-fetched image sizes
    for tag in tags:
        img_key = tag.img_key
        if img_key and img_key in image_sizes:  # check if the key exists in the image_sizes dictionary
            img_height, img_width = image_sizes[img_key]
            tag_display_name = tag.tag_name
            if lang:
                for locale, name in tag.display_name.items():
                    if locale.startswith(lang):
                        tag_display_name = name
                        break
                
            rs = {
                'img_url': utils.get_signed_url(tag.img_key, is_yasuo=True),
                'img_height': img_height,
                'img_width': img_width,
                'style': tag_display_name,
                'id': tag.id,
                'tag_id': tag.id
            }
            result['styles'].append(rs)

    response = {
        'data': result,
        'msg': '成功获取示例图片',
        'code': 200
    }
    return jsonify(response)

@app.route('/api/get_example_images', methods=['GET'])
def get_example_images():
    scenes = models.Scene.query.filter(models.Scene.action_type == 'example', models.Scene.base_img_key != None).all()
    result = []

    for scene in scenes:
        img_url = utils.get_signed_url(scene.base_img_key)
        img_height, img_width = utils.get_image_size(img_url)

        result.append({
            'img_url': img_url,
            'img_height': img_height,
            'img_width': img_width,
            'style_name': scene.collection_name,
            'id': scene.scene_id
        })

    response = {
        'data': result,
        'msg': '成功获取示例图片',
        'code': 200
    }
    return jsonify(response)

@app.route('/api/upload_source', methods=['POST'])
def upload_source():        
    if 'img_file' not in request.files or 'user_id' not in request.form or 'person_name' not in request.form:
        return {"status": "error", "message": "Missing img_file, user_id or person_name"}, 400
    img_file = request.files['img_file']
    user_id = request.form['user_id']

    logging.info(f'upload source request {user_id}')

    try: 
        png_img = utils.convert_to_png_bytes(img_file)
    except Exception as e:
        logging.info(f'{user_id} upload source fail {e}')
        # random generate 10 char as name
        random_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        utils.oss_put(f'error/user_{user_id}-{random_id}.dat', img_file)
        return {"msg": f"上传失败，图片格式错误或中断导致无法打开", "code": 1, "data" : ''}, 200 

    png_img = utils.convert_to_png_bytes(img_file)
    jpg_img = utils.convert_to_jpg_bytes(png_img)

    source_type = request.form.get('type', None)
    person_name = request.form['person_name']


    face_count = aliyun_face_detector.detect_face(jpg_img)
    if face_count != 1:
        logging.info(f'{user_id}上传失败，图片中有{face_count}人脸')
        return {"msg": f"上传失败，图片中有{face_count}人脸", "code": 1, "data" : ''}, 200
    
    # 查找 persons 表中是否存在相应的记录
    person = models.Person.query.filter_by(user_id=user_id, name=person_name).first()
    if not person:
        # 如果不存在，创建一个新的 Person 对象并将其保存到数据库中
        new_person = models.Person(name=person_name, user_id=user_id)
        db.session.add(new_person)
        db.session.commit()
        person_id = new_person.id
    else:
        person_id = person.id

    base_img_key = f'source/{user_id}/{person_name}/{secrets.token_hex(16)}.png'
    utils.oss_put(base_img_key, png_img)

    # 存储记录到数据库
    source = models.Source(base_img_key=base_img_key, user_id=user_id, type=source_type, person_id=person_id)
    db.session.add(source)
    db.session.commit()

    count = models.Source.query.filter(models.Source.person_id == person_id).count()

    response = {
        "msg": "上传人像图片成功", 
        "code": 0, 
        "data": {
            "person_id": person_id,
            "person_name": person_name,
            "source_num": count
        }
    }
    
    logging.info(f'upload source success {user_id} {person_id} {person_name}')
    return jsonify(response)


# uploda one picture and create person
@app.route('/api/create_person', methods=['POST'])
def create_person(): 

    logger.info(f'create_person args is {request.json}')
    args = dict(request.json)

    missing_params = [param for param in ['user_id', 'image_oss_key']
                      if args.get(param) is None]
                
    if missing_params:
        logger.error(f'create_person missing params {missing_params}')
        return return_error(f"Missing parameters: {', '.join(missing_params)}")       
    
    user_id = args.get('user_id')
    image_oss_key = args.get('image_oss_key')
    user = models.User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"msg": "用户不存在","code":-1}), 400
    # get image from oss by image_oss_key
    try:
        data = utils.oss_source_get(image_oss_key)
    except Exception as e:
        message = e.details['Message']
        return jsonify({"msg": message,"code":-1}), 400
    
    try:
        oss_result = aliyun_face_detector.one_face(data)
    except Exception as e:
        return {"msg": "error", "code": -1}, 400
    
    if oss_result:
        person_name = utils.generate_unique_string()
        new_person =models.Person(name=person_name, user_id=user_id)
        db.session.add(new_person)
        db.session.commit()
        utils.oss_put(image_oss_key, data)
        source = models.Source(base_img_key=image_oss_key, user_id=user_id, person_id=new_person.id, is_first=1)
        db.session.add(source)
        db.session.commit()
    else:
        return jsonify({"msg": "上传图片不正确，图片应该是正面人脸照片且只有一张人脸","code":-1}), 400

    response = {
        "msg": "上传人像图片成功", 
        "code": 0, 
        "data": {
            "person_id": new_person.id,
            "persion_name": person_name,
        }
    }
    
    logging.info(f'upload source success {user_id} {new_person.id} {person_name}')
    return jsonify(response)

@app.route('/api/v2/upload_multiple_sources', methods = ['POST'])
def upload_multiple_sources_v2():
    logger.info(f'upload_multiple_sources args is {request.json}')
    args = dict(request.json)

    missing_params = [param for param in ['user_id', 'img_oss_keys', 'person_id']
                      if args.get(param) is None]
                
    if missing_params:
        logger.error(f'upload_multiple_sources missing params {missing_params}')
        return return_error(f"Missing parameters: {', '.join(missing_params)}")       
    
    user_id = args.get('user_id')
    person_id = args.get('person_id')
    image_oss_keys = args.get('img_oss_keys')

    # 查找 persons 表中是否存在相应的记录
    person = models.Person.query.filter_by(user_id=user_id, id=person_id).first()
    source = models.Source.query.filter_by(user_id=user_id, person_id=person_id, is_first=1).first()
    if not person:
        return jsonify({"msg": "person_id不存在","code":-1}), 400
    if not source:
        return jsonify({"msg": "首张图片不存在","code":-1}), 400
    else:
        person_id = person.id
        person.lora_train_status = None

    print(image_oss_keys, type(image_oss_keys))

    success_count = 0
    result_map={}
    soure_base_img = utils.oss_source_get(source.base_img_key)
    for key in image_oss_keys:
        data = utils.oss_source_get(key)
        # confidence =aliyun_face_detector.aliyun_face_compare(soure_base_img, data)['Data']['Confidence']
        confidence =aliyun_face_detector.aliyun_face_compare(soure_base_img, data)
        logging.info(f'confidence={confidence}')
        if confidence is not None and confidence> config.FACE_COMPARE_CONFIDENCE:
            utils.oss_put(key, data)
            source = models.Source(base_img_key=key, user_id=user_id, person_id=person_id, is_first=0)
            db.session.add(source)
            result_map[key]="success"
            success_count += 1
        else:
            utils.oss_put(key, data)
            result_map[key]="fail"
    db.session.commit()

    response = {
        "msg": "上传人像图片成功", 
        "code": 0, 
        "data": {
            "person_id": person_id,
            "img_result": result_map,
            "success_count": success_count
        }
    }
    logging.info(f'upload source response={response}')
    
    return jsonify(response)


@app.route('/api/pay_config', methods = ['GET'])
def get_pay_config():
    with open('backend/pay_config.json', 'r') as f:
        config = json.load(f)
    response = {
        "msg": "get pay config success", 
        "code": 0, 
        "data": config
    }
    return jsonify(response)

@app.route('/api/upload_multiple_sources', methods = ['POST'])
def upload_multiple_sources():
    if 'img_oss_keys' not in request.form or 'user_id' not in request.form or 'person_name' not in request.form:
        return {"status": "error", "message": "Missing img_oss_keys, user_id or person_name"}, 400
    img_oss_keys = request.form.get('img_oss_keys', None)
    user_id = request.form['user_id']
    person_name = request.form['person_name']
    source_type = request.form.get('type', None)
    not_filtration= request.form.get('not_filtration', type=int, default=0)
    person_id = request.form.get('person_id', type=str, default=None)
    
    logging.info(f'upload_multiple_sources request {user_id}, not_filtration {not_filtration}, source_type {source_type}')

    # 查找 persons 表中是否存在相应的记录
    person = models.Person.query.filter_by(user_id=user_id, name=person_name).first()
    if not person:
        # 如果不存在，创建一个新的 Person 对象并将其保存到数据库中
        new_person = models.Person(name=person_name, user_id=user_id)
        db.session.add(new_person)
        db.session.commit()
        person_id = new_person.id
    else:
        person_id = person.id
        person.lora_train_status = None

    print(img_oss_keys, type(img_oss_keys))

    success_count = 0
    keys = json.loads(img_oss_keys)
    for key in keys:
        data = utils.oss_source_get(key)
        if (not_filtration==1) or aliyun_face_detector.one_face(data):
            utils.oss_put(key, data)
            source = models.Source(base_img_key=key, user_id=user_id, type=source_type, person_id=person_id)
            db.session.add(source)
            success_count += 1
    db.session.commit()

    response = {
        "msg": "上传人像图片成功", 
        "code": 0, 
        "data": {
            "person_id": person_id,
            "person_name": person_name,
            "success_count": success_count,
            "checklist": [
            {
                "title": "背景多样性",
                "hint": "上传更多背景不同的照片",
                "score": 87,
                "is_ok": 1
            },
            {
                "title": "人物照片清晰度",
                "hint": "上传清晰的人物照片",
                "score": 43,
                "is_ok": 0
            },
            {
                "title": "人物角度多样性",
                "hint": "上传更多不同角度的人物照片",
                "score": 40,
                "is_ok": 0
            }]
        }
    }
    
    logging.info(f'upload source success {user_id} {person_id} {person_name}')
    return jsonify(response)

@app.route('/api/start_sd_generate', methods=['POST'])
def start_sd_generate():
    if 'user_id' not in request.form or 'person_id_list' not in request.form or 'category' not in request.form:
        return {"status": "error", "message": "Missing user_id, person_id_list or category"}, 400

    user_id = request.form['user_id']
    person_id_list = json.loads(request.form['person_id_list'])
    if (len(person_id_list) == 0):
        return {"status": "error", "message": "person_id_list is empty"}, 400
    try:
        person_id_list = [int(person_id) for person_id in person_id_list]
    except Exception as e:
        return {"status": "error", "message": "Invalid person_id_list"}, 400
    person_id_list.sort()
    category = request.form['category']
    limit = request.form.get('limit', 50, type=int)
    tag_id_list_input = request.form.get('tag_id_list', None)
    if (tag_id_list_input):
        tag_id_list_input = json.loads(tag_id_list_input)
        try:
            tag_id_list_input = [int(tag_id) for tag_id in tag_id_list_input]
        except Exception as e:
            return {"status": "error", "message": "Invalid tag_id_list"}, 400
    for tag_id in tag_id_list_input:
        tag_id_list = [tag_id]
        
        pack = models.Pack(user_id=user_id, total_img_num=0, start_time= datetime.utcnow(), unlock_num = 0, description='合集')
        db.session.add(pack)
        db.session.commit()


        m = 0
        # --------------------------- SD 生成任务 ------------------------------------
        if (models.User.query.filter_by(user_id=user_id).first().group == 1):
            if (tag_id_list):
                logging.info(f'generate_sd_task_with_tag user_id: {user_id},  person_id_list: {person_id_list},  {category},  tag_id_list: {tag_id_list} {limit}')
                m += selector_sd.generate_sd_task_with_tag(category=category, person_id_list = person_id_list, user_id = user_id, pack_id=pack.pack_id, tag_ids = tag_id_list, limit=limit, wait_status=wait_status)
            else:
                m += selector_sd.generate_sd_task(category=category, person_id_list = person_id_list, user_id = user_id, pack_id=pack.pack_id, limit=limit, wait_status=wait_status)
            # Check if person in person_id_list are all finished
            all_lora_ready = True
            for person_id in person_id_list:
                person = models.Person.query.get(person_id)
                if person.lora_train_status != 'finish':
                    all_lora_ready = False
                    break
            if all_lora_ready:
                pack.total_seconds = 23*60
            else:
                # Count all persons with lora_train_status == 'wait'
                wait_count = models.Person.query.filter(models.Person.lora_train_status == 'wait').count()
                if wait_count == 0:
                    pack.total_seconds = 57 * 60
                elif wait_count == 1:
                    pack.total_seconds = 86 * 60
                else:
                    pack.total_seconds = 3*60*60

        # --------------------------- 以下是启动mj和reface的任务 ------------------------------
        else :
            limit = 5
            pack.total_seconds = 2*60
            # m += selector_other.generate_task(person_id=person_id_list[0], category=category, pack_id=pack.pack_id, user_id=user_id, action_type='mj', limit=limit, wait_status=wait_status)

            m += selector_other.generate_task(person_id=person_id_list[0], category=category, pack_id=pack.pack_id, user_id=user_id, action_type='reface', limit=limit, wait_status=wait_status)

        # --------------------------- 以下是返回结果 ----------------------------------
        response = {
            'code': 0, 
            'msg': f'启动{m}张照片的AI拍摄任务',
            'data': {
                "total_time_seconds": pack.total_seconds,
                "total_img_num": m,
                "des": f"AI拍摄完成后，您将获得{m}张照片"
            }
        }
        pack.total_img_num = m
        pack.description = f'合集{m}张'
        db.session.add(pack)
        
    db.session.commit()

    try:
        # 认为生成任务就是付了1分钱
        bd_conversion_utils.report_event(user_id, "game_addiction", 1)
    except Exception as e:
        logging.error(f'report_event error: {e}')

    return jsonify(response)
@app.route('/api/get_generated_images', methods=['GET'])
def get_generated_images():
    t0 = time.time()
    user_id = request.args.get('user_id', None)
    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400

    logging.info(f'get_generated_images user_id: {user_id}')

    # Explicitly joining Task and Pack tables
    Task = aliased(models.Task)
    Pack = aliased(models.Pack)

    join_condition = and_(Pack.user_id == user_id, Pack.pack_id == Task.pack_id)
    query = db.session.query(Pack, Task).filter(join_condition).order_by(desc(Task.rate)).limit(3000)
    result = query.all()

    # Accelerate getting image size using multi-threading
    img_keys = [task.result_img_key for _, task in result if task.result_img_key]
    image_sizes = utils.get_image_sizes(img_keys)

    logging.info(f'Number of records returned: {len(result)}')

    pack_dict = {}

    for pack, task in result:
        # logging.info(f'Processing pack_id: {pack.pack_id}')

        if not pack.pack_id in pack_dict:
            if pack.banner_img_key is None and task.result_img_key:
                logging.info(f'Generating banner for pack_id: {pack.pack_id}')
                image_data = utils.oss_get(task.result_img_key)

                # Generate a dummy face_coordinate
                face_coordinates = (0, 0)  # this needs to be actual coordinates

                banner_img = aliyun_face_detector.crop_16_9_pil(image_data, face_coordinates)
                pack.banner_img_key = f'banner_img/{pack.pack_id}.jpg'
                utils.oss_put(pack.banner_img_key , banner_img)
                db.session.commit()

            pack_dict[pack.pack_id] = {
                "pack_id": pack.pack_id,
                "description": pack.description,
                "total_img_num": pack.total_img_num,
                "is_unlock": pack.is_unlock,
                "imgs": [],
                "thumb_imgs": [], 
                "finish_seconds_left": pack.total_seconds - int((datetime.utcnow() - pack.start_time).total_seconds()),
                'total_seconds': pack.total_seconds ,
                'banner_img_url': utils.get_signed_url(pack.banner_img_key) if pack.banner_img_key else None,
                'heights': [],
                'widths': [],
                'price': pack.price,
                'unlock_num': pack.unlock_num,
            }

        img_key = task.result_img_key
        if img_key:
            is_shuiyin = is_mohu = True
            is_thumb_shuiyin = True
            if len(pack_dict[pack.pack_id]['imgs']) < config.PREVIEW_CLEAR_IMG_NUM:
                is_mohu = False
            if len(pack_dict[pack.pack_id]['imgs']) < pack_dict[pack.pack_id]['unlock_num']:
                is_shuiyin = False
                is_mohu = False
                is_thumb_shuiyin = False

            img_url = utils.get_signed_url(img_key, is_shuiyin = is_shuiyin, is_yasuo = False, is_mohu=is_mohu)
            thumb_url = utils.get_signed_url(img_key, is_shuiyin = is_thumb_shuiyin, is_yasuo = True, is_mohu=is_mohu)
            height, width = image_sizes[img_key]
            if int(height) > 0 and int(width) > 0:
                pack_dict[pack.pack_id]["imgs"].append(img_url)
                pack_dict[pack.pack_id]["thumb_imgs"].append(thumb_url)
                pack_dict[pack.pack_id]["heights"].append(height)
                pack_dict[pack.pack_id]["widths"].append(width)
            else:
                logging.error(f'Invalid image size: {img_key} {height} {width}')

    logging.info(f'time used: {int(time.time() - t0)}s')

    rst_packs = []
    for pack in pack_dict.values():
        if len(pack['imgs']) > 0 or pack['finish_seconds_left'] > 0:
            rst_packs.append(pack)
        else:
            pack['description'] = '用户激增，任务超时，请耐心等待或联系客服'
            logger.error(f'pack {pack["pack_id"]} is timeout')
            rst_packs.append(pack)
    # sort rst_packs by pack_id
    rst_packs.sort(key=lambda x: x['pack_id'], reverse=True)    

    response = {
        'code': 0,
        'msg': 'success',
        'data': {
            'packs': rst_packs
        }
    }

    return jsonify(response), 200



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scene_editor')
def scene_editor():
    return render_template('scene_editor.html')

@app.route('/meiyan_test')
def meiyan_test():
    return render_template('meiyan_test.html')

# 获取场景列表
@app.route('/get_scenes', methods=['GET'])
def get_scenes_route():
    return web_function.get_scenes()

@app.route('/api/get_source', methods=['GET'])
def get_source_route():
    return web_function.get_source()

# 上传图片
@app.route('/upload_scene', methods=['POST'])
def upload_scene_route():
    return web_function.upload_scene()

@app.route('/update_scene', methods=['POST'])
def update_scene_route():
    return web_function.update_scene()

@app.route('/web/update_scene', methods=['POST'])
def update_scene():
    data = request.get_json()
    scene_id = data.get('scene_id')
    params = data.get('params')
    rate = data.get('rate')
    print(f'{scene_id}, {params}, {rate}')
    scene = models.Scene.query.get(scene_id)
    if scene:
        # scene.params = params
        scene.rate = rate
        db.session.commit()
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Scene not found'}), 404

# Get global config
@app.route('/api/global_config', methods=['GET'])
def get_global_config():
    # get all global models.GlobalConfig. Return in key-value dict. Filter out is_delete=1
    configs = models.GlobalConfig.query.filter_by(is_delete=False).all()
    result = {}
    for config in configs:
        result[config.key] = config.value
    # Locale for person_type_data
    if request.headers.get('language'):
        language = request.headers.get('language')
        logger.info(f'language: {language}')

        person_type_data = json.loads(result['person_type_data'])

        fields_to_replace = [('display_name', 'display_name_locale'), ('display_info', 'display_info_locale')]
        for fields_replace_pair in fields_to_replace:
            # for each entry in person_type_data, match first language in entry['display_name_locale'] using 'laugnage' as prefix
            # replace entry['display_name'] with display_name_locale[locale] content
            for entry in person_type_data:
                for locale, display_name in entry[fields_replace_pair[1]].items():
                    if locale.startswith(language):
                        entry[fields_replace_pair[0]] = display_name
                        break
        result['person_type_data'] = json.dumps(person_type_data)

    response = {
        'code': 0,
        'msg': 'success',
        'data': result
    }
    return jsonify(response), 200

@app.route('/api/contact', methods=['POST'])
def submit_contact_form():
    name = request.form.get('name')
    user_id = request.form.get('user_id')
    phone = request.form.get('phone')
    wechat = request.form.get('wechat')
    message = request.form.get('message')

    contact = models.Contact(name=name, phone=phone, user_id=user_id, wechat=wechat, message=message)
    db.session.add(contact)
    db.session.commit()

    response = {
        'code': 0,
        'msg': 'success',
        'data': {'message': 'Contact form submitted successfully'}
    }
    return jsonify(response), 200

def return_error(msg):
    response = {
        'code': 1,
        'msg': msg,
        'data': {'message': msg}
    }
    return jsonify(response), 200

def return_success(msg, **kwargs):
    response = {
        'code': 0,
        'msg': 'success',
        'data': {'message': msg}
    }
    response['data'].update(kwargs)
    return jsonify(response), 200

@app.route('/api/use_promo_code', methods=['POST'])
def use_promo_code():
    '''
    {
        "code": "Fffdddd";
        "user_id": "I63CGgUTMT";
    }
    '''
    data = request.get_json()
    code = data.get('code')
    user_id = data.get('user_id')
    user = models.User.query.filter_by(user_id=user_id).first()
    if not code or not user_id:
        return return_error('Missing code or user_id')
    if not user:
        return return_error('User not found')
    # Mark models.PromoCode as used.
    promo_code = models.PromoCode.query.filter_by(code=code).first()
    if not promo_code:
        return return_error('No such code')
    if not promo_code.is_valid():
        return return_error('Invalid code')
    if promo_code.referer_user_id == user_id:
        return return_error('Cannot use your own code')
    # Valid. Use the code
    promo_code.use(user_id)
    
    # Subscribe promo type
    if promo_code.type in [models.PromoCode.Type.subscribe_week, models.PromoCode.Type.subscribe_month, models.PromoCode.Type.subscribe_year]:
        # determine time_delta by type using switch
        if promo_code.type == models.PromoCode.Type.subscribe_week:
            time_delta = timedelta(days=7)

        elif promo_code.type == models.PromoCode.Type.subscribe_month:
            time_delta = timedelta(days=30)
        elif promo_code.type == models.PromoCode.Type.subscribe_year:
            time_delta = timedelta(days=365)

        # Update user's subscribe_until
        if user.subscribe_until is None or user.subscribe_until < datetime.utcnow():
            user.subscribe_until = datetime.utcnow() + time_delta
        else:
            user.subscribe_until += time_delta
        user.promo_code_id = promo_code.id
        
        db.session.commit()
        return return_success('Promo code used successfully', promo_code=promo_code.to_dict())

    # Unkown promo type
    return return_error('Unknown promo code type')

@app.route('/api/get_token', methods=['GET'])
def get_token():
    # Define the request
    request = AssumeRoleRequest.AssumeRoleRequest()

    # Set the parameters
    request.set_RoleArn("xcx-upload-source@role.1669620267795435.onaliyunservice.com")
    request.set_RoleSessionName("yourSessionName")
    request.set_Policy('''
        {
            "Version": "1",
            "Statement": [
                {
                    "Action": "oss:*",
                    "Resource": "*",
                    "Effect": "Allow"
                }
            ]
        }
    ''')

    request.set_DurationSeconds(3600)

    # Initiate the request and get the response
    response = client.do_action_with_exception(request)

    # Convert the response from bytes to json
    response_dict = json.loads(response)

    # Get the credentials from the response
    credentials = response_dict['Credentials']

    return jsonify(credentials)

@app.route('/api/send_msg', methods=['GET'])
def send_msg():
    access_token = get_wechat_access_token(config.appid, config.appsecret)
    logger.info(f'access_token={access_token}')
    wechat_notify_complete_packs(access_token)
     # Create the response object with the specified format
    response = {
        "code": 0,
        "msg": "send msg success",
        "data": {
        }
    }

    # Return the response object as a JSON response
    return jsonify(response)

def get_wechat_access_token(appid, secret):
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}"
    response = requests.get(url)
    result = response.json()
    if 'access_token' in result:
        return result['access_token']
    else:
        logging.error(f"Failed to get access_token: {result}")
        return None

# def job():
#     app = Flask(__name__)
#     with app.app_context():
#         try:
#             logger.info(f'task run')
#             access_token = get_wechat_access_token(config.appid, config.appsecret)
#             logger.info(f'access_token={access_token}')
#             wechat_notify_complete_packs(access_token)
#         except Exception as e:
#             print("An error occurred:", e)


# def run_schedule():
#     while True:
#         schedule.run_pending()
#         time.sleep(100)

# # 每30分钟执行一次
# schedule.every(10).seconds.do(job)

# # 在一个新的线程中启动定时任务
# t = threading.Thread(target=run_schedule)
# t.start()

if __name__ == '__main__':
    # Add argument parser: -p: port
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=8000, help='port to listen on')
    parser.add_argument('--is_industry', action='store_true', help="Enable industry mode.")
    parser.add_argument('-i', '--image-num', type=int, default = 15,  help="min image num.")
    parser.add_argument('-u', '--user-group', type=int, default = 1,  help="user group.")
    args = parser.parse_args()
    config.is_industry = args.is_industry
    config.min_image_num = args.image_num
    config.user_group = args.user_group
    # wechat_pay = WeChatPay(config.appid, config.appsecret, config.m)
    app.run(host='0.0.0.0', port=args.port, ssl_context=('photolab.aichatjarvis.com.pem', 'photolab.aichatjarvis.com.key'))
    
else:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    logging.root.handlers = gunicorn_logger.handlers
    logging.root.setLevel(gunicorn_logger.level)
    logging.debug('logger setup.')


