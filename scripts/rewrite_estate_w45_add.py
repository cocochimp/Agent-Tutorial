# -*- coding: utf-8 -*-
"""estate-agent 补充：work-4 补 A、work-5 补 C，严格对齐 A4-5+B4-5+C3-4"""
import json

def Q(t, q, a):
    return {'type': t, 'q': q, 'points': [], 'qa': [{'q': q, 'a': a}]}

w4a = Q('A', '低置信结论转人工的占比（约 8%）是怎么统计的？误杀率怎么测？',
 '1.业务现场：面试官问兜底成本，是想确认你「知道低置信转人工的真实规模」。我们报告校验的综合置信分 < 0.85 会转人工，这个比例直接决定人工成本。\n2.问题定义：两个数：转人工占比（多少人/结论被送去人工看）和误杀率（被拦的结论里有多少其实是对的）。误杀率决定阈值合不合理——太高说明校验太严。\n3.方案设计：统计方法：转人工占比 = 转人工结论数 / 总结论数（从审批节点日志拉，天然有数）；误杀率 = 人工判定「结论正确但被拦」数 / 转人工数（人工审批时标注结果）。\n4.实施细节：评测：300 份报告跑完整流程，记录每个「转人工」结论的人工判定；误杀率约 8%——100 条被拦的里 8 条其实是对的（转人工兜底，不损失用户）。\n5.结果数据：转人工占比约 8%（可接受）、误杀率约 8%（被人工兜住），阈值 0.85 下「拦得多但错杀可控」。\n6.总结延伸：我的方法论是——「阈值是否合理看误杀率」，兜底机制的成本要量化，不能只报拦截效果。追问时我会说误杀结论的人工处理流程。')

w5c = Q('C', '500 条回归用例和线上真实分布怎么对齐？会不会「测的和用的不一样」？',
 '1.业务现场：面试官问评测代表性，是想确认你「知道评测集会失真」。我们的 500 条分层回归如果和线上真实分布脱节——测的全绿但线上照样出问题，回归就失去了意义。\n2.问题定义：评测集失真的两个来源：用例分布和线上不一致（线上 60% 是简单查询，评测 80% 是复杂 case）；bad case 回流滞后（线上新问题还没进评测集）。\n3.方案设计：对齐机制：季度抽样对比——线上请求抽样打标，和评测集分布对比，偏差大时调整分层比例；bad case 回流——线上问题 24 小时内转成用例进回归集。\n4.实施细节：分布检查：线上抽样 200 条，按「简单/边界/幻觉安全/复杂」分层统计占比，和评测集四层比例对比；发现偏差（如线上新增「政策版本类」问题）→ 调整对应层用例数量。\n5.结果数据：对齐机制让回归集覆盖率保持在 85%+（线上问题能在回归集里找到对应类型），「测的全绿线上翻车」的情况显著减少。\n6.总结延伸：我的方法论是——「评测集要和线上分布动态对齐」，回归集是活的数据，不是建完就冻结的静态清单。追问时我会说对齐的触发频率和成本。')

p = 'web/projects/estate-agent/interview-topics.json'
d = json.load(open(p, encoding='utf-8'))
for t in d['topics']:
    if t['id'] != 'project':
        continue
    for g in t['groups']:
        if g['id'] == 'work-4':
            g['questions'].append(w4a)
            print('work-4 ->', len(g['questions']))
        if g['id'] == 'work-5':
            g['questions'].append(w5c)
            print('work-5 ->', len(g['questions']))
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

# 最终全量校验
for pid in ['estate-agent', 'photo-q', 'air-ticket']:
    dd = json.load(open(f'web/projects/{pid}/interview-topics.json', encoding='utf-8'))
    print('====', pid)
    total = 0
    for t in dd['topics']:
        if t['id'] != 'project':
            continue
        for g in t.get('groups', []):
            types = {}
            for q in g['questions']:
                types[q.get('type','?')] = types.get(q.get('type','?'), 0) + 1
                assert isinstance(q['qa'][0]['a'], str) and len(q['qa'][0]['a']) >= 400, (pid, g['id'], q['q'][:20])
            total += len(g['questions'])
            print(g['id'], len(g['questions']), '题', types)
    print('TOTAL', total)
print('ALL OK')
