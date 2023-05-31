import time
import requests
from backend import models, config
from urllib.parse import urlparse, parse_qs
import logging

"""
{
    "event_type": "active", 
    "event_weight": 0.21312,
    "context": {
        "ad": {
            "callback": "demo_callback",
            "match_type": 3
        },
        "device": {
            "platform": "ios",
            "idfa": "FCD369C3-F622-44B8-AFDE-12065659F34B"
        }
    },
    "properties": {
        "pay_amount": 1231.211
    },
    "timestamp": 1604888786102
}


http://ad.toutiao.com/track/activate/?
callback=B.ezpH241vFUgYLNheuhOp1SaTnA3WQSTLKKeSSTy0FvaRlPTV3rgqXBFKtVKr2to9lKmKrJ1JgQKVa4e59f6MrjaifaPsQJbaFIfBPD1PjtgLNs6mTog9Aayd418g7GLTapckqntVHQUlFyVg7LI2y7C
&os=1
&muid=C25C5AAA-7B24-4E56-9EE0-7FA89267B2FD
"""

def generate_post_data(event_type, callback, pay_amount):
    data = {
        "event_type": event_type,
        "context": {
            "ad": {
                "callback": callback,
            }
        },
        "properties": {
            "pay_amount": pay_amount
        },
        "timestamp": int(time.time() * 1000)
    }

    return data

def report_event(user_id, event_type, payment_amount):
    ############################
    # send payment callback request to toutiao
    user_ip = models.User.query.filter_by(user_id=user_id).first().ip
    click = models.BdClick.query.filter(models.BdClick.ip == user_ip, models.BdClick.con_status==0).order_by(models.BdClick.id.desc()).first()
    if click:
        try:
            # extract callback param from click.callback
            parsed_url = urlparse(click.callback)
            params = parse_qs(parsed_url.query)
            callback_param = params.get('callback', [None])[0]
            post_data = generate_post_data(event_type, callback_param, float(payment_amount))
            rst = requests.post(config.BD_CONVERSION_POST_URL, json=post_data, timeout=5)
            
            logging.info(f"Report {event_type} of user {user_id} to BD: {rst.content.decode('utf8')}")
        except Exception as e:
            logging.error(f'update click {click.id} to user {user_id} error: {e}')
    else:
        logging.error(f'no click for ip {user_ip}')