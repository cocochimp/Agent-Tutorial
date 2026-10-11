import json
from collections import Counter

WEB = 'web'


def load():
    with open(f'{WEB}/interview-questions.json', encoding='utf-8') as f:
        return json.load(f)


def test_six_categories_and_total():
    data = load()
    assert data['categories'] == ['agent', 'rag', 'sql', 'hallucination', 'evals', 'general']
    active = [q for q in data['questions'] if q['status'] == 'active']
    assert len(active) >= 25


def test_categories_valid_and_merged():
    data = load()
    valid = set(data['categories'])
    for q in data['questions']:
        assert q['category'] in valid, q['question'][:30]
    cats = Counter(q['category'] for q in data['questions'] if q['status'] == 'active')
    assert cats['agent'] >= 8          # 原 intent(3)+memory(3)+agent(5) ≥ 11
    assert cats['evals'] >= 3          # 补题下限
    assert 'intent' not in cats and 'memory' not in cats
    assert cats['rag'] >= 4 and cats['sql'] >= 3 and cats['hallucination'] >= 2


def test_every_question_has_required_fields():
    data = load()
    for q in data['questions']:
        for k in ['category', 'question', 'tips', 'answer', 'weight', 'status']:
            assert k in q, (q.get('question', '?')[:20], k)
        assert q['question'].strip() and q['answer'].strip()
