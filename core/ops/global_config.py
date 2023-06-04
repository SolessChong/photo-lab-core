import argparse
import json
import logging
from backend import models
from backend.extensions import db, app

if __name__ == '__main__':
    argparse = argparse.ArgumentParser()
    # args cmd: ['update_types_from_json']
    argparse.add_argument('cmd', type=str, help='update_types_from_json')

    app.app_context().push()

    args = argparse.parse_args()
    if args.cmd == 'update_types_from_json':
        # read json file from backend/data/person_type_data.json
        content = open('backend/data/person_type_data.json', 'r').read()
        gc = models.GlobalConfig.query.filter(models.GlobalConfig.key == 'person_type_data').first()
        gc.value = content
        db.session.commit()
        # read all tags with img_key not None
        all_tags_id = [t.id for t in models.Tag.query.filter(models.Tag.img_key != None).all()]
        # all tags mentioned in the json file 'tags' field
        typed_tags = []
        for item in json.loads(content):
            typed_tags.extend(item['tags'])
        # set subtract
        untyped_tags_id = list(set(all_tags_id) - set(typed_tags))
        logging.info(f'all tags num: {len(all_tags_id)}')
        logging.info(f'untyped_tags_id: {untyped_tags_id}')
