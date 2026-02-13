[app]
# 应用标题
title = DaveSaveEd

# 包名
package.name = davesaveed
package.domain = com.abaguai.tools

# 源代码目录
source.dir = .

# 包含的文件扩展名
source.include_exts = py,png,jpg,kv,atlas,json,ttf,otf,ttc,txt

# 版本号
version = 1.0

# 屏幕方向
orientation = portrait

# 全屏模式
fullscreen = 0

# ============ 依赖项 ============
# 核心依赖（不要删除 android 和 pyjnius）
requirements = python3,kivy==2.3.0,android,pyjnius

# ============ 字体文件包含配置 ============
# 关键：确保字体文件被打包到APK中
source.include_patterns = 
    main.py,
    font_utils.py,
    fonts/*.otf,
    fonts/*.ttf,
    fonts/*.ttc,
    items_id_map.json

# 额外的包含目录（确保fonts目录被打包）
# 使用 ; 分隔多个目录（Windows）或 : 分隔（Linux/Mac）
source.include_paths = fonts

# ============ Android 权限 ============
android.permissions = 
    INTERNET,
    WRITE_EXTERNAL_STORAGE,
    READ_EXTERNAL_STORAGE,
    MANAGE_EXTERNAL_STORAGE

# ============ Android API 设置 ============
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.ndk_api = 21

# 架构设置
android.archs = arm64-v8a

# 自动接受SDK许可证
android.accept_sdk_license = True

# ============ Android 应用配置 ============
# 应用图标（可选）
# android.icon = assets/icon.png

# 启动图片（可选）
# android.presplash = assets/presplash.png

# ============ Buildozer 设置 ============
[buildozer]
# 日志级别 (0=错误, 1=警告, 2=信息, 3=调试)
log_level = 2

# 警告设置
warn_on_root = 1

# 构建目录
build_dir = ./.buildozer

# 输出目录
bin_dir = ./bin
