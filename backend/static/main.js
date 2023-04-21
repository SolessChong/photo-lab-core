// 获取场景并展示
async function getScenes() {
    const response = await fetch('/get_scenes');
    const scenes = await response.json();

    const sceneContainer = document.getElementById('scene-container');
    sceneContainer.innerHTML = '';

    const promptContainer = document.getElementById('prompt-container');
    promptContainer.innerHTML = '';

    scenes.forEach(scene => {
        if (scene.signed_url) {
            // 在 Scene Tab 下
            const sceneItem = document.createElement('div');
            sceneItem.className = 'scene-item';

            const img = document.createElement('img');
            img.src = scene.signed_url;
            img.style.maxWidth = '100%';
            img.style.height = 'auto';
            img.style.borderRadius = '10px';
            sceneItem.appendChild(img);

            const sceneDetails = document.createElement('div');
            sceneDetails.className = 'scene-details';

            const actionTypeLabel = document.createElement('span');
            actionTypeLabel.className = 'label';
            actionTypeLabel.innerText = 'Action Type:   ';
            sceneDetails.appendChild(actionTypeLabel);

            const actionType = document.createElement('span');
            actionType.className = 'editable';
            actionType.contentEditable = 'true';
            actionType.innerText = scene.action_type;
            sceneDetails.appendChild(actionType);

            const imgTypeLabel = document.createElement('span');
            imgTypeLabel.className = 'label';
            imgTypeLabel.innerText = 'Img Type:   ';
            sceneDetails.appendChild(imgTypeLabel);

            const imgType = document.createElement('span');
            imgType.className = 'editable';
            imgType.contentEditable = 'true';
            imgType.innerText = scene.img_type;
            sceneDetails.appendChild(imgType);

            const rateLabel = document.createElement('span');
            rateLabel.className = 'label';
            rateLabel.innerText = 'Rate:   ';
            sceneDetails.appendChild(rateLabel);

            const rate = document.createElement('span');
            rate.className = 'editable';
            rate.contentEditable = 'true';
            rate.innerText = scene.rate;
            sceneDetails.appendChild(rate);

            sceneItem.appendChild(sceneDetails);
            sceneContainer.appendChild(sceneItem);
        } else {
            // 在 Prompt Tab 下展示没有 signed_url 的场景
            const promptItem = document.createElement('div');
            promptItem.className = 'prompt-item';

            const promptDetails = document.createElement('div');
            promptDetails.className = 'prompt-details';

            const promptLabel = document.createElement('span');
            promptLabel.className = 'label';
            promptLabel.innerText = 'Prompt:   ';
            promptDetails.appendChild(promptLabel);

            const prompt = document.createElement('span');
            prompt.className = 'editable prompt-text';
            prompt.contentEditable = 'true';
            prompt.innerText = scene.prompt;
            promptDetails.appendChild(prompt);

            const imgTypeLabel = document.createElement('span');
            imgTypeLabel.className = 'label';
            imgTypeLabel.innerText = 'Img Type:   ';
            promptDetails.appendChild(imgTypeLabel);

            const imgType = document.createElement('span');
            imgType.className = 'editable';
            imgType.contentEditable = 'true';
            imgType.innerText = scene.img_type;
            promptDetails.appendChild(imgType);

            promptItem.appendChild(promptDetails);
            promptContainer.appendChild(promptItem);
        }
    });
}

async function updateScene(sceneId, actionType, rate, prompt) {
    const response = await fetch(`/update_scene`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ scene_id: sceneId, action_type: actionType, rate: rate, prompt: prompt })
    });

    if (response.ok) {
        alert('修改成功');
        getImages();
    } else {
        alert('修改失败');
    }
}

// 上传图片
document.getElementById('upload-form').addEventListener('submit', async function (event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const imgType = formData.get("img_type");
    let apiUrl = '/upload_scene';

    if (imgType === 'source') {
        apiUrl = '/api/upload_source';
    }

    // 获取所选文件
    const files = event.target.elements.img_file.files;

    // 逐个上传文件
    for (const file of files) {
        const currentFormData = new FormData();
        currentFormData.append("img_file", file);
        currentFormData.append("action_type", formData.get("action_type"));
        currentFormData.append("img_type", formData.get("img_type"));
        currentFormData.append("prompt", formData.get("prompt"));
        currentFormData.append("rate", formData.get("rate"));
        currentFormData.append("user_id", formData.get("user_id"));
        currentFormData.append("user_id", formData.get("user_id"));
        currentFormData.append("collection_name", formData.get("collection_name"));

        const response = await fetch(apiUrl, {
            method: 'POST',
            body: currentFormData
        });

        if (response.ok) {
            alert('图片上传成功');
            // 如果有其他更新图片列表的函数，请在这里调用
        } else {
            alert('图片上传失败');
        }
    }
});

async function getSourceImages() {
    const response = await fetch('/api/get_source?user_id=michaelfeng007');
    const sources = await response.json();
    const container = document.getElementById('user_face');
    container.innerHTML = '';

    sources.forEach(source => {
        const item = document.createElement('div');
        item.className = 'image-item';

        const img = document.createElement('img');
        img.src = source.img_url;
        item.appendChild(img);

        // 创建按钮
        const generateButton = document.createElement('button');
        generateButton.innerHTML = '启动生成图片';
        generateButton.dataset.sourceId = source.source_id;
        generateButton.dataset.userId = source.user_id;
        generateButton.dataset.type = source.type;
        generateButton.onclick = (event) => startGenerate(event.target.dataset.sourceId, event.target.dataset.userId, event.target.dataset.type);
        item.appendChild(generateButton);

        const showGeneratedButton = document.createElement('button');
        showGeneratedButton.innerHTML = '展示已生成图片';
        showGeneratedButton.dataset.userId = source.user_id;
        showGeneratedButton.onclick = (event) => showGeneratedImages(event.target.dataset.userId);
        item.appendChild(showGeneratedButton);

        container.appendChild(item);
    });
}

async function startGenerate(sourceId, userId, type) {
    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('source_id', sourceId);
    formData.append('type', type);
    const response = await fetch('/api/start_generate', {
        method: 'POST',
        body: formData
    });
    const result = await response.json();
    alert(result.message);
}

async function showGeneratedImages(userId) {
    const response = await fetch('/api/get_generated_images?user_id=' + userId);
    const data = await response.json();
    const container = document.getElementById('blind-box-results');
    container.innerHTML = '';

    data.packs.forEach(pack => {
        pack.imgs.forEach(url => {
            const item = document.createElement('div');
            item.className = 'image-item';
            const img = document.createElement('img');
            img.src = url;
            img.width = 200;
            item.append(img)
            container.appendChild(item);
        });
        container.appendChild(document.createElement('br'));
        // const remainingImagesText = document.createElement('span');
        // remainingImagesText.innerText = `还有 ${pack.total_img_num - pack.imgs.length} 张图片在合成中`;
        // container.appendChild(remainingImagesText);
    });
}

function switchTab(tabName) {
    // 切换选项卡
    let tabs = document.querySelectorAll('.tab');
    for (let tab of tabs) {
        tab.classList.remove('active');
    }
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // 切换内容
    let tabContents = document.querySelectorAll('.tab-content');
    for (let tabContent of tabContents) {
        tabContent.classList.remove('active');
    }
    document.getElementById(`${tabName}-content`).classList.add('active');
}
getScenes();
getSourceImages();