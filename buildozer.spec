[app]
title = DaveSaveEd
package.name = davesaveed
package.domain = com.github.abaguai
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0
orientation = portrait
fullscreen = 0

# ============ 核心修正：简化依赖 ============
# 删除了 libiconv, libffi，系统会自动处理它们的依赖
requirements = python3,kivy,android,pyjnius

entrypoint = main.py

# ============ Android 配置 ============
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.ndk_api = 21
android.archs = arm64-v8a
android.accept_sdk_license = True

# 排除模式
exclude_patterns = **/test/*, **/tests/*

[buildozer]
log_level = 2
warn_on_root = 1
