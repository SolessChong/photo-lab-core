import hashlib
import json
import argparse
import requests
import time
import logging
from backend.models import *
from backend.extensions import app, db
from backend import config

app.app_context().push()


def md5(s):
    m = hashlib.md5(s)
    return m.hexdigest()

appkey ='644fc9e27dddcc5bad3fb32f'
app_master_secret ='fpejqex8becwzzwmikiv3xr1szqscahn'

msg_templates = {
    'render_finish': {
        'aps': {
            'alert': {
                'title': '您有一套AI照片待查看',
                'subtitle': '',
                'body': '您的一套AI照片已经完成，为了避免过期，请尽快打开PicMagic查看吧！'
            }
        }
    },
    'new_user_activate_2': {
        'aps': {
            'alert': {
                'title': '欢迎使用PicMagic',
                'subtitle': '',
                'body': '您的账号已经激活，请您尽快在新人优惠过期前上传照片。'
            }
        }
    },
    'new_user_activate': {
        'aps': {
            'alert': {
                'title': 'PicMagic新人礼遇已准备就绪',
                'subtitle': '',
                'body': '账号已激活，上传照片享受新人特惠，赶快行动吧！'
            }
        }
    },
    'new_tag': {

    },
    'payment_error': {
        'aps': {
            'alert': {
                'title': 'PicMagic支付出错',
                'subtitle': '',
                'body': '您的支付失败，请联系客服微信 solesschong。'
            }
        }
    },
}

def send_notification(msg_type, user_id, **kwargs):
    method ='POST'
    url ='http://msg.umeng.com/api/send'
    payload = msg_templates.get(msg_type)
    if payload is None:
        logging.error('unknown msg_type: %s' % msg_type)
        return

    params = {
        'appkey': appkey,
        'timestamp': int(time.time()),
        'type':'customizedcast',
        'alias_type':'UMENGTEST',
        'alias': user_id,
        'payload': payload,
    }
    post_body = json.dumps(params)
    sign_str = '%s%s%s%s' % (method, url, post_body, app_master_secret)
    sign = md5(sign_str.encode('utf-8'))
    r = requests.post(url + '?sign=' + sign, data=post_body)
    logging.info('send notification to %s, response: %s' % (user_id, r.text))

def notify_pack(pack):
    if type(pack) is int:
        pack = Pack.query.filter(Pack.pack_id == pack).first()
    if pack is None:
        logging.error('pack not found')
        return
    send_notification('render_finish', pack.user_id)
    pack.notify_count += 1
    db.session.commit()

def notify_complete_packs(notify_count=0, user_id=None):
    # Join Task and Packs, on Task.pack_id == Pack.pack_id, filter all packs with:
    #   1. count task with status is 'finish' and task.pack_id == pack.pack_id >= COMPLETE_PACK_MIN_PICS
    #   2. no task with status is 'wait' and task.pack_id == pack.pack_id
    #   3. pack.notify_count <= notify_count
    if user_id:
        base_query = db.session.query(Task.pack_id).\
            filter(Task.status == 'finish').\
            filter(Task.user_id == user_id)
    else:
        base_query = db.session.query(Task.pack_id).\
            filter(Task.status == 'finish')
    subquery = base_query.\
        group_by(Task.pack_id).\
        having(db.func.count(Task.id) >= config.COMPLETE_PACK_MIN_PICS).\
        correlate(Pack)
    
    filtered_packs = db.session.query(Pack).\
        filter(~db.exists().where(db.and_(Task.pack_id == Pack.pack_id, Task.status == 'wait'))).\
        filter(Pack.notify_count <= notify_count).\
        filter(Pack.pack_id.in_(subquery)).\
        all()
    
    # filter packs used_up 
    
    logging.info(f'notify_complete_packs: {len(filtered_packs)}')
    for pack in filtered_packs:
        pack.total_seconds = 0
        notify_pack(pack)
    db.session.commit()
    

if __name__ == "__main__":
    argparse = argparse.ArgumentParser()
    # args: cmd, --pack, --user,
    argparse.add_argument('--pack', type=int, help='Pack ID')
    argparse.add_argument('--user', type=str, help='User ID')
    argparse.add_argument('--notify_count', type=int, default=0, help='Notify Count')
    argparse.add_argument('--user_since', type=str, help='All new users since')
    argparse.add_argument('--user_activate_since', type=str, help='All new users (not activated) registered since')

    notification_num = 0
    args = argparse.parse_args()

    logging.info(f'args: {args}')

    if args.pack:
        notify_pack(args.pack)
    elif args.user:
        notify_complete_packs(args.notify_count, args.user)
    elif args.user_since:
        users = User.query.filter(User.create_time >= args.user_since).all()
        notify_count = args.notify_count
        subquery = db.session.query(Task.pack_id).\
            filter(Task.status == 'finish').\
            group_by(Task.pack_id).\
            having(db.func.count(Task.id) >= config.COMPLETE_PACK_MIN_PICS).\
            correlate(Pack)
        
        filtered_packs = db.session.query(Pack).\
            filter(~db.exists().where(db.and_(Task.pack_id == Pack.pack_id, Task.status == 'wait'))).\
            filter(Pack.notify_count <= notify_count).\
            filter(Pack.pack_id.in_(subquery)).\
            all()

        for u in users:
            for p in filtered_packs:
                if p.user_id == u.user_id:
                    notify_pack(p)
                    notification_num += 1
                    break
    elif args.user_activate_since:
        # filter all users since
        users_without_persons = db.session.query(User).join(Person, User.id == Person.user_id, isouter=True) \
            .filter(User.create_time >= args.user_activate_since) \
            .filter(Person.id.is_(None)).all()
        for u in users_without_persons:
            send_notification('new_user_activate_2', u.user_id)
            notification_num += 1

    logging.info(f'notification_num: {notification_num}')
