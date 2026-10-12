"""细节优化回归（2026-10-13）：
1. 项目名不再拼接「教学」（app.js）
2. guide qa 章已迁移到 recording，项目导读不再含 qa 章
3. 工作项与实习模版一一对应（air/photo work-4=记忆、work-5=方案生成；estate 标题对齐模版）
4. 迁移的追问答案全部六段式（≥6 段 ≥400 字）
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJ = ROOT / 'web' / 'projects'


def load(rel):
    with open(ROOT / rel, encoding='utf-8') as f:
        return json.load(f)


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def test_project_names_have_no_teaching_suffix():
    src = read('web/app.js')
    assert "p.name + ' 教学'" not in src
    assert "p.name + \" 教学\"" not in src


def test_guide_qa_chapter_migrated():
    for pid in ('estate-agent', 'photo-q', 'air-ticket'):
        gd = load(f'web/projects/{pid}/guide-data.json')
        ids = [c['id'] for c in gd['chapters']]
        assert 'qa' not in ids, pid
        it = load(f'web/projects/{pid}/interview-topics.json')
        rec = next(t for t in it['topics'] if t['id'] == 'recording')
        assert rec['title'] == '高频面试题'
        assert len(rec['questions']) >= 14, pid


def test_intro_html_has_no_followup_block():
    for pid in ('estate-agent', 'photo-q', 'air-ticket'):
        wi = load(f'web/projects/{pid}/work-items.json')
        for item in wi['workItems']:
            assert '面试追问' not in item.get('introHtml', ''), (pid, item['id'])


def test_work_items_match_resume_order():
    """air/photo：work-4=记忆系统、work-5=方案生成；estate：标题对齐模版措辞。"""
    for pid in ('estate-agent', 'photo-q', 'air-ticket'):
        wi = load(f'web/projects/{pid}/work-items.json')
        it = load(f'web/projects/{pid}/interview-topics.json')
        proj = next(t for t in it['topics'] if t['id'] == 'project')
        by_id = {i['id']: i for i in wi['workItems']}
        g_by_id = {g['id']: g for g in proj['groups']}
        for gid in ('work-1', 'work-2', 'work-3', 'work-4', 'work-5'):
            assert g_by_id[gid]['title'] == by_id[gid]['title'], (pid, gid)
        if pid in ('air-ticket', 'photo-q'):
            assert '记忆' in by_id['work-4']['title'], pid
            assert ('方案生成' in by_id['work-5']['title'] or '解题生成' in by_id['work-5']['title']), pid
            assert 'memory_node' in by_id['work-4']['nodes'], pid
        else:
            assert '企业 RAG' in by_id['work-2']['title'], pid
            assert 'Text-to-SQL' in by_id['work-3']['title'], pid


def test_all_project_questions_are_six_stage():
    for pid in ('estate-agent', 'photo-q', 'air-ticket'):
        it = load(f'web/projects/{pid}/interview-topics.json')
        proj = next(t for t in it['topics'] if t['id'] == 'project')
        for g in proj['groups']:
            for q in g['questions']:
                a = q['qa'][0]['a']
                lines = [ln for ln in a.split('\n') if ln.strip()]
                assert len(lines) >= 6, (pid, g['id'], q['q'][:20])
                for i, ln in enumerate(lines[:6], 1):
                    assert ln.strip().startswith(f'{i}.'), (pid, g['id'], q['q'][:20])
                assert len(a) >= 400, (pid, g['id'], q['q'][:20])
