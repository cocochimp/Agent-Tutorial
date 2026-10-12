/* 面试题库：5 个子题库（项目面试题 / Agent / RAG / LLM / 高频面试题）。
   项目面试题按 5 工作项分组，问题卡点开展开「要点说明」+「参考问答」（P2 形态）。 */
(() => {
  const el = id => document.getElementById(id);
  const make = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  let topics = null, activeTopic = 'project', activeGroup = 'work-1';
  const pid = () => (window.App && window.App.projectId()) || 'estate-agent';

  async function load() {
    if (topics) return topics;
    // 项目面试题（project/recording）按项目加载；八股题（agent/rag/llm）全局共享
    const [proj, common] = await Promise.all([
      fetch('projects/' + pid() + '/interview-topics.json', {cache: 'no-cache'}).then(r => { if (!r.ok) throw new Error('面试题数据加载失败'); return r.json(); }),
      fetch('static/interview-common.json', {cache: 'no-cache'}).then(r => r.ok ? r.json() : {topics: []})
    ]);
    topics = [...(proj.topics || []), ...(common.topics || [])];
    return topics;
  }
  const topicById = id => topics.find(t => t.id === id);
  const countOf = t => t.groups ? t.groups.reduce((s, g) => s + g.questions.length, 0) : (t.questions ? t.questions.length : 0);

  /* ---- 左侧子题库 ---- */
  function renderCats() {
    const nav = el('interview-cats'); nav.replaceChildren();
    for (const t of topics) {
      const b = make('button', undefined, 'interview-cat' + (t.id === activeTopic ? ' active' : ''));
      b.setAttribute('aria-pressed', String(t.id === activeTopic));
      b.append(make('span', t.title), make('span', String(countOf(t)), 'cat-count'));
      b.onclick = () => {
        activeTopic = t.id;
        if (t.groups) activeGroup = t.groups[0].id;
        renderCats(); renderGroups(); renderCurrent();
      };
      nav.append(b);
    }
  }

  /* ---- 项目面试题：工作项分组 tabs + 六段式模板 ---- */
  const TEMPLATE = {
    title: '六段式回答模板',
    steps: ['业务现场', '出现问题', '定位原因', '我的动作', '为什么这样选', '结果 / 指标'],
    hint: '面试官问项目时，按这六步把「你做了什么、为什么、结果如何」讲成一个完整故事；数字和口径要对得上简历。'
  };

  function renderGroups() {
    const host = el('interview-groups'); host.replaceChildren();
    const t = topicById(activeTopic);
    if (!t || !t.groups) return;
    const template = make('div', undefined, 'answer-template');
    const titleBox = make('div', undefined, 'answer-template-title');
    titleBox.append(make('b', TEMPLATE.title));
    const steps = TEMPLATE.steps.map((s, i) => {
      const chip = make('span', undefined, 'tmpl-step');
      chip.append(make('b', String(i + 1) + '.'), make('span', s));
      return chip;
    });
    template.append(titleBox, ...steps, make('p', TEMPLATE.hint, 'answer-template-hint'));
    host.append(template);
    const tabs = make('div', undefined, 'interview-group-tabs');
    for (const g of t.groups) {
      const b = make('button', undefined, 'group-tab' + (g.id === activeGroup ? ' active' : ''));
      b.append(make('span', g.title), make('span', String(g.questions.length), 'cat-count'));
      b.onclick = () => { activeGroup = g.id; renderGroups(); renderCurrent(); };
      tabs.append(b);
    }
    host.append(tabs);
  }

  /* ---- 当前问题列表（P2 展开卡） ---- */
  function renderCurrent() {
    const host = el('interview-current'); host.replaceChildren();
    const t = topicById(activeTopic);
    if (!t) return;
    if (t.id === 'recording') {
      const card = make('div', undefined, 'empty');
      card.append(make('h3', '高频面试题（建设中）'), make('p', '这里将沉淀学员真实面试录音中的高频真题，持续优化更新中。'), make('p', '先把「项目面试题」和 Agent / RAG / LLM 八股过一遍，面试后回来补充你的真题。', 'muted'));
      host.append(card);
      return;
    }
    const questions = t.groups ? t.groups.find(g => g.id === activeGroup).questions : (t.questions || []);
    if (!questions.length) {
      const card = make('div', undefined, 'empty');
      card.append(make('h3', '暂无题目'), make('p', '该子题库内容建设中。'));
      host.append(card);
      return;
    }
    const list = make('div', undefined, 'iq-list');
    questions.forEach((q, i) => list.appendChild(questionCard(q, i + 1)));
    host.append(list);
  }

  /* 六段式答案分段渲染：把 "\n1. 业务现场：…\n2. …" 拆成带编号的小节；
     Agent/RAG/LLM 八股的短答案保持整段文本。 */
  function renderAnswer(a) {
    const lines = String(a).split('\n').map(s => s.trim()).filter(Boolean);
    if (lines.length <= 1) return make('p', '答：' + a, 'iq-atext');
    const wrap = make('div', undefined, 'iq-steps');
    lines.forEach(line => {
      const m = line.match(/^(\d+)\.\s*(.*)$/);
      if (!m) { wrap.appendChild(make('p', line, 'iq-atext')); return; }
      const step = make('div', undefined, 'iq-step');
      const body = m[2];
      const lm = body.match(/^([^：:]{1,12})[：:]\s*(.*)$/);
      step.append(make('b', m[1] + '.', 'iq-step-no'));
      if (lm) {
        step.append(make('span', lm[1], 'iq-step-label'), make('p', lm[2], 'iq-step-text'));
      } else {
        step.append(make('p', body, 'iq-step-text iq-step-text-only'));
      }
      wrap.append(step);
    });
    return wrap;
  }

  function questionCard(q, no) {
    const card = make('article', undefined, 'iq-card');
    const summary = make('summary', undefined, 'iq-head');
    const idx = make('span', String(no).padStart(2, '0'), 'iq-no');
    const text = make('span', q.q, 'iq-title');
    const caret = make('span', '展开', 'iq-toggle');
    summary.append(idx, text, caret);
    const body = make('div', undefined, 'iq-body');
    if (q.points && q.points.length) {
      const pBox = make('div', undefined, 'iq-section iq-points');
      pBox.append(make('h4', '要点说明'));
      const ul = make('ul');
      q.points.forEach(p => ul.appendChild(make('li', p)));
      pBox.append(ul);
      body.append(pBox);
    }
    if (q.qa && q.qa.length) {
      const aBox = make('div', undefined, 'iq-section iq-qa');
      aBox.append(make('h4', '参考问答'));
      for (const pair of q.qa) {
        const p = make('div', undefined, 'iq-pair');
        p.append(make('p', '问：' + pair.q, 'iq-qtext'), renderAnswer(pair.a));
        aBox.append(p);
      }
      body.append(aBox);
    }
    const details = make('details', undefined, 'iq-details');
    details.append(summary, body);
    card.append(details);
    details.addEventListener('toggle', () => {
      caret.textContent = details.open ? '收起' : '展开';
    });
    return card;
  }

  window.Interview = {
    async init() {
      try {
        await load();
        renderCats(); renderGroups(); renderCurrent();
      } catch (e) {
        const host = el('interview-current'); host.replaceChildren();
        host.append(make('p', '数据加载失败：' + e.message, 'learning-error'));
      }
    },
    // 切换项目后清缓存重载
    async reload() { topics = null; activeTopic = 'project'; activeGroup = 'work-1'; await this.init(); },
    renderCats, renderGroups, renderCurrent,
    getCurrentTopic: () => topicById(activeTopic),
    getActiveQuestions: () => {
      const t = topicById(activeTopic);
      return t ? (t.groups ? t.groups.find(g => g.id === activeGroup).questions : (t.questions || [])) : [];
    }
  };
})();
