async function loadUserResults(userIds) {
    const container = document.querySelector('#user-result-container');
    container.innerHTML = '';

    for (const userId of userIds) {
        try {
            const response = await fetch(`http://photolab.aichatjarvis.com/api/get_generated_images?user_id=${userId}`);
            const data = await response.json();

            for (const pack of data.data.packs) {
                // Create pack card
                const packCard = document.createElement('div');
                packCard.className = 'card mb-3';
                container.appendChild(packCard);

                // Create pack card body
                const cardBody = document.createElement('div');
                cardBody.className = 'card-body';
                packCard.appendChild(cardBody);

                // Add user ID, pack ID and pack description
                const infoRow = document.createElement('div');
                infoRow.className = 'row';
                cardBody.appendChild(infoRow);

                const userIdElement = document.createElement('div');
                userIdElement.className = 'col-md-4 mb-2';
                userIdElement.innerHTML = `<h5 class="card-title mb-0">User ID: ${userId}</h5>`;
                infoRow.appendChild(userIdElement);

                const packId = document.createElement('div');
                packId.className = 'col-md-4 mb-2';
                packId.innerHTML = `<h5 class="card-title mb-0">Pack ID: ${pack.pack_id}</h5>`;
                infoRow.appendChild(packId);

                const packDescription = document.createElement('div');
                packDescription.className = 'col-md-4 mb-2';
                packDescription.innerHTML = `<h5 class="card-title mb-0">Description: ${pack.description}</h5>`;
                infoRow.appendChild(packDescription);

                // Add pack photos container
                const photosContainer = document.createElement('div');
                photosContainer.className = 'd-flex flex-row flex-wrap';
                cardBody.appendChild(photosContainer);

                pack.imgs.forEach((imgUrl, index) => {
                    const photo = document.createElement('img');
                    const photoSrc = imgUrl;

                    // Add FancyBox functionality
                    const lightboxLink = document.createElement('a');
                    lightboxLink.href = photoSrc;
                    lightboxLink.setAttribute('data-fancybox', `gallery-${pack.pack_id}`);
                    photosContainer.appendChild(lightboxLink);

                    // Configure the thumbnail image
                    photo.src = photoSrc;
                    photo.className = 'img-thumbnail me-2 mb-2';
                    photo.style.width = 'calc(100% / 3 - 10px)';
                    lightboxLink.appendChild(photo);

                    // Add clearfix after every third image
                    if ((index + 1) % 3 === 0) {
                        const clearfix = document.createElement('div');
                        clearfix.className = 'w-100';
                        photosContainer.appendChild(clearfix);
                    }
                });
            }
        } catch (error) {
            console.error('Error fetching user results:', error);
        }
    }
}




async function loadAllUserIds() {
    try {
        const response = await fetch('/get_all_user');
        const data = await response.json();
        const sortedUserIds = data.data.user_ids;
        const userSelect = document.querySelector('#user-select');

        // Clear the default option
        userSelect.innerHTML = '';

        sortedUserIds.forEach(userId => {
            const option = document.createElement('option');
            option.value = userId;
            option.textContent = userId;
            userSelect.appendChild(option);
        });

        // Load the first 20 user IDs by default
        loadUserResults(sortedUserIds.slice(0, 20));
    } catch (error) {
        console.error('Error fetching all user IDs:', error);
    }
}


