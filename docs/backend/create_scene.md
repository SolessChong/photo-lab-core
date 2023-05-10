Please write a tab to create scene, 
1. prompt text area, params text area, negative_prompt text area
2. image upload control for "base_img_key", backend fake_app.py will receive that file and upload to oss, return the key, save to db. Reference is below 'upload_new_scene' fn.
3. collection name text input
4. action_type dropdown, "sd" or "mj" or "reface"
5. img_type dropdown, "girl", "boy"
6. Text label prompt for each input field
7. Create Scene button that creates a scene, display id in frontend upon success.
8. Copy from feature, enter scene id, click load, it loads that scene's info but image key to this UI, for faster creation.


I have upload scene function defined in 'core.ops.upload_scene' that you can use as referrence: 
```
def upload_new_scene(fn):
    logging.info(f"Uploading {fn}")
    img = Image.open(file_path + '/' + fn)
    
    img_key = oss_path + collection_name + '/' + fn
    # change extension from any to .png
    img_key = img_key.split('.')[0] + '.png'

    write_PILimg(img, img_key)

    scene = models.Scene(
        base_img_key=img_key,
        prompt=prompt,
        action_type="sd",
        img_type="girl",
        negative_prompt=negative_prompt,
        params=params,
        collection_name=collection_name,
        setup_status="wait",
    )

    db.session.add(scene)
    db.session.commit()
    db.session.close()
```
Please refer to this api to write new api.

Current HTML for tab like this:

```
    <ul class="nav nav-tabs" id="mainTabs" role="tablist">
        <li class="nav-item" role="presentation">
            <a class="nav-link" id="dashboard-tab" data-bs-toggle="tab" href="#dashboard" role="tab"
                aria-controls="dashboard" aria-selected="false">Dashboard</a>
        </li>
        ...
    </ul>
    <div class="tab-content" id="mainTabsContent">
        <div class="tab-pane fade" id="dashboard" role="tabpanel" aria-labelledby="dashboard-tab">
        </div>
        ...
    </div>
```

My model is defined like this in Flask: 
```
class Scene(db.Model):
    __tablename__ = 'scenes'

    scene_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    img_url = db.Column(db.String(2000), nullable=True)
    prompt = db.Column(db.Text, nullable=True)
    action_type = db.Column(db.String(255), nullable=False, comment='type包括mj,reface, sd等。\r\n如果是mj，直接调用prompt生成图片\r\n如果是reface，直接与上传的头像图片进行换脸\r\n')
    img_type = db.Column(db.String(255), nullable=False, comment='图片类型，包括男生、女生、多人、猫、狗')
    rate = db.Column(db.Float, nullable=True, default=0, comment='推荐评分，从0-10分，可以有小数点\r\n')
    
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
    
```