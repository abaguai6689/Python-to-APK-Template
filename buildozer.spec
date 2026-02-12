[app]

# 应用名称 - 可以中文
title = DaveSaveEd

# 包名 - 小写英文，无特殊字符
package.name = davesaveed

# 域名 - 使用你自己的域名或反向域名格式
# 例如：com.yourname.davesaveed
# 如果没有域名，可以用 com.github.你的用户名.davesaveed
package.domain = com.github.abaguai6689

# 工作目录
source.dir = .

# 需要打包的文件类型 - 添加 json 支持数据文件
source.include_exts = py,png,jpg,kv,atlas,json

# 版本号
version = 1.0

# 屏幕方向 - 竖屏更适合手机操作
orientation = portrait

# 全屏 - 0 表示非全屏（显示状态栏）
fullscreen = 0

# ============ 依赖库配置 ============

# 核心依赖：python3 + kivy + android 存储支持
# 注意：不需要 kivymd（除非你想用 Material Design 界面）
# 添加 android 和 pyjnius 用于 Android 权限和存储访问
requirements = python3,kivy,android,pyjnius,libiconv,libffi

# 主程序入口
entrypoint = main.py

# ============ Android 配置 ============

# 权限 - 关键！必须添加存储权限才能访问存档文件
android.permissions = 
    INTERNET,
    WRITE_EXTERNAL_STORAGE,
    READ_EXTERNAL_STORAGE,
    MANAGE_EXTERNAL_STORAGE

# API 版本
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.ndk_api = 21

# 接受 SDK 许可
android.accept_sdk_license = True

# 排除测试文件
exclude_patterns = **/test/*, **/tests/*

# Gradle 配置
android.gradle_download = https://services.gradle.org/distributions/gradle-7.6.4-all.zip
android.gradle_plugin = 7.4.2
p4a.gradle_dependencies = gradle:7.6.4
p4a.bootstrap = sdl2
p4a.gradle_options = -Dorg.gradle.java.home=/usr/lib/jvm/java-17-openjdk-amd64

# ============ 打包配置（Debug 模式） ============

# 强制打包为 APK 而不是 AAB
android.aab = False

# 架构 - 现代手机用 arm64-v8a，兼容旧手机用 armeabi-v7a
android.arch = arm64-v8a

# ============ Release 模式配置（可选） ============

# 取消注释以下行用于发布模式
# android.keystore = /path/to/your.keystore
# android.keystore_storepass = your_password
# android.keystore_keypass = your_password
# android.keystore_alias = your_alias

[buildozer]

# 日志级别 - 2 显示详细信息，1 只显示错误
log_level = 2

# 根目录警告
warn_on_root = 1
