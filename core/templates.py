# Where magic happens

from core import conf

i2i_para_template = {
    'arg1': 'task(z7mdw1573f7sox9)',  # id_task: str
    'arg2': 2,  # mode: int
    'arg3': '',  # prompt: str
    'arg4': '',  # negative_prompt: str
    'arg5': [],  # prompt_styles
    'arg6': None,  # init_img
    'arg7': None,  # sketch
    'arg8': {'image': None, 'mask': None},  # init_img_with_mask PIL.PngImagePlugin.PngImageFile image mode=RGBA
    'arg9': None,  # inpaint_color_sketch
    'arg10': None,  # inpaint_color_sketch_orig
    'arg11': None,  # init_img_inpaint
    'arg12': None,  # init_mask_inpaint
    'arg13': 20,  # steps: int
    'arg14': 16,  # sampler_index: int
    'arg15': 4,  # mask_blur: int
    'arg16': 0,  # mask_alpha: float
    'arg17': 1,  # inpainting_fill: int
    'arg18': True,  # restore_faces: bool
    'arg19': False,  # tiling: bool
    'arg20': 1,  # n_iter: int
    'arg21': 1,  # batch_size: int
    'arg22': 7,  # cfg_scale: float
    'arg23': 1.5,  # image_cfg_scale: float
    'arg24': 0.5,  # denoising_strength: float
    'arg25': -1,  # seed: int
    'arg26': -1.0,  # subseed: int
    'arg27': 0,  # subseed_strength: float
    'arg28': 0,  # seed_resize_from_h: int
    'arg29': 0,  # seed_resize_from_w: int
    'arg30': False,  # seed_enable_extras: bool
    'arg31': 768,  # height: int
    'arg32': 512,  # width: int
    'arg33': 0,  # resize_mode: int
    'arg34': 0,  # inpaint_full_res: bool
    'arg35': 32,  # inpaint_full_res_padding: int
    'arg36': 0,  # inpainting_mask_invert: int
    'arg37': '',  # img2img_batch_input_dir: str
    'arg38': '',  # img2img_batch_output_dir: str
    'arg39': '',  # img2img_batch_inpaint_mask_dir: str
    'arg40': [],  # override_settings_texts
    'arg41': 0,
    'arg42': False,
    'arg43': '',
    'arg44': 0,
    'arg45': None, # ControlNet 1,  <scripts.external_code.ControlNetUnit object at 0x000001F98F732C50>,
    'arg46': None, # <scripts.external_code.ControlNetUnit object at 0x000001F98F732CE0>,
    'arg47': None, # <scripts.external_code.ControlNetUnit object at 0x000001F98F732D70>,
    'arg48': None, # <scripts.external_code.ControlNetUnit object at 0x000001F98F732E00>,
    'arg49': r'<ul>\n<li><code>CFG Scale</code> should be 2 or lower.</li>\n</ul>\n',
    'arg50': True,
    'arg51': True,
    'arg52': '',
    'arg53': '',
    'arg54': True,
    'arg55': 50,
    'arg56': True,
    'arg57': 1,
    'arg58': 0,
    'arg59': False,
    'arg60': 4,
    'arg61': 0.5,
    'arg62': 'Linear',
    'arg63': 'None',
    'arg64': '<p style="margin-bottom:0.75em">Recommended settings: Sampling Steps: 80-100, Sampler: Euler a, Denoising strength: 0.8</p>',
    'arg65': 128,
    'arg66': 8,
    'arg67': ['left', 'right', 'up', 'down'],
    'arg68': 1,
    'arg69': 0.05,
    'arg70': 128,
    'arg71': 4,
    'arg72': 0,
    'arg73': ['left', 'right', 'up', 'down'],
    'arg74': False,
    'arg75': False,
    'arg76': 'positive',
    'arg77': 'comma',
    'arg78': 0,
    'arg79': False,
    'arg80': False,
    'arg81': '',
    'arg82': '<p style="margin-bottom:0.75em">Will upscale the image by the selected scale factor; use width and height sliders to set tile size</p>',
    'arg83': 64,
    'arg84': 0,
    'arg85': 2,
    'arg86': 1,
    'arg87': '',
    'arg88': 0,
    'arg89': '',
    'arg90': 0,
    'arg91': '',
    'arg92': True,
    'arg93': False,
    'arg94': False,
    'arg95': False,
    'arg96': 0,
    'arg97': True,
    'arg98': True,
    'arg99': '',
    'arg100': False,
    'arg101': 1,
    'arg102': 'Both ▦',
    'arg103': False,
    'arg104': '',
    'arg105': False,
    'arg106': True,
    'arg107': True,
    'arg108': False,
    'arg109': False,
    'arg110': False,
    'arg111': False,
    'arg112': 0,
    'arg113': False,
    'arg114': '',
    'arg115': '',
    'arg116': '',
    'arg117': 'generateMasksTab',
    'arg118': 1,
    'arg119': 4,
    'arg120': 2.5,
    'arg121': 30,
    'arg122': 1.03,
    'arg123': 1,
    'arg124': 1,
    'arg125': 5,
    'arg126': 0.5,
    'arg127': 5,
    'arg128': False,
    'arg129': True,
    'arg130': False,
    'arg131': 20,
    'arg132': None,
    'arg133': False,
    'arg134': None,
    'arg135': False,
    'arg136': None,
    'arg137': False,
    'arg138': None,
    'arg139': False,
    'arg140': 50,
    'arg141': False,
    'arg142': '',
    'arg143': '',
    'arg144': 'disable',
    'arg145': 'Custom',
    'arg146': 'HSL',
    'arg147': 'abs(v)',
    'arg148': 'abs(v)',
    'arg149': 'abs(v)',
    'arg150': '(2+v)/3',
    'arg151': '1.0',
    'arg152': '0.5',
    'arg153': 'Auto [0,1]',
    'arg154': -1,
    'arg155': 1,
    'arg156': 1,
    'arg157': 0,
    'arg158': False,
    'arg159': '',
    'arg160': False,
    'arg161': '',
    'arg162': '',
    'arg163': 'disable',
    'arg164': [],
    'arg165': 'Custom',
    'arg166': 'HSL',
    'arg167': 'abs(v)',
    'arg168': 'abs(v)',
    'arg169': 'abs(v)',
    'arg170': '(2+v)/3',
    'arg171': '1.0',
    'arg172': '0.5',
    'arg173': 'Auto [0,1]',
    'arg174': -1,
    'arg175': 1,
    'arg176': 1,
    'arg177': 0,
    'arg178': False,
    'arg179': '',
    'arg180': False,
    'arg181': False,
    'arg182': '',
    'arg183': '',
    'arg184': 'disable',
    'arg185': 'Custom',
    'arg186': 'HSL',
    'arg187': 'abs(v)',
    'arg188': 'abs(v)',
    'arg189': 'abs(v)',
    'arg190': '(2+v)/3',
    'arg191': '1.0',
    'arg192': '0.5',
    'arg193': 'Auto [0,1]',
    'arg194': -1,
    'arg195': 1,
    'arg196': 1,
    'arg197': 0,
    'arg198': False,
    'arg199': '',
    'arg200': False
}

