// Load all tags
function loadTags() {
  console.log('Loading tags...')
    $.get('/api/get_all_tags', function(response) {
      if (response.code === 0) {
        const tags = response.data;
        const tagSelect = document.getElementById('tag-select');
  
        // Clear existing options
        tagSelect.innerHTML = '<option value="" selected>Select a Tag</option>';
  
        // Add options for each tag
        tags.forEach(function(tag) {
          const option = document.createElement('option');
          option.value = tag.id;
          option.textContent = tag.tag_name;
          tagSelect.appendChild(option);
        });
      } else {
        console.error('Failed to fetch tags:', response.msg);
      }
    });
  }
  
// Filter scenes by selected tag
function filterScenesByTag(tagId) {
  $.post({
    url: '/api/filter_scenes_by_tag',
    data: JSON.stringify({ tag_id: tagId }),
    contentType: 'application/json',
    dataType: 'json',
    success: function(response) {
      console.log('Filtering scenes by tag...' + tagId);
      if (response.code === 0) {
        const scenes = response.scenes;
        const tag = response.tag;
        const tagImage = document.getElementById('tag-image');
        const tagImageContainer = document.getElementById('tag-image-container');
        const ossPrefix = 'https://photolab-test.oss-cn-shenzhen.aliyuncs.com/';

        // Clear existing image and hide container if no scenes
        tagImage.src = '';
        tagImageContainer.style.display = scenes.length > 0 ? 'block' : 'none';

        if (scenes.length > 0) {
          const imgKey = response.tag_img_key;
          const imageUrl = ossPrefix + imgKey;
          tagImage.src = imageUrl;
          tagImage.alt = 'Tag Image';

          scenes.forEach(scene => {
            let imgElement = document.createElement('img');
            imgElement.src = ossPrefix + scene.img_key;
            imgElement.alt = 'Scene Image';
            tagImageContainer.appendChild(imgElement);
          });
        }

        // Set tag fields
        document.getElementById('tag-id').value = tag.tag_id;
        document.getElementById('tag-name').value = tag.tag_name;
        document.getElementById('tag-rate').value = tag.tag_rate;

      } else {
        console.error('Failed to filter scenes by tag:', response.msg);
      }
    },
    error: function(xhr, status, error) {
      console.error('Error filtering scenes by tag:', error);
    }
  });
}


  // Upload tag image
function uploadTagImage() {
  const fileInput = document.getElementById('upload-tag-image');
  const file = fileInput.files[0];
  const tagName = document.getElementById('tag-name').value;
  console.log('Uploading tag image...');

  if (file && tagName) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('tag_name', tagName);

      $.ajax({
          url: '/upload_tag_image',
          type: 'POST',
          data: formData,
          processData: false,
          contentType: false,
          success: function(response) {
              if (response.success) {
                  console.log('Tag image uploaded successfully');
              } else {
                  console.error('Failed to upload tag image:', response.error);
              }
          },
          error: function(error) {
              console.error('Failed to upload tag image:', error);
          }
      });
  }
}

  

  // Initialize Tags Tab
function initializeTagsTab() {
  loadTags();

  const tagSelect = document.getElementById('tag-select');
  const tagImage = document.getElementById('tag-image');
  const tagImageContainer = document.getElementById('tag-image-container');
  const tagIdInput = document.getElementById('tag-id');
  const tagNameInput = document.getElementById('tag-name');
  const tagRateInput = document.getElementById('tag-rate');
  const uploadImageButton = document.getElementById('upload-image-btn');

  // Handle tag select change event
  tagSelect.addEventListener('change', function(event) {
    const selectedTagId = event.target.value;
    if (selectedTagId) {
      filterScenesByTag(selectedTagId);
    }
  });

  // Handle upload image button click event
  uploadImageButton.addEventListener('click', function() {
    uploadTagImage();
  });

  // Show the first tag's image (if available)
  const firstTagOption = tagSelect.querySelector('option');
  if (firstTagOption) {
    const firstTagId = firstTagOption.value;
    filterScenesByTag(firstTagId);
  }

  // Clear tag fields when the image is changed
  tagImage.addEventListener('change', function() {
    tagIdInput.value = '';
    tagNameInput.value = '';
    tagRateInput.value = '';
  });

  // Show/hide tag fields when image container is clicked
  tagImageContainer.addEventListener('click', function() {
    const isTagFieldsHidden = tagIdInput.value === '' && tagNameInput.value === '' && tagRateInput.value === '';
    const displayValue = isTagFieldsHidden ? 'block' : 'none';
    tagIdInput.style.display = displayValue;
    tagNameInput.style.display = displayValue;
    tagRateInput.style.display = displayValue;
  });
}


$(document).ready(function() {
  console.log('Document ready.');
  initializeTagsTab();
});