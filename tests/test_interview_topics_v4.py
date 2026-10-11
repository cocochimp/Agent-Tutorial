import json

WEB = 'web'


def load():
    with open(f'{WEB}/interview-topics.json', encoding='utf-8') as f:
        return json.load(f)


def test_five_topics_and_counts():
    data = load()
    ids = [t['id'] for t in data['topics']]
    assert ids == ['project', 'recording', 'agent', 'rag', 'llm']
    for t in data['topics']:
        if t['id'] == 'project':
            assert t['groups'] and len(t['groups']) == 5
            for g in t['groups']:
                assert len(g['questions']) >= 10, g['id']
        else:
            assert 'questions' in t
            if t['id'] != 'recording':
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
