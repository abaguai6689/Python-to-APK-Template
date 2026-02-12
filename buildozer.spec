[app]
# 应用名称
title = DaveSaveEd
# 包名
package.name = davesaveed
# 域名
package.domain = com.github.abaguai
# 工作目录
source.dir = .
# 包含的文件后缀
source.include_exts = py,png,jpg,kv,atlas,json
# 版本号
version = 1.0
# 屏幕方向
orientation = portrait
# 非全屏
fullscreen = 0

# ============ 依赖库配置 (已修正) ===========
# 删除了 libiconv 和 libffi，由 p4a 自动处理
requirements = python3,kivy,android,pyjnius

# 主程序入口
entrypoint = main.py

# ============ Android 配置 ===========
# 权限
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
# API 版本配置
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.ndk_api = 21

# 架构 - 保持 arm64-v8a
android.archs = arm64-v8a

# 自动接受许可
android.accept_sdk_license = True

# 排除测试文件
exclude_patterns = **/test/*, **/tests/*

[buildozer]
# 日志级别
log_level = 2
# 发生错误时停止
warn_on_root = 1
