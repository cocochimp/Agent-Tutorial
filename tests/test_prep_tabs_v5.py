"""V5 面试板块新增模块回归（2026-10-13）：
1. 自我介绍/反问 tab（prep.js）：2.2 自我介绍四段式、2.3 技术面反问 5 问、2.4 HR 面反问（薪资 9 项）
2. 模版简历 tab：优秀简历模版内容（教育/技能/实习 5 条/项目 5 条）+ 导出 PDF（打印容器与按钮）
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def test_prep_js_self_intro_template():
    src = read('web/prep.js')
    # 2.2 自我介绍四段式占位模板
    for key in ('开场问候', '校园与团队经历', '赛事与学术成果', '实习经历', '收尾'):
        assert key in src, key
    assert '面试官您好' in src
    assert '感谢面试官的聆听' in src


def test_prep_js_tech_round_questions():
    src = read('web/prep.js')
    # 2.3 技术面反问 5 问
    assert "'2.3 反问环节（技术面）'" in src
    for q in ('部门承担的项目业务是有哪些？', '部门项目的技术栈有哪些？',
              '您希望候选人有哪些方面的特质？', '我有哪些优势或者不足', '新人的培育方案'):
        assert q in src, q


def test_prep_js_hr_round_salary_items():
    src = read('web/prep.js')
    # 2.4 HR 面反问：薪资 9 项
    assert "'2.4 反问环节（HR面）'" in src
    for k in ('底薪、绩效、年终奖', '绩效考核的标准', '五险一金', '发薪水', '试用期', '福利待遇', '涨薪/晋升机制'):
        assert k in src, k
    # 薪资组 9 个子项
    m = re.search(r"name: '薪资'.*?items: \[(.*?)\]", src, re.S)
    assert m, '未找到薪资组'
    count = len(re.findall(r"\{ t: '", m.group(1)))
    assert count == 9, f'薪资子项应为 9 个，实际 {count}'


def test_prep_js_resume_template_data():
    src = read('web/prep.js')
    # 优秀简历模版：教育 / 技能 / 实习 5 条 / 项目 5 条
    for k in ('xxx 大学 · xxx 专业', 'AI Agent 应用开发工程师', '去哪儿旅行 · 机票售后经营组',
              'AI 图像开放平台', '金标准', '双维度限流'):
        assert k in src, k
    assert src.count('ReAct 规划编排') >= 1            # 实习条目标题（打印模板为动态拼接）
    assert src.count("d: '") >= 5                        # 实习经历 5 条内容
    for k in ('双维度限流模型', '分布式计数一致性', 'Redis Key 结构与算法组合',
              '异步任务闭环', '配置热加载与降级策略'):
        assert k in src, k


def test_prep_js_export_pdf_plumbing():
    src = read('web/prep.js')
    assert 'window.print' in src
    assert "exportPdf" in src
    html = read('web/index.html')
    assert 'nav-selfprep' in html and 'nav-resume' in html
    assert 'selfview-view' in html and 'resumeview-view' in html
    assert 'print-host' in html
    css = read('web/style.css')
    assert '@media print' in css and '#print-host { display: none; }' in css


def test_app_js_has_five_views():
    src = read('web/app.js')
    assert "'selfprep'" in src and "'resume'" in src
    assert 'nav-selfprep' in src and 'nav-resume' in src
