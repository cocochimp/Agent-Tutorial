"""V6：多项目数据目录（projects/ 注册表 + estate-agent 迁移 + 八股共享）。"""
import json
from pathlib import Path

WEB = Path('web')
PROJECTS = WEB / 'projects'
ESTATE = PROJECTS / 'estate-agent'
COMMON = WEB / 'static' / 'interview-common.json'


def test_projects_index_registry():
    d = json.loads((PROJECTS / 'index.json').read_text(encoding='utf-8'))
    ids = [p['id'] for p in d['projects']]
    assert 'estate-agent' in ids
    assert all(k in d['projects'][0] for k in ('id', 'name', 'tagline'))


def test_estate_package_complete():
    """estate-agent 数据五件套齐全。"""
    for f in ('work-items.json', 'guide-data.json', 'interview-topics.json',
              'tutorial-data.json', 'graph.json', 'handbook.html'):
        assert (ESTATE / f).is_file(), f'{f} 缺失'
    wi = json.loads((ESTATE / 'work-items.json').read_text(encoding='utf-8'))
    assert len(wi['workItems']) == 5
    guide = json.loads((ESTATE / 'guide-data.json').read_text(encoding='utf-8'))
    assert len(guide['chapters']) == 13
    hb = (ESTATE / 'handbook.html').read_text(encoding='utf-8')
    assert hb.count('<section ') == 22


def test_common_eight_legs_extracted():
    """八股题（agent/rag/llm）抽到共享文件；estate interview-topics.json 不再含八股。"""
    common = json.loads(COMMON.read_text(encoding='utf-8'))
    ids = [t['id'] for t in common['topics']]
    assert ids == ['agent', 'rag', 'llm']
    for t in common['topics']:
        assert len(t.get('questions', [])) >= 20

    estate = json.loads((ESTATE / 'interview-topics.json').read_text(encoding='utf-8'))
    estate_ids = [t['id'] for t in estate['topics']]
    assert 'project' in estate_ids and 'recording' in estate_ids
    assert not ({'agent', 'rag', 'llm'} & set(estate_ids)), 'estate 不应再含八股'


def test_old_root_files_removed():
    """根目录旧数据文件已迁移，避免双源。"""
    for f in ('work-items.json', 'guide-data.json', 'interview-topics.json',
              'tutorial-data.json', 'graph.json', 'handbook.html'):
        assert not (WEB / f).exists(), f'{f} 仍留在根目录'
