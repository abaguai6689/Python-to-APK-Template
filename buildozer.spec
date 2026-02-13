[app]
title = DaveSaveEd
package.name = davesaveed
package.domain = com.abaguai.tools
source.dir = .

# 1. 确保包含 otf 扩展名
source.include_exts = py,png,jpg,kv,atlas,json,ttf,otf,ttc

# 2. 修改包含模式，确保 fonts 文件夹及其内容被完整打包
source.include_patterns = main.py,fonts/*,*.json

version = 1.0
orientation = portrait
fullscreen = 0

# 3. 依赖项：保持精简，确保不与系统库冲突
requirements = python3,kivy==2.3.0,android,pyjnius

# 4. Android 权限：确保包含管理外部存储的权限（针对存档读写）
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

# 5. API 与 NDK 设置 (维持稳定版本)
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.ndk_api = 21

# 6. 架构设置
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1