function loadSceneEditData(page, collection_name_filter='') {
    const url = `/list_scenes?page=${page}&collection_name_filter=${encodeURIComponent(collection_name_filter)}`;
    fetch(url)
        .then(response => response.json())
        .then(data => {
            const scenes = data.scenes;
            const total_pages = data.total_pages;
            const container = document.querySelector('#scene-edit-data');
            container.innerHTML = '';

            scenes.forEach(scene => {
                const sceneRow = document.createElement('div');
                sceneRow.className = 'row scene-row';
                container.appendChild(sceneRow);

                 // Add base_img
                 const baseImgCol = document.createElement('div');
                 baseImgCol.className = 'col-2';
                 const baseImg = document.createElement('img');
                 baseImg.src = `https://photolab-test.oss-cn-shenzhen.aliyuncs.com/${scene.base_img_key}`;
                 baseImg.className = 'img-thumbnail';
                 baseImgCol.appendChild(baseImg);
                 sceneRow.appendChild(baseImgCol);

                 // Add hint_img if exists
                 if (scene.hint_img_list && scene.hint_img_list.length > 0) {
                     const hintImgCol = document.createElement('div');
                     hintImgCol.className = 'col-2';
                     const hintImg = document.createElement('img');
                     hintImg.src = `https://photolab-test.oss-cn-shenzhen.aliyuncs.com/${scene.hint_img_list[0]}`;
                     hintImg.className = 'img-thumbnail';
                     hintImgCol.appendChild(hintImg);
                     sceneRow.appendChild(hintImgCol);
                 }

                 // Fetch tasks for this scene
                 fetch(`/list_tasks/${scene.scene_id}`)
                     .then(response => response.json())
                     .then(tasks => {
                         const tasksCol = document.createElement('div');
                         tasksCol.className = 'col';
                         sceneRow.appendChild(tasksCol);
                         tasks.forEach(task => {
                             const taskImgLink = document.createElement('a');
                             taskImgLink.href = task.result_img_key; // Original size for FancyBox
                             taskImgLink.setAttribute('data-fancybox', `gallery-${scene.scene_id}`);
                             tasksCol.appendChild(taskImgLink);

                             const taskImg = document.createElement('img');
                             taskImg.src = `${task.result_img_key}?x-oss-process=image/resize,w_400`; // Preview with width 400px
                             taskImg.className = 'task-img';
                             taskImgLink.appendChild(taskImg);
                         });
                     });


                // Add additional scene info and editable fields
                const sceneInfo = document.createElement('div');
        
                // Add collection name
                const collectionNameRow = document.createElement('div');
                collectionNameRow.style.display = 'flex';
                collectionNameRow.style.alignItems = 'center';
                collectionNameRow.style.justifyContent = 'space-between';
                collectionNameRow.style.flexWrap = 'nowrap';

                const collectionNameLabel = document.createElement('span');
                collectionNameLabel.innerHTML = '<strong>Collection Name:</strong>';
                collectionNameRow.appendChild(collectionNameLabel);

                console.log(scene.collection_name)

                const collectionNameInput = document.createElement('input');
                collectionNameInput.type = 'text';
                collectionNameInput.id = `collection-name-${scene.scene_id}`;
                collectionNameInput.value = scene.collection_name;
                collectionNameInput.style.width = '80%';
                collectionNameRow.appendChild(collectionNameInput);

                const saveCollectionNameButton = document.createElement('button');
                saveCollectionNameButton.innerHTML = 'Save Collection Name';
                saveCollectionNameButton.style.display = 'none';
                saveCollectionNameButton.onclick = function() {
                    const url = `/update_scene_collection_name?scene_id=${scene.scene_id}&collection_name=${encodeURIComponent(collectionNameInput.value)}`;
                    fetch(url)
                        .then(response => response.json())
                        .then(data => {console.log(data);alert('Collection Name updated!');})  // handle the response here
                        .catch(error => console.error('Error:', error));
                };
                collectionNameRow.appendChild(saveCollectionNameButton);

                collectionNameInput.addEventListener('input', function() {
                    if (this.value !== scene.collection_name) {
                        saveCollectionNameButton.style.display = 'block';
                    } else {
                        saveCollectionNameButton.style.display = 'none';
                    }
                });

                sceneInfo.appendChild(collectionNameRow);

                
                // Fetch tags for this scene
                fetch(`/get_scene_tag_list/${scene.scene_id}`)
                    .then(response => response.json())
                    .then(data => {
                        const tags = data.tag_list;

                        const tagsRow = document.createElement('div');
                        tagsRow.style.gap = '10px';
                        
                        sceneInfo.appendChild(tagsRow);
                        tags.forEach(tag => {
                            const tagInput = document.createElement('input');
                            tagInput.type = 'text';
                            tagInput.oninput = function() {
                                showApplyButtons();
                            };
                            tagInput.value = tag;
                            tagsRow.appendChild(tagInput);
                        });
                        const addTagButton = document.createElement('button');
                        addTagButton.innerHTML = 'Add Tag';
                        addTagButton.buttonsAdded = false; // Custom property to track whether buttons have been added
                        addTagButton.onclick = function() {
                            const newTagInput = document.createElement('input');
                            newTagInput.type = 'text';
                            tagsRow.appendChild(newTagInput);
                            
                            showApplyButtons();
                        };

                        function showApplyButtons() {
                            if (addTagButton.buttonsAdded) return;
                            addTagButton.buttonsAdded = true;
                
                            // Create Apply Scene button
                            const applySceneButton = document.createElement('button');
                            applySceneButton.innerHTML = 'Apply Scene';
                            applySceneButton.onclick = function() {
                                const newTagList = Array.from(tagsRow.querySelectorAll('input')).map(input => input.value);
                                updateTag(scene.scene_id, newTagList, false);
                            };
                            sceneInfo.appendChild(applySceneButton);
                
                            // Create Apply Collection button
                            const applyCollectionButton = document.createElement('button');
                            applyCollectionButton.innerHTML = 'Apply Collection';
                            applyCollectionButton.onclick = function() {
                                const newTagList = Array.from(tagsRow.querySelectorAll('input')).map(input => input.value);
                                updateTag(scene.scene_id, newTagList, true);
                            };
                            sceneInfo.appendChild(applyCollectionButton);
                        }

                        tagsRow.appendChild(addTagButton);

                    });
                

                // Add prompt
                const promptLabel = document.createElement('p');
                promptLabel.innerHTML = '<strong>Prompt:</strong>';
                sceneInfo.appendChild(promptLabel);

                const promptTextarea = document.createElement('textarea');
                promptTextarea.id = `prompt-${scene.scene_id}`;
                promptTextarea.rows = '4';
                promptTextarea.style.width = '100%';
                promptTextarea.textContent = scene.prompt;
                sceneInfo.appendChild(promptTextarea);

                const savePromptButton = document.createElement('button');
                savePromptButton.textContent = 'Save Prompt';
                savePromptButton.onclick = function() {
                    updateScenePrompt(scene.scene_id);
                };
                sceneInfo.appendChild(savePromptButton);

                // Add params
                const paramsLabel = document.createElement('p');
                paramsLabel.innerHTML = '<strong>Params:</strong>';
                sceneInfo.appendChild(paramsLabel);

                const paramsTextarea = document.createElement('textarea');
                paramsTextarea.id = `params-${scene.scene_id}`;
                paramsTextarea.rows = '4';
                paramsTextarea.style.width = '100%';
                paramsTextarea.textContent = JSON.stringify(scene.params, null, 2);
                sceneInfo.appendChild(paramsTextarea);

                const saveParamsButton = document.createElement('button');
                saveParamsButton.textContent = 'Save Params';
                saveParamsButton.onclick = function() {
                    updateSceneParams(scene.scene_id);
                };
                sceneInfo.appendChild(saveParamsButton);

                // Add rate
                const rateRow = document.createElement('div');
                // rateRow.style.display = 'flex';
                // rateRow.style.alignItems = 'center';
                // rateRow.style.justifyContent = 'space-between';
                // rateRow.style.flexWrap = 'nowrap';

                const rateLabel = document.createElement('span');
                rateLabel.innerHTML = '<strong>Rate:</strong>';
                rateRow.appendChild(rateLabel);

                const rateInput = document.createElement('input');
                rateInput.type = 'number';
                rateInput.id = `rate-${scene.scene_id}`;
                rateInput.value = scene.rate;
                // rateInput.style.width = '80%';
                rateRow.appendChild(rateInput);

                const saveRateButton = document.createElement('button');
                saveRateButton.innerHTML = 'Save Rate';
                saveRateButton.style.display = 'none';
                saveRateButton.onclick = function() {
                    const url = `/update_scene_rate?scene_id=${scene.scene_id}&rate=${encodeURIComponent(rateInput.value)}`;
                    fetch(url)
                        .then(response => response.json())
                        .then(data => {
                            console.log(data); 
                            alert(JSON.stringify(data));
                        })  // handle the response here
                        .catch(error => console.error('Error:', error));
                };
                rateRow.appendChild(saveRateButton);

                rateInput.addEventListener('input', function() {
                    if (this.value !== scene.rate) {
                        saveRateButton.style.display = 'block';
                    } else {
                        saveRateButton.style.display = 'none';
                    }
                });
                sceneInfo.appendChild(rateRow);

                sceneRow.appendChild(sceneInfo);
            });

            if (currentScenePage >= total_pages) {
                document.getElementById('load-more-scenes').style.display = 'none';
            }
        })
        .catch(error => console.error('Error fetching scenes:', error));
}


function updateTag(sceneId, newTagList, isCollection) {
    const url = `/update_tag/${sceneId}?tags=${encodeURIComponent(newTagList.join(','))}&is_collection=${isCollection}`;
    fetch(url, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log(data);
            alert('Tag updated!');
            // Handle data or errors here...
        })
        .catch(error => console.error('Error updating tag:', error));
}
