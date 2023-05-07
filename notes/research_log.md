## 0505
同照片美化：表情，松弛感，氛围
人物多样化：宝妈，动物
## 0506
CFG: try larger than 7

## 0507 
Dataset Quality
- Introduce quality measure, 
    - but not all the good dataset generate good Lora.
        - E.g. 272: 
            ```
            Dataset Quality: {
                "background_variety": 0.7813114420572916,
                "blurriness": 0.5205774658443018,
                "face_pose_variety": 0.6666113046499399,
                "jpeg_compression": 0.6682560024783015,
                "lighting": 0.5546059608459473,
                "num_score": 0
            }
            ```
        - E.g. 263:
            ```
            Dataset Quality: {
                "background_variety": 0.9553107706705728,
                "blurriness": 1.2803481708783877,
                "face_pose_variety": 0.8282191936786358,
                "jpeg_compression": 0.7613012697547674,
                "lighting": 0.5602251172065735,
                "num_score": 0
            }
            ···
    - Some good examples:
        - 胖妞
            ···
            ID: 226
            Name: hAL3kCJFQ4_1683369653866
            Lora Train Status: finish
            Dataset Quality: {
                "background_variety": 0.8636626180013021,
                "blurriness": 0.10039523582970428,
                "face_pose_variety": 0.8864937562208909,
                "jpeg_compression": 0.1873522207606584,
                "lighting": 0.5080103278160095,
                "num_score": 0
            }
            ···