"""
    "payload":{    // 必填，JSON格式，具体消息内容(iOS最大为2012B)
        "aps":{    // 必填，严格按照APNs定义来填写
            "alert":""或者{,    // 当content-available=1时(静默推送)，可选; 否则必填
                                // 可为字典类型和字符串类型
                  "title":"title",
                  "subtitle":"subtitle",
                  "body":"body"
             },
            "badge":"xx",    // 可选，取值为N（代表设置角标为N）、+N（代表角标原有基础上+N）、-N（代表角标原有基础上-N）、空字符串（代表清空角标，同N=0）。
            "sound":"xx",    // 可选         
            "content-available":1,    // 可选，代表静默推送     
            "category":"xx",    // 可选，注意: iOS8才支持该字段
            "thread-id":"xx",  // 可选，分组折叠，设置UNNotificationContent的threadIdentifier属性
            "interruption-level": "active" //可选，消息的打扰级别，iOS15起支持，四个选项"passive", "active", "time-sensitive", "critical"
        },
"""
"""
{
    "appkey":"xx",    // 必填，应用唯一标识
    "timestamp":"xx",    // 必填，时间戳，10位或者13位均可，时间戳有效期为10分钟
    "type":"xx",    // 必填，消息发送类型,其值可以为: 
                        // unicast-单播
                        // listcast-列播，要求不超过500个device_token
                        // filecast-文件播，多个device_token可通过文件形式批量发送
                        // broadcast-广播
                        // groupcast-组播，按照filter筛选用户群, 请参照filter参数
                        // customizedcast，通过alias进行推送，包括以下两种case:
                        // -alias: 对单个或者多个alias进行推送
                        // -file_id: 将alias存放到文件后，根据file_id来推送
    "device_tokens":"xx",    // 当type=unicast时, 必填, 表示指定的单个设备
                                      // 当type=listcast时, 必填, 要求不超过500个, 以英文逗号分隔
    "alias_type":"xx",    // 当type=customizedcast时, 必填
                                // alias的类型, alias_type可由开发者自定义, 开发者在SDK中调用setAlias(alias, alias_type)时所设置的alias_type
    "alias":"xx",    // 当type=customizedcast时, 选填(此参数和file_id二选一)
                        // 开发者填写自己的alias, 要求不超过500个alias, 多个alias以英文逗号间隔
                        // 在SDK中调用setAlias(alias, alias_type)时所设置的alias
    "file_id":"xx",    // 当type=filecast时，必填，file内容为多条device_token，以回车符分割
                          // 当type=customizedcast时，选填(此参数和alias二选一)
                          // file内容为多条alias，以回车符分隔。注意同一个文件内的alias所对应的alias_type必须和接口参数alias_type一致。
                          // 使用文件播需要先调用文件上传接口获取file_id，参照"2.4文件上传接口"
    "filter":{},    // 当type=groupcast时，必填，用户筛选条件，如用户标签、渠道等，参考附录G
    "payload":{    // 必填，JSON格式，具体消息内容(iOS最大为2012B)
        "aps":{    // 必填，严格按照APNs定义来填写
            "alert":""或者{,    // 当content-available=1时(静默推送)，可选; 否则必填
                                // 可为字典类型和字符串类型
                  "title":"title",
                  "subtitle":"subtitle",
                  "body":"body"
             },
            "badge":"xx",    // 可选，取值为N（代表设置角标为N）、+N（代表角标原有基础上+N）、-N（代表角标原有基础上-N）、空字符串（代表清空角标，同N=0）。
            "sound":"xx",    // 可选         
            "content-available":1,    // 可选，代表静默推送     
            "category":"xx",    // 可选，注意: iOS8才支持该字段
            "thread-id":"xx",  // 可选，分组折叠，设置UNNotificationContent的threadIdentifier属性
            "interruption-level": "active" //可选，消息的打扰级别，iOS15起支持，四个选项"passive", "active", "time-sensitive", "critical"
        },
        "key1":"value1",    // 可选，用户自定义内容, "d","p"为友盟保留字段,key不可以是"d","p"
        "key2":"value2",
    ...
    },
    "policy":{    // 可选，发送策略
        "start_time":"xx",    // 可选，定时发送时间，若不填写表示立即发送
                                    // 定时发送时间不能小于当前时间
                                    // 格式: "yyyy-MM-dd HH:mm:ss"
                                    // 注意，start_time只对任务生效
        "expire_time":"xx",    // 可选，消息过期时间，其值不可小于发送时间或者
                                      // start_time(如果填写了的话)
                                      // 如果不填写此参数，默认为3天后过期。格式同start_time
        "out_biz_no":"xx",    // 可选，消息发送接口对任务类消息的幂等性保证
                                     // 强烈建议开发者在发送任务类消息时填写这个字段，友盟服务端会根据这个字段对消息做去重避免重复发送
                                     // 同一个appkey下面的多个消息会根据out_biz_no去重，不同发送任务的out_biz_no需要保证不同，否则会出现后发消息被去重过滤的情况
                                     // 注意，out_biz_no只对任务类消息有效
        "apns_collapse_id":"xx"    // 可选，多条带有相同apns_collapse_id的消息，iOS设备仅展示
                                            // 最新的一条，字段长度不得超过64bytes
    },
    "production_mode":"true/false",    // 可选，正式/测试模式。默认为true
                                                    // 广播、组播下的测试模式只会将消息发给测试设备。测试设备需要到web上添加
                                                     // 单播、文件播不受测试设备限制
    "description":"xx"    // 可选，发送消息描述，建议填写接口     
}
"""