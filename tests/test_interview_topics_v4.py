import json

WEB = 'web/projects/estate-agent'


def load():
    with open(f'{WEB}/interview-topics.json', encoding='utf-8') as f:
        return json.load(f)


def test_project_and_recording_topics():
    data = load()
    ids = [t['id'] for t in data['topics']]
    assert ids == ['project', 'recording']
    proj = next(t for t in data['topics'] if t['id'] == 'project')
    assert proj['groups'] and len(proj['groups']) == 5
    for g in proj['groups']:
        assert len(g['questions']) >= 10, g['id']
    rec = next(t for t in data['topics'] if t['id'] == 'recording')
    assert 'questions' in rec


def test_common_eight_legs():
    """八股（agent/rag/llm）在共享文件，各 ≥20 题。"""
    with open('web/interview-common.json', encoding='utf-8') as f:
        data = json.load(f)
    ids = [t['id'] for t in data['topics']]
    assert ids == ['agent', 'rag', 'llm']
    for t in data['topics']:
        assert len(t['questions']) >= 20, t['id']


def test_question_shape():
    data = load()
    for t in data['topics']:
        qs = []
        if t.get('groups'):
            for g in t['groups']:
                qs.extend(g['questions'])
        else:
            qs = t.get('questions', [])
        for q in qs:
            assert q['q'].strip()
            assert isinstance(q.get('points', []), list)
            assert len(q.get('qa', [])) >= 1, q['q'][:20]
            for pair in q['qa']:
                assert pair['q'].strip() and pair['a'].strip()


def test_recording_placeholder():
    data = load()
    rec = next(t for t in data['topics'] if t['id'] == 'recording')
    assert rec['questions'] == []


def test_project_six_stage_answers():
    """V4.1：项目面试题每题参考回答必须是完整六段式故事。"""
    data = load()
    proj = next(t for t in data['topics'] if t['id'] == 'project')
    for g in proj['groups']:
        for q in g['questions']:
            a = q['qa'][0]['a']
            steps = [ln for ln in a.split('\n') if ln.strip()]
            assert len(steps) >= 6, (g['id'], q['q'][:20], '不足六段')
            for i, ln in enumerate(steps[:6], 1):
                assert ln.strip().startswith(f'{i}.'), (g['id'], q['q'][:20], f'第{i}段缺失')
            assert len(a) >= 400, (g['id'], q['q'][:20], '回答过短')
