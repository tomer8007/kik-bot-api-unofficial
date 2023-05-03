"""
Here we put all the device configuration that we emulate.
"""

from kik_unofficial.configuration import env

# possible kik versions to emulate
kik_version_11_info = {"kik_version": "11.1.1.12218", "classes_dex_sha1_digest": "aCDhFLsmALSyhwi007tvowZkUd0="}
kik_version_13_info = {"kik_version": "13.4.0.9614", "classes_dex_sha1_digest": "ETo70PFW30/jeFMKKY+CNanX2Fg="}
kik_version_14_info = {"kik_version": "14.0.0.11130",  "classes_dex_sha1_digest": "9nPRnohIOTbby7wU1+IVDqDmQiQ="}
kik_version_14_5_info = {"kik_version": "14.5.0.13136", "classes_dex_sha1_digest": "LuYEjtvBu4mG2kBBG0wA3Ki1PSE="}
kik_version_15_21_info = {'kik_version': '15.21.0.22201', 'classes_dex_sha1_digest': 'MbZ+Zbjaz5uFXKFDM88CwFh7DAg='}
kik_version_15_49_info = {'kik_version': '15.49.0.27501', 'classes_dex_sha1_digest': '5o61frOsakJJ2iCYafCoKHtyu7w='}

kik_version_info = kik_version_15_49_info        # a kik version that's not updated will cause a captcha on login

# grab instance variables from the environment, OR use the default values as a fallback
device_id = env.get('DEVICE_ID', '62030843678b7376a707ca3d11e87836')  # 32 characters. Should be unique per account
android_id = env.get('ANDROID_ID', '849d4ffb0c020de6')                # 16 characters. Should be unique per account