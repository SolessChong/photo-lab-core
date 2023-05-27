import time
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