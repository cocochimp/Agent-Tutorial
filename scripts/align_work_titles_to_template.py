#!/usr/bin/env python3
"""细节优化：工作项与「实习经历模版」样式一一对齐（三个项目）。

用户要求（2026-10-13）：工作项应按「实习经历模板」的样式来写。
- work-items.title    -> 「工作X · 模版条目标题」（如 工作一 · ReAct 规划编排）
- resume.label        -> 模版条目标题（不带「工作X ·」前缀）
- resume.text         -> 模版条目正文（真实工作内容原文，非教学重写）
- interview-topics project groups title 同步跟随 work title（id 不变）
- estate-agent 已与模版一致（验证，不一致则修正）
- metrics / metricDetails / introHtml 保持不变（真实场景教学在 introHtml）
"""
import html as _html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJ = ROOT / 'web' / 'projects'
CN = ['一', '二', '三', '四', '五', '六']


def clean_text(s: str) -> str:
    s = re.sub(r'<[^>]+>', '', s)
    s = _html.unescape(s)
    s = s.replace('\u00a0', ' ')
    return re.sub(r'\s+', ' ', s).strip()


def extract_template_items(pid: str):
    gd = json.load(open(PROJ / pid / 'guide-data.json', encoding='utf-8'))
    resume_ch = next(c for c in gd['chapters'] if c['id'] == 'resume')
    html = resume_ch['html']
    ol = re.search(r'<ol[^>]*>(.*?)</ol>', html, re.S)
    seg = ol.group(1) if ol else html
    lis = re.findall(r'<li>(.*?)</li>', seg, re.S)
    items = []
    for li in lis:
        li = li.strip()
        # 标题：li 开头首个 <b> 或 <strong> 包裹的「XX：」；否则正文第一个「：」前
        m = re.match(r'<(?:b|strong)>(.*?)</(?:b|strong)>', li, re.S)
        if m:
            title = clean_text(m.group(1)).rstrip('：:')
            body0 = li[m.end():]
        else:
            body0 = li
            txt = clean_text(body0)
            idx = txt.find('：')
            if idx <= 0 or idx > 20:
                raise ValueError(f'{pid} 无法提取标题: {txt[:40]}')
            title = txt[:idx]
            body0 = body0.replace(txt[:idx + 1], '', 1)
        body = clean_text(body0)
        # 去掉正文开头的「标题：」前缀（若有）
        body = re.sub(r'^' + re.escape(title) + r'[：:]?\s*', '', body)
        items.append({'title': title, 'text': body})
    return items


def align(pid: str, need_swap_titles: bool = True):
    items = extract_template_items(pid)
    assert len(items) == 5, f'{pid} 模版条目数 {len(items)}'
    wi_path = PROJ / pid / 'work-items.json'
    wi = json.load(open(wi_path, encoding='utf-8'))
    its = wi['workItems']
    assert len(its) == 5

    changes = []
    for i, (item, tpl) in enumerate(zip(its, items)):
        new_title = f'工作{CN[i]} · {tpl["title"]}'
        new_label = tpl['title']
        new_text = tpl['text']
        if item['title'] != new_title:
            changes.append(f'{item["id"]} title: {item["title"]} -> {new_title}')
            item['title'] = new_title
        r = item.setdefault('resume', {})
        if r.get('label') != new_label:
            changes.append(f'{item["id"]} resume.label: {r.get("label")} -> {new_label}')
            r['label'] = new_label
        if r.get('text', '') != new_text:
            # 只替换教学重写版 text（以「工作X ·」开头或包含 🎯）
            old = r.get('text', '')
            if '🎯' in old or re.match(r'^工作[一二三四五] ·', old.strip()):
                changes.append(f'{item["id"]} resume.text: 教学重写版 -> 模版原文')
                r['text'] = new_text
            elif old.strip() != new_text.strip():
                changes.append(f'{item["id"]} resume.text: 与模版不一致，已对齐')
                r['text'] = new_text
    json.dump(wi, open(wi_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    # interview-topics project groups title 同步
    it_path = PROJ / pid / 'interview-topics.json'
    it = json.load(open(it_path, encoding='utf-8'))
    proj = next(t for t in it['topics'] if t['id'] == 'project')
    by_id = {x['id']: x['title'] for x in its}
    for g in proj['groups']:
        if g['title'] != by_id[g['id']]:
            changes.append(f'group {g["id"]} title: {g["title"]} -> {by_id[g["id"]]}')
            g['title'] = by_id[g['id']]
    json.dump(it, open(it_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return changes


def verify(pid: str):
    items = extract_template_items(pid)
    wi = json.load(open(PROJ / pid / 'work-items.json', encoding='utf-8'))
    it = json.load(open(PROJ / pid / 'interview-topics.json', encoding='utf-8'))
    ok = True
    for i, (w, tpl) in enumerate(zip(wi['workItems'], items)):
        exp_title = f'工作{CN[i]} · {tpl["title"]}'
        if w['title'] != exp_title:
            print(f'  ✗ {pid} {w["id"]} title != 模版: {w["title"]!r} vs {exp_title!r}'); ok = False
        if w['resume']['label'] != tpl['title']:
            print(f'  ✗ {pid} {w["id"]} label != 模版: {w["resume"]["label"]!r}'); ok = False
        if '🎯' in w['resume']['text'] or w['resume']['text'].strip() != tpl['text'].strip():
            print(f'  ✗ {pid} {w["id"]} resume.text != 模版原文 (len {len(w["resume"]["text"])})'); ok = False
        proj = next(t for t in it['topics'] if t['id'] == 'project')
        g = next(g for g in proj['groups'] if g['id'] == w['id'])
        if g['title'] != w['title']:
            print(f'  ✗ {pid} group {w["id"]} title != work title'); ok = False
    return ok


if __name__ == '__main__':
    for pid in ('air-ticket', 'photo-q', 'estate-agent'):
        ch = align(pid)
        print(f'{pid}: {"无改动" if not ch else chr(10).join("  " + c for c in ch)}')
        verify(pid)
