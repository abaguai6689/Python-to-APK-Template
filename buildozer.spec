[app]
title = DaveSaveEd
package.name = davesaveed
package.domain = com.abaguai.tools
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0
orientation = portrait
fullscreen = 0

# 【重要修改】只保留核心依赖
requirements = python3,kivy==2.3.0,android,pyjnius

entrypoint = main.py

# Android 权限
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.ndk_api = 21
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1