[app]
title = MOSTAFA_MAHMOUD_BOT
package.name = mostafabot
package.domain = org.mostafa
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
source.exclude_dirs = logs,bin,.git,.github
version = 1.0
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.0,openssl,requests,urllib3,charset-normalizer,idna,certifi,chardet,libffi
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
p4a.branch = release-2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
