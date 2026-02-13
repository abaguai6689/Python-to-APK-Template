[app]
title = DaveSaveEd
package.name = davesaveed
package.domain = com.abaguai.tools
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf,otf,ttc
version = 1.0
orientation = portrait
fullscreen = 0

# 依赖项 - 只保留核心依赖
requirements = python3,kivy==2.3.0,android,pyjnius

# 入口文件
source.include_patterns = main.py,fonts/*.ttf,fonts/*.otf,fonts/*.ttc

# Android 权限
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

# Android API 设置
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.ndk_api = 21

# 架构设置 - 只构建arm64-v8a以加快构建速度
android.archs = arm64-v8a

# 自动接受SDK许可证
android.accept_sdk_license = True

# Buildozer 设置
[buildozer]
log_level = 2
warn_on_root = 1