i2i_lut = {
    'id_task': 'arg1',
    'mode': 'arg2',
    'prompt': 'arg3',
    'negative_prompt': 'arg4',
    'prompt_styles': 'arg5',
    'init_img': 'arg6',
    'sketch': 'arg7',
    'init_img_with_mask': 'arg8',
    'inpaint_color_sketch': 'arg9',
    'inpaint_color_sketch_orig': 'arg10',
    'init_img_inpaint': 'arg11',
    'init_mask_inpaint': 'arg12',
    'steps': 'arg13',
    'sampler_index': 'arg14',
    'mask_blur': 'arg15',
    'mask_alpha': 'arg16',
    'inpainting_fill': 'arg17',
    'restore_faces': 'arg18',
    'tiling': 'arg19',
    'n_iter': 'arg20',
    'batch_size': 'arg21',
    'cfg_scale': 'arg22',
    'image_cfg_scale': 'arg23',
    'denoising_strength': 'arg24',
    'seed': 'arg25',
    'subseed': 'arg26',
    'subseed_strength': 'arg27',
    'seed_resize_from_h': 'arg28',
    'seed_resize_from_w': 'arg29',
    'seed_enable_extras': 'arg30',
    'height': 'arg31',
    'width': 'arg32',
    'resize_mode': 'arg33',
    'inpaint_full_res': 'arg34',
    'inpaint_full_res_padding': 'arg35',
    'inpainting_mask_invert': 'arg36',
    'img2img_batch_input_dir': 'arg37',
    'img2img_batch_output_dir': 'arg38',
    'img2img_batch_inpaint_mask_dir': 'arg39',
    'override_settings_texts': 'arg40',
}

LORA_INPAINT_PARAMS = {
    "negative_prompt": "EasyNegative, paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, glans,extra fingers,fewer fingers,strange fingers,bad hand, NSFW, nude, sexy, porn, underwear, big breasts, pussy,",
    "inpainting_fill": 1,
    "inpaint_full_res": False,
    "seed": -1,
    "sampler_name": "DPM++ SDE Karras",
    "restore_faces": True,
    "width": conf.LORA_ROI_RENDERING_SETTINGS['size'][0],
    "height": conf.LORA_ROI_RENDERING_SETTINGS['size'][1],
    "cfg_scale": 7,
    "steps": 50,
    "denoising_strength": 0.4
}

LORA_T2I_PARAMS = {
    "negative_prompt": "EasyNegative, paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, glans,extra fingers,fewer fingers,strange fingers,bad hand, NSFW, nude, sexy, porn, underwear, big breasts, pussy,",
    "seed": -1,
    "sampler_name": "DPM++ SDE Karras",
    "restore_faces": True,
    "width": conf.DIRECT_RENDERING_SETTINGS['size'][0],
    "height": conf.DIRECT_RENDERING_SETTINGS['size'][1],
    "cfg_scale": 7,
    "steps": 30,
}

