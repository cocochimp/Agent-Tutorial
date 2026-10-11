/* 教程只读取显式白名单内的源码快照，不开放任意文件读取接口。 */
(() => {
  const el = id => document.getElementById(id);
  const make = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  let catalog, loading, activeLesson = 'overview', activeSource = 0, fullFile = false;
  let navigationVersion = 0;
  // 节点名称与真实编译图一致，主题 ID 来自 docs/tutorials.json。
  const topics = {
    __start__: 'overview', __end__: 'overview', understand: 'intent', clarify: 'intent',
    agent_node: 'graph', schema_retrieval: 'sql', query_sql: 'sql', calculate: 'sql', analyze: 'sql',
    rag_search: 'rag', generate_report: 'report', validate: 'report', finish: 'memory',
    checkpoint_gate: 'recovery', retry_node: 'recovery', human_approval: 'recovery',
    execute_action: 'recovery', failed: 'recovery', data_agent: 'extensions',
    knowledge_agent: 'extensions', report_agent: 'extensions'
  };
  async function loadCatalog() {
    if (catalog) return catalog;
    // 合并快速连点产生的请求；失败后可以重新加载。
    if (!loading) loading = fetch('/static/tutorial-data.json', {cache: 'no-cache'})
      .then(r => { if (!r.ok) throw new Error('教程文件加载失败，请确认服务已启动。'); return r.json(); })
      .then(data => { catalog = data; return data; }).finally(() => { loading = null; });
    return loading;
  }
  function showPanel(learn) {
    el('analysis-panel').hidden = learn; el('learning-panel').hidden = !learn;
    for (const [id, selected] of [['nav-learn', learn], ['nav-workspace', !learn]]) {
      el(id).classList.toggle('active', selected); el(id).setAttribute('aria-pressed', String(selected));
    }
    document.dispatchEvent(new CustomEvent('agent:view'));
  }
  function route(id, index = 0) {
    const hash = '#learn=' + encodeURIComponent(id) + '&source=' + index;
    if (location.hash === hash) openLesson(id, index); else location.hash = hash;
  }
  function workspace() {
    // 切换教程不重置任务或关闭 SSE，返回时原来的报告与进度仍保留。
    if (location.hash) location.hash = ''; else { navigationVersion++; showPanel(false); }
    window.scrollTo({top: 0, behavior: 'instant'});
  }
  function renderNav() {
    const query = el('lesson-search').value.trim().toLowerCase(), nav = el('lesson-nav'); nav.replaceChildren();
    let group = '', count = 0;
    catalog.lessons.forEach((lesson, i) => {
      const haystack = [lesson.title, lesson.summary, ...lesson.tags, ...lesson.refs.flatMap(r => [r.path, r.symbol || '', r.label])].join(' ').toLowerCase();
      if (query && !haystack.includes(query)) return;
      count++;
      if (group !== lesson.category) { nav.append(make('div', lesson.category, 'lesson-group')); group = lesson.category; }
      const button = make('button', undefined, 'lesson-link'); button.classList.toggle('active', lesson.id === activeLesson);
      button.setAttribute('aria-current', lesson.id === activeLesson ? 'page' : 'false');
      button.append(make('span', String(i + 1).padStart(2, '0')), make('span', lesson.title)); button.onclick = () => route(lesson.id); nav.append(button);
    });
    el('lesson-count').textContent = query ? count + ' 个匹配主题' : catalog.lessons.length + ' 个主题 · 按兴趣阅读';
    if (!count) nav.append(make('p', '没有匹配的主题。试试 RAG、SQL 或审批。', 'lesson-empty'));
  }
  async function openLesson(id, index = 0) {
    const version = ++navigationVersion; showPanel(true);
    try {
      await loadCatalog();
      // 异步加载完成时，用户可能已经切回工作台；丢弃过期导航。
      if (version !== navigationVersion) return;
      const lesson = catalog.lessons.find(l => l.id === id) || catalog.lessons[0];
      activeLesson = lesson.id; activeSource = Number.isInteger(index) && index >= 0 && index < lesson.refs.length ? index : 0; fullFile = false;
      renderNav(); renderLesson(lesson);
      el('lesson-content').querySelector('h2').focus({preventScroll: true});
      if (matchMedia('(max-width: 780px)').matches) el('lesson-content').scrollIntoView({block: 'start', behavior: 'instant'});
      else window.scrollTo({top: 0, behavior: 'instant'});
    } catch (e) {
      if (version !== navigationVersion) return;
      const box = make('div', undefined, 'learning-error'); box.append(make('h2', '暂时无法加载教程'), make('p', e.message));
      const retry = make('button', '重新加载'); retry.onclick = () => openLesson(id, index); box.append(retry); el('lesson-content').replaceChildren(box);
    }
  }
  function renderLesson(lesson) {
    const host = el('lesson-content'); host.replaceChildren();
    const ordinal = catalog.lessons.indexOf(lesson), heading = make('div', undefined, 'lesson-heading'), title = make('div');
    title.append(make('div', lesson.category + ' / IMPLEMENTATION', 'eyebrow'), make('h2', lesson.title));
    title.querySelector('h2').tabIndex = -1;
    heading.append(make('span', String(ordinal + 1).padStart(2, '0'), 'chapter-number'), title);
    const tags = make('div', undefined, 'lesson-tags'); lesson.tags.forEach(t => tags.append(make('span', t, 'lesson-tag')));
    const flow = make('div', undefined, 'lesson-flow');
    lesson.flow.forEach((s, i) => { if (i) flow.append(make('span', '→', 'flow-arrow')); flow.append(make('span', s)); });
    const explanation = make('div', undefined, 'lesson-explanation'), steps = make('div', undefined, 'lesson-steps'), list = make('ol');
    lesson.steps.forEach(s => list.append(make('li', s))); steps.append(make('h3', '实现过程'), list);
    const asides = make('div', undefined, 'lesson-asides');
    for (const [label, content, cls] of [['在工作台里观察', lesson.observe, ''], ['阅读时留意', lesson.pitfall, ' caution']]) {
      const note = make('div', undefined, 'lesson-note' + cls); note.append(make('b', label), make('p', content)); asides.append(note);
    }
    explanation.append(steps, asides);
    const reader = make('section', undefined, 'source-reader'); reader.setAttribute('aria-label', '项目源码阅读器');
    const readerHead = make('div', undefined, 'source-reader-head'); readerHead.append(make('h3', '对应实现'), make('small', '项目源码 · 中文注释 · 原始行号'));
    const tabs = make('div', undefined, 'source-tabs'); tabs.setAttribute('aria-label', '选择实现片段');
    lesson.refs.forEach((ref, i) => {
      const b = make('button', ref.label); b.setAttribute('aria-pressed', String(i === activeSource)); b.classList.toggle('active', i === activeSource);
      b.onclick = () => {
        activeSource = i; fullFile = false; history.replaceState(null, '', '#learn=' + lesson.id + '&source=' + i);
        Array.from(tabs.children).forEach((t, n) => { t.classList.toggle('active', n === i); t.setAttribute('aria-pressed', String(n === i)); }); renderSource(lesson.refs[i]);
      }; tabs.append(b);
    });
    const body = make('div'); body.id = 'source-body'; reader.append(readerHead, tabs, body);
    const bottom = make('div', undefined, 'lesson-bottom'), manual = make('button', '继续阅读说明书 · 第 ' + lesson.chapter + ' 章 ↗');
    manual.onclick = () => openManual(lesson.chapter); bottom.append(manual);
    if (ordinal < catalog.lessons.length - 1) {
      const next = catalog.lessons[ordinal + 1], b = make('button', '下一主题：' + next.title + ' →');
      b.onclick = () => { route(next.id); window.scrollTo({top: 0, behavior: 'instant'}); }; bottom.append(b);
    }
    host.append(heading, make('p', lesson.summary, 'lesson-summary'), tags, flow, explanation, reader, bottom); renderSource(lesson.refs[activeSource]);
  }
  // 词法着色仅用于阅读。源码通过 textContent 创建，不作为 HTML 执行。
  // Python 三引号状态跨行保留，关键片段前的行也会先被扫描。
  function colorLine(text, path, state) {
    const fragment = document.createDocumentFragment();
    const expression = /(#.*$|\/\/.*$|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:def|class|return|if|elif|else|for|while|in|not|and|or|is|with|as|from|import|try|except|finally|raise|lambda|yield|async|await|True|False|None|global|const|let|function|new|throw|true|false|null)\b|\b\d+(?:\.\d+)?\b)/g;
    function emit(value, cls) { fragment.append(cls ? make('span', value, cls) : document.createTextNode(value)); }
    function plain(value) {
      let offset = 0;
      for (const m of value.matchAll(expression)) {
        emit(value.slice(offset, m.index));
        const token = m[0], cls = token.startsWith('#') || token.startsWith('//') ? 'token-comment' : /^['"]/.test(token) ? 'token-string' : /^\d/.test(token) ? 'token-number' : 'token-keyword';
        emit(token, cls); offset = m.index + token.length;
      }
      emit(value.slice(offset));
    }
    if (!path.endsWith('.py')) { plain(text); return fragment; }
    let pos = 0;
    while (pos < text.length) {
      if (state.quote) {
        const end = text.indexOf(state.quote, pos);
        if (end < 0) { emit(text.slice(pos), 'token-string'); break; }
        emit(text.slice(pos, end + 3), 'token-string'); pos = end + 3; state.quote = null;
      } else {
        const match = /"""|'''/.exec(text.slice(pos));
        if (!match) { plain(text.slice(pos)); break; }
        const start = pos + match.index;
        if (text.slice(pos, start).trimStart().startsWith('#')) { plain(text.slice(pos)); break; }
        plain(text.slice(pos, start)); emit(match[0], 'token-string'); state.quote = match[0]; pos = start + 3;
      }
    }
    return fragment;
  }
  function renderSource(ref) {
    const file = catalog.files[ref.path], lines = file.text.replace(/\r\n/g, '\n').split('\n');
    if (lines.at(-1) === '') lines.pop();
    const start = fullFile ? 1 : ref.start, end = fullFile ? lines.length : ref.end, body = el('source-body'); body.replaceChildren();
    const bar = make('div', undefined, 'source-pathbar'); bar.append(make('span', ref.path, 'source-path'), make('span', 'L' + start + '–' + end, 'source-range'));
    const controls = make('div', undefined, 'source-controls'), toggle = make('button', fullFile ? '只看关键片段' : '查看完整文件');
    toggle.setAttribute('aria-pressed', String(fullFile)); toggle.onclick = () => { fullFile = !fullFile; renderSource(ref); };
    const copy = make('button', '复制代码');
    copy.onclick = async () => {
      try { await navigator.clipboard.writeText(lines.slice(start - 1, end).join('\n')); copy.textContent = '已复制'; }
      catch { copy.textContent = '请选中代码复制'; }
      setTimeout(() => { copy.textContent = '复制代码'; }, 2000);
    }; controls.append(toggle, copy); bar.append(controls);
    const scroll = make('div', undefined, 'source-scroll'); scroll.tabIndex = 0; scroll.setAttribute('aria-label', ref.path + ' 源码，可滚动阅读');
    const listing = make('div', undefined, 'source-lines'), lexical = {quote: null};
    for (let i = 0; i < start - 1; i++) colorLine(lines[i], ref.path, lexical);
    for (let i = start; i <= end; i++) {
      const row = make('div', undefined, 'source-line'); row.dataset.line = i;
      if (fullFile && i >= ref.start && i <= ref.end) row.classList.add('highlight-line');
      const code = make('code'); code.append(colorLine(lines[i - 1], ref.path, lexical));
      const lineNumber = make('span', String(i), 'line-number'); lineNumber.setAttribute('aria-hidden', 'true'); row.append(lineNumber, code); listing.append(row);
    }
    scroll.append(listing);
    const foot = make('div', undefined, 'source-foot'); foot.append(make('span', fullFile ? '浅绿色为当前主题关联片段' : '关键片段 · 行号对应项目源文件'), make('span', 'SHA256 ' + file.sha256.slice(0, 12)));
    body.append(bar, make('p', ref.note, 'source-note'), scroll, foot);
    if (fullFile) scroll.scrollTop = Math.max(0, (ref.start - 3) * 24);
  }
  function openManual(chapter) {
    el('manual-frame').src = '/guide/能力对照说明书.html' + (chapter ? '#section-' + chapter : '');
    if (!el('manual-dialog').open) el('manual-dialog').showModal();
  }
  function fromHash() {
    const params = new URLSearchParams(location.hash.slice(1));
    if (params.has('learn')) openLesson(params.get('learn'), Number(params.get('source') || 0));
    else { navigationVersion++; showPanel(false); }
  }
  // 事件委托同时覆盖固定入口、动态 Trace 按钮和 SVG 节点。
  document.addEventListener('click', event => {
    const learn = event.target.closest('[data-learn]'), graphNode = event.target.closest('#graph [data-node]');
    if (learn) route(learn.dataset.learn);
    else if (graphNode) route(topics[graphNode.dataset.node] || 'graph');
    else if (event.target.closest('[data-manual]')) openManual();
  });
  el('graph').addEventListener('keydown', event => {
    const target = event.target.closest('[data-node]');
    if (target && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); route(topics[target.dataset.node] || 'graph'); }
  });
  function annotateGraph() {
    el('graph').querySelectorAll('[data-node]').forEach(n => {
      n.setAttribute('role', 'button'); n.setAttribute('tabindex', '0'); n.setAttribute('aria-label', (n.textContent || n.dataset.node) + '：查看实现教程');
    });
    el('graph').querySelector('svg')?.setAttribute('role', 'group');
  }
  new MutationObserver(annotateGraph).observe(el('graph'), {childList: true}); annotateGraph();
  el('nav-learn').onclick = () => route(activeLesson, activeSource); el('nav-workspace').onclick = workspace;
  el('back-to-analysis').onclick = workspace; el('lesson-search').oninput = () => { if (catalog) renderNav(); };
  el('close-manual').onclick = () => el('manual-dialog').close();
  window.addEventListener('hashchange', fromHash); window.Learning = {topicForNode: step => topics[step] || 'overview'}; fromHash();
})();
