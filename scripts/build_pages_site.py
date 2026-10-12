#!/usr/bin/env python3
"""构建 GitHub Pages 站点目录。

GitHub Pages 无法运行 FastAPI 后端，教学站需以纯静态方式发布。
本脚本把 web/ 目录转换为 Pages 兼容结构（site_pages/）：
- web/index.html            -> site_pages/index.html
- web/ 其余所有文件/目录    -> site_pages/static/（保持 /static/* 引用不变；
                              web/projects/ 递归复制为 static/projects/）

这样 index.html 中的 /static/style.css、/static/*.js、/static/*.json
等绝对路径在 Pages 上直接成立；本地 FastAPI 的 /static 挂载不受影响。
"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
OUT = os.path.join(ROOT, "site_pages")
STATIC = os.path.join(OUT, "static")


def main() -> None:
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(STATIC, exist_ok=True)

    index = os.path.join(WEB, "index.html")
    assert os.path.isfile(index), f"missing {index}"
    shutil.copy2(index, os.path.join(OUT, "index.html"))

    copied = 0
    for name in sorted(os.listdir(WEB)):
        src = os.path.join(WEB, name)
        if name == "index.html":
            continue
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(STATIC, name))
            copied += 1
            continue
        if not os.path.isfile(src):
            continue
        shutil.copy2(src, os.path.join(STATIC, name))
        copied += 1

    manifest = {
        "index": "index.html",
        "static_count": copied,
        "files": sorted(os.listdir(STATIC)),
    }
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"site_pages 构建完成：index.html + static/ {copied} 个文件")


if __name__ == "__main__":
    main()
