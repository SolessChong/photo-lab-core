# Features
## Task View
Show all tasks. Task info is shown in data panel. All task shown in two column flow view.

## Create task view
1. List distinct "collection_name" in Scene table.
1. Dropdown, list all persons, with `id` and `name` fields in User table.
1. Generate button, generate task with selected collection, specified by `collection_name` and person, by `id`.
1. In the backend request for generate, params: (collection_name, person_id): 
    1. Filter all scenes with `collection_name`
    1. Create a new task with `person_id` and `collection_name`, save all these task id's in a list.
    1. Send out celery task for all these tasks
        1. create list of set_up_scene tasks: 
            `group([signature('set_up_scene', (scene.scene_id,)) for scene in scene_list])`
        2. create list of render_scene tasks:
            `group([signature('render_scene', (task_id,), immutable=True) for task_id in task_id_list])`
        3. Assemble a celery.chain:
            ```
            ch = chain(
                group([signature('set_up_scene', (scene.scene_id,)) for scene in scene_list]),
                group([signature('render_scene', (task_id,), immutable=True) for task_id in task_id_list])
            )
            ```

## Scene edit view
1. Show scene info in a complete row. Card layout.
1. In each row, list the scene base_img at the left most position.
1. In each row, next to base_img, is hint_img, if exists.
1. In each row, list all the tasks for this scene, in a horizontal flow layout. `Task.scene_id == scene.scene_id` is the filter.
1. Also show the additional info of scene:
    1. `scene.scene_id`
    1. `scene.collection_name`
    1. `scene.prompt`
    1. `scene.params`, a json string, show in a json editor, with expandable tree view, editable each field. Save button to update this field. If frontend editor is empty, save python none (Mysql NULL) object for this.
    1. `scene.rate`, a int. Add 'add', 'minus' button for this field, click will add or minus 1, update the db.


## Utils
Image url: https://photolab-test.oss-cn-shenzhen.aliyuncs.com/ + image's some `key` field in db.









## GPT Prompt:
Please complete the scene edit view according to the doc, including all the api from backend, linking to FE, covering all the fields editable in the doc.

## Scene edit view
1. Show scene info in a complete row. Card layout.
1. In each row, list the scene base_img at the left most position.
1. In each row, next to base_img, is hint_img, if exists.
1. In each row, list all the tasks for this scene, in a horizontal flow layout. `Task.scene_id == scene.scene_id` is the filter.
1. Also show the additional info of scene:
    1. `scene.scene_id`
    1. `scene.collection_name`
    1. `scene.prompt`
    1. `scene.params`, a json string, show in a json editor, with expandable tree view, editable each field. Save button to update this field. If frontend editor is empty, save python none (Mysql NULL) object for this.
    1. `scene.rate`, a int. Add 'add', 'minus' button for this field, click will add or minus 1, update the db.


## Utils
Image url: https://photolab-test.oss-cn-shenzhen.aliyuncs.com/ + image's some `key` field in db.

My previous code for api is like this:

```
import os
import oss2
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from backend.extensions import  app, db
from flask_cors import CORS
from backend.models import User, Source, Person, GeneratedImage, Pack, Scene, Task
from celery import Celery, chain, chord, group, signature
from backend.config import CELERY_CONFIG

@app.route('/list_tasks', methods=['GET'])
def list_tasks():
    tasks = Task.query.all()
    task_list = [{'task_id': task.id, 'result_img_key': f'https://photolab-test.oss-cn-shenzhen.aliyuncs.com/{task.result_img_key}'} for task in tasks]
    return jsonify(task_list)
```

Scene is defined like this:
```

class Scene(db.Model):
    __tablename__ = 'scenes'

    scene_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    img_url = db.Column(db.String(2000), nullable=True)
    prompt = db.Column(db.Text, nullable=True)
    action_type = db.Column(db.String(255), nullable=False, comment='type包括mj,reface, sd等。\r\n如果是mj，直接调用prompt生成图片\r\n如果是reface，直接与上传的头像图片进行换脸\r\n')
    img_type = db.Column(db.String(255), nullable=False, comment='图片类型，包括男生、女生、多人、猫、狗')
    rate = db.Column(db.Float, nullable=True, comment='推荐评分，从0-10分，可以有小数点\r\n')
    
    name = db.Column(db.String(255), nullable=True)
    base_img_key = db.Column(db.String(2550), nullable=True)
    hint_img_list = db.Column(db.JSON, nullable=True)
    setup_status = db.Column(db.String(255), nullable=True)
    roi_list = db.Column(db.JSON, nullable=True)
    model_name = db.Column(db.String(2550), nullable=True)
    negative_prompt = db.Column(db.Text, nullable=True)
    params = db.Column(db.JSON, nullable=True)  # usually dict
    collection_name = db.Column(db.String(255), nullable=True)
    tags = db.Column(db.String(255), nullable=True)
    
    def update_pose_img(self, pose_img_url):
        if self.hint_img_list is None:
            self.hint_img_list = [pose_img_url]
        else:
            self.hint_img_list[0] = pose_img_url
        db.session.commit()

    def get_pose_img(self):
        if self.hint_img_list is None:
            return None
        return self.hint_img_list[0]
    
    def update_setup_status(self, setup_status):
        self.setup_status = setup_status
        db.session.commit()
```