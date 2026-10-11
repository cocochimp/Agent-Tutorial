import json
import pytest

WEB = 'web'


@pytest.fixture(scope='module')
def items():
    with open(f'{WEB}/work-items.json', encoding='utf-8') as f:
        return json.load(f)['workItems']


LABELS = {"understand", "clarify", "agent_node", "schema_retrieval", "query_sql", "calculate",
          "analyze", "rag_search", "generate_report", "validate", "human_approval",
          "execute_action", "finish", "retry_node", "checkpoint_gate"}


def test_v2_has_exactly_five_items(items):
    assert [i['id'] for i in items] == ['work-1', 'work-2', 'work-3', 'work-4', 'work-5']
    assert [i['title'].split(' · ')[0] for i in items] == ['工作一', '工作二', '工作三', '工作四', '工作五']


def test_resume_metrics_match_resume_template(items):
    w1 = next(i for i in items if i['id'] == 'work-1')
    assert '86.8%' in w1['resume']['metrics'] and '94.1%' in w1['resume']['metrics']
    assert '73.5%' in w1['resume']['metrics'] and '89.2%' in w1['resume']['metrics']
    w2 = next(i for i in items if i['id'] == 'work-2')
    assert '79.0%' in w2['resume']['metrics'] and '94.0%' in w2['resume']['metrics']
    assert '0.78' in w2['resume']['metrics']
    w3 = next(i for i in items if i['id'] == 'work-3')
    assert '90.6%' in w3['resume']['metrics'] and '100%' in w3['resume']['metrics']
    w4 = next(i for i in items if i['id'] == 'work-4')
    assert '87.3%' in w4['resume']['metrics'] and '96.1%' in w4['resume']['metrics']
    w5 = next(i for i in items if i['id'] == 'work-5')
    assert 'P95' in w5['resume']['metrics'] and '3.8s' in w5['resume']['metrics']


def test_seven_part_intro_complete(items):
    for item in items:
        for k in ['scene', 'problem', 'locate', 'action', 'why', 'result']:
            assert item['intro'].get(k) and item['intro'][k].strip(), f"{item['id']} 缺 {k}"
        assert len(item['intro'].get('qa', [])) >= 1, f"{item['id']} 缺面试追问"


def test_work1_subtopics_present(items):
    w1 = next(i for i in items if i['id'] == 'work-1')
    assert len(w1['subTopics']) == 2
    assert '意图' in w1['subTopics'][0]['title'] and 'Memory' in w1['subTopics'][1]['title']
    for other in items:
        if other['id'] != 'work-1':
            assert other.get('subTopics', []) == []


def test_nodes_in_labels_and_spec_mapping(items):
    for item in items:
        for n in item['nodes']:
            assert n in LABELS, f"{item['id']} 节点 {n} 不在 labels"
    assert set(next(i for i in items if i['id'] == 'work-1')['nodes']) == {
        "understand", "clarify", "agent_node", "checkpoint_gate", "retry_node", "execute_action", "finish"}
    assert set(next(i for i in items if i['id'] == 'work-2')['nodes']) == {"rag_search"}
    assert set(next(i for i in items if i['id'] == 'work-3')['nodes']) == {
        "schema_retrieval", "query_sql", "calculate", "analyze"}
    assert set(next(i for i in items if i['id'] == 'work-4')['nodes']) == {
        "generate_report", "validate", "human_approval"}
    assert next(i for i in items if i['id'] == 'work-5')['nodes'] == []


def test_io_nodes_within_item_nodes(items):
    for item in items:
        for io in item['io']:
            assert io['node'] in item['nodes'], f"{item['id']} io.node={io['node']} 不在 nodes"


def test_code_refs_exist_in_tutorial_files(items):
    with open(f'{WEB}/tutorial-data.json', encoding='utf-8') as f:
        files = json.load(f)['files']
    for item in items:
        assert len(item['codeRefs']) >= 1, f"{item['id']} 缺 codeRefs"
        for ref in item['codeRefs']:
            assert ref['path'] in files, f"{item['id']} codeRef 路径 {ref['path']} 不在 tutorial-data"
            assert ref['start'] >= 1 and ref['end'] > ref['start']
