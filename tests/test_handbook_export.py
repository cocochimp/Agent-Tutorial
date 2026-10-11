"""V4.3：导出数据源 = 完整旧手册副本（22 章、可编辑、自包含）。"""
import re
from pathlib import Path


def test_handbook_present_and_complete():
    h = Path('web/handbook.html').read_text(encoding='utf-8')
    assert len(re.findall(r'<section ', h)) == 22
    assert '<section ' in h and 'id="work1"' in h and 'id="cheatsheet"' in h
    assert 'contenteditable' in h  # 可编辑能力
    assert '<script' in h  # 交互脚本自包含
    assert re.search(r'<style[^>]*>.*?</style>', h, re.S)  # 样式自包含
    # 无外链资源（离线可用）
    for m in re.finditer(r'(?:src|href)="([^"]+)"', h):
        u = m.group(1)
        assert u.startswith('#') or u.startswith('javascript') or u == '', u
