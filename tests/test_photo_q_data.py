"""V6：拍照搜题项目数据完整性（work-items 5 工作项 / 导读 / 面试题 / 执行图 / 手册）。"""
import json, re
from pathlib import Path

PHOTO = Path('web/projects/photo-q')


def load(name):
    return json.loads((PHOTO / name).read_text(encoding='utf-8'))


def test_photo_work_items_five():
    d = load('work-items.json')
    items = d['workItems']
    assert [i['id'] for i in items] == ['work-1', 'work-2', 'work-3', 'work-4', 'work-5']
    for it in items:
        assert it['title'].startswith('工作') and it['short']
        assert it['resume']['label'] and it['resume']['text']
        assert it['resume']['metrics'] and it['resume']['metricDetails']
        for md in it['resume']['metricDetails']:
            assert md['design'] and len(md['design']) >= 150 and md.get('numbers') and len(md['numbers']) >= 3
        assert it['nodes'], it['id']
        assert it['introHtml'] and it['intro']['action'] and it['intro']['result']
        for io in it['io']:
            assert io['node'] and io['input'] is not None and io['output'] is not None


def test_photo_work_items_metrics():
    """关键量化指标出现在简历与指标详解中。"""
    d = load('work-items.json')
    text = json.dumps(d['workItems'], ensure_ascii=False)
    for kw in ('92%', '25%', '18%', '96%', '0.85', '60', '40', '10', '5', '3', '70%', '30%', 'Recall@100'):
        assert kw in text, kw


def test_photo_guide_chapters():
    d = load('guide-data.json')
    assert len(d['chapters']) >= 8
    for c in d['chapters']:
        assert c['title'] and c['html']


def test_photo_handbook_self_contained():
    hb = (PHOTO / 'handbook.html').read_text(encoding='utf-8')
    assert hb.count('<section ') >= 14
    assert '拍照搜题' in hb


def test_photo_tutorial_data():
    d = load('tutorial-data.json')
    assert 'files' in d and len(d['files']) >= 5
    for p, f in d['files'].items():
        assert f['text'], p


def test_photo_interview_project_50():
    d = load('interview-topics.json')
    ids = [t['id'] for t in d['topics']]
    assert 'project' in ids and 'recording' in ids
    proj = next(t for t in d['topics'] if t['id'] == 'project')
    assert len(proj['groups']) == 5
    total = 0
    for g in proj['groups']:
        assert len(g['questions']) >= 10, g['id']
        total += len(g['questions'])
        for q in g['questions']:
            a = q['qa'][0]['a']
            steps = [ln for ln in a.split('\n') if ln.strip()]
            assert len(steps) >= 6 and len(a) >= 400, (g['id'], q['q'][:20])
    assert total >= 50


def test_photo_graph_svg_valid():
    d = load('graph.json')
    svg = d.get('svg', '')
    assert svg and svg.lstrip().startswith('<svg')
    assert len(re.findall(r'data-node="', svg)) >= 15


def test_photo_q_code_refs_cover_all_nodes():
    """全链路节点图：每个工作项每个节点都必须有实例代码（严禁无代码）。"""
    import json as _json
    d = load('work-items.json')
    for it in d['workItems']:
        refs = it['codeRefs']
        covered = {r['node'] for r in refs}
        assert set(it['nodes']) <= covered, (it['id'], set(it['nodes']) - covered)
        for r in refs:
            assert r['node'] and r['text'] and len(r['text']) >= 20, r
