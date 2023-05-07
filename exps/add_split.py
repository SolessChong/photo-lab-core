import argparse
import sys
from backend import models
from backend import aliyun_face_detector
from backend.extensions import app, db
from backend import utils
import logging

def add_split_for_person(person_id):
    person = models.Person.query.filter(models.Person.id == person_id).first()
    new_person = models.Person(name=f'{person.name}_with_crop', user_id = person.user_id)
    db.session.add(new_person)
    db.session.commit()

    sources = models.Source.query.filter(models.Source.person_id == person_id, models.Source.base_img_key != None).order_by(models.Source.source_id.desc()).all()
    
    for source in sources:
        logging.info(f'start to get img {source.base_img_key}')
        img = utils.oss_get(source.base_img_key)
        logging.info(f'finish to get img {source.base_img_key}, {len(img)}')

        crop_img = aliyun_face_detector.aliyun_human_segmentation(img)
        if crop_img:
            crop_img_key = f'{source.base_img_key[:-4]}_crop.png'
            utils.oss_put(crop_img_key, crop_img)
            new_source = models.Source(base_img_key=crop_img_key, user_id=source.user_id, type=source.type, person_id=new_person.id)
            db.session.add(new_source)
            db.session.commit()
            logging.info(f'add crop img {crop_img_key} for source {source.source_id}')
        
        new_source = models.Source(base_img_key=source.base_img_key, user_id=source.user_id, type=source.type, person_id=new_person.id)
        db.session.add(new_source)
        db.session.commit()

        # break

# 开始执行main 函数
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--personid', type=int, default=0, help='person id to generate crop images')
    args = parser.parse_args()
    
    app.app_context().push()

    add_split_for_person(args.personid)