SD_MODEL_LIST = [
{'title': 'lyriel_v14.safetensors [f1b08b30f8]',
  'model_name': 'lyriel_v14',
  'hash': 'f1b08b30f8',
  'sha256': 'f1b08b30f8bed6de7d19903c86f5ccb936ec24f444b9940a9eeda59d2f5e3c4d',
  'filename': '/home/chong/photolab/stable-diffusion-webui/models/Stable-diffusion/lyriel_v14.safetensors',
  'config': None},
 {'title': 'realisticVisionV20_v20.safetensors',
  'model_name': 'realisticVisionV20_v20',
  'hash': None,
  'sha256': None,
  'filename': '/home/chong/photolab/stable-diffusion-webui/models/Stable-diffusion/realisticVisionV20_v20.safetensors',
  'config': None},
 {'title': 'revAnimated_v121.safetensors [f57b21e57b]',
  'model_name': 'revAnimated_v121',
  'hash': 'f57b21e57b',
  'sha256': 'f57b21e57b3178e4999d719c26f3b3e7e3fe8ef6cb839e2617209063a0ece487',
  'filename': '/home/chong/photolab/stable-diffusion-webui/models/Stable-diffusion/revAnimated_v121.safetensors',
  'config': None},
 {'title': 'sunshinemix_sunlightmixPruned.safetensors',
  'model_name': 'sunshinemix_sunlightmixPruned',
  'hash': None,
  'sha256': None,
  'filename': '/home/chong/photolab/stable-diffusion-webui/models/Stable-diffusion/sunshinemix_sunlightmixPruned.safetensors',
  'config': None},
 {'title': 'YorrrlMixV2.1fp16-no ema-.safetensors',
  'model_name': 'YorrrlMixV2.1fp16-no ema-',
  'hash': None,
  'sha256': None,
  'filename': '/home/chong/photolab/stable-diffusion-webui/models/Stable-diffusion/YorrrlMixV2.1fp16-no ema-.safetensors',
  'config': None},
 {'title': 'cartoonish_v1.safetensors [07f029f6d1]',
  'model_name': 'cartoonish_v1',
  'hash': '07f029f6d1',
  'sha256': '07f029f6d18ebbce4aea6ff741c2f9f9104a614a8ea4dbd6b0f6948333651c0f',
  'filename': '/home/chong/photolab/stable-diffusion-webui/models/Stable-diffusion/cartoonish_v1.safetensors',
  'config': None},
 {'title': 'dosmix_.safetensors [9c59842129]',
  'model_name': 'dosmix_',
  'hash': '9c59842129',
  'sha256': '9c5984212998236a99239ac8ad8d60043206f7625c3ca69943d36c58578223f3',
  'filename': '/home/chong/photolab/stable-diffusion-webui/models/Stable-diffusion/dosmix_.safetensors',
  'config': None},
 {'title': 'dreamshaper_4BakedVaeFp16.safetensors [db2c51c333]',
  'model_name': 'dreamshaper_4BakedVaeFp16',
  'hash': 'db2c51c333',
  'sha256': 'db2c51c33339792df6baf443710c525440ce2e67617641368dd1688d57925926',
  'filename': '/home/chong/photolab/stable-diffusion-webui/models/Stable-diffusion/dreamshaper_4BakedVaeFp16.safetensors',
  'config': None},
 {'title': 'chilloutmix_NiPrunedFp16Fix.safetensors [59ffe2243a]',
  'model_name': 'chilloutmix_NiPrunedFp16Fix',
  'hash': '59ffe2243a',
  'sha256': '59ffe2243a25c9fe137d590eb3c5c3d3273f1b4c86252da11bbdc9568773da0c',
  'filename': '/home/chong/photolab/stable-diffusion-webui/models/Stable-diffusion/chilloutmix_NiPrunedFp16Fix.safetensors',
  'config': None}]

PROMPT_PHOTO = ",(8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37),professional lighting, photon mapping, radiosity, physically-based rendering,"

UPSCALER_DEFAULT = {
    "upscaler_1": "ESRGAN_4x",
    "upscaler_2": "R-ESRGAN 4x+",
    "extras_upscaler_2_visibility": 0.2
}

UPSCALER_ANIME = {
    "upscaler_1": "ESRGAN_4x",
    "upscaler_2": "R-ESRGAN 4x+ Anime6B",
    "extras_upscaler_2_visibility": 0.5
}

PROMPT_PARAMS = {
    'CHAR_ATTENTION': 1,
}

def make_params(template, lut, **kwargs):
    for k, v in kwargs.items():
        if k in lut:
            template[lut[k]] = v
    params = [template[f'arg{i + 1}'] for i in range(len(template.items()))]
    return params

