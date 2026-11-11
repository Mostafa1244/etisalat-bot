[app]
title = MOSTAFA_MAHMOUD_BOT
package.name = mostafabot
package.domain = org.mostafa
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.0,requests,urllib3,charset-normalizer,idna,certifi,libffi
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 31
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
p4a.branch = release-2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
