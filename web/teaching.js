/* V2 实习项目教程：四模块纵向布局（工作项标签 / 分析执行图 / 全链路节点图 / 内容介绍）。
   节点浮窗展示该节点真实输入输出与工作项实例代码。 */
(() => {
  const el = id => document.getElementById(id);
  const make = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  let workItems = [], files = {}, activeWork = null, activeSub = null, svgCache = null;
  const pid = () => (window.App && window.App.projectId()) || 'estate-agent';

  async function loadData() {
    const [a, b] = await Promise.all([
      fetch('static/projects/' + pid() + '/work-items.json', {cache: 'no-cache'}).then(r => { if (!r.ok) throw new Error('工作项数据加载失败'); return r.json(); }),
      fetch('static/projects/' + pid() + '/tutorial-data.json', {cache: 'no-cache'}).then(r => { if (!r.ok) throw new Error('教程数据加载失败'); return r.json(); })
    ]);
    workItems = a.workItems || [];
    files = b.files || {};
  }

  function currentItem() { return workItems.find(w => w.id === activeWork) || null; }

  /* 模块1：工作项横向标签 + 简历卡 */
  function renderTabs() {
    const nav = el('work-tabs'); nav.replaceChildren();
    workItems.forEach((item, i) => {
      const b = make('button', undefined, 'work-tab' + (item.id === activeWork ? ' active' : ''));
      b.setAttribute('aria-pressed', String(item.id === activeWork));
      b.append(make('span', '工作' + (i + 1), 'wi-no'), make('span', item.short));
      b.onclick = () => selectWorkItem(item.id);
      nav.append(b);
    });
    renderResume(currentItem());
  }

  function renderResume(item) {
    const host = el('work-resume'); host.replaceChildren();
    if (!item) { host.append(make('p', '选择上方工作项查看对应简历描述', 'small muted')); return; }
    const head = make('div', undefined, 'resume-head');
    const who = make('div', undefined, 'who');
    who.append(document.createTextNode('实习经历模版 · '), make('span', item.resume.label));
    head.append(who, make('span', item.resume.label, 'when'));
    host.append(head, make('p', item.resume.text));
    if (item.resume.metrics) {
      const row = make('div', undefined, 'metrics-row');
      const details = item.resume.metricDetails || [];
      item.resume.metrics.split('·').map(s => s.trim()).filter(Boolean).forEach((m, i) => {
        const chip = make('button', m, 'score metric-chip');
        chip.type = 'button';
        if (details[i]) {
          chip.title = '点击查看设计思路与数据来源';
          chip.onclick = () => openMetric(details[i]);
        } else {
          chip.disabled = true;
        }
        row.append(chip);
      });
      host.append(row);
      host.append(make('p', '指标可点击查看「设计思路」与「数据来源」，面试讲数据时直接可用。', 'small muted metric-tip'));
    }
  }

  /* 量化指标浮窗：面试话术（多段）+ 关键数字 bullet */
  function openMetric(m) {
    const body = el('metric-dialog-body'); body.replaceChildren();
    body.append(make('h3', m.title, 'metric-title'));
    const script = make('div', undefined, 'metric-block');
    script.append(make('strong', '面试话术 · 可以直接讲'));
    String(m.design || '').split(/\n\n+/).filter(Boolean).forEach(p => script.append(make('p', p)));
    const nums = make('div', undefined, 'metric-block');
    nums.append(make('strong', '关键数字 · 被追问时捞'));
    const list = make('ul', undefined, 'metric-numbers');
    const items = Array.isArray(m.numbers) ? m.numbers : String(m.source || '').split(/\n+/).filter(Boolean);
    items.forEach(n => list.append(make('li', n)));
    nums.append(list);
    body.append(script, nums);
    el('metric-dialog').showModal();
  }

  /* 模块2：分析执行图（静态 graph.json 的 SVG 全图；静态文件缺失时回退后端 /api/graph） */
  async function renderExecGraph() {
    const host = el('exec-graph');
    if (svgCache) { host.replaceChildren(svgCache); return; }
    let data = null;
    try {
      const r = await fetch('static/projects/' + pid() + '/graph.json', {cache: 'no-cache'});
      if (r.ok) data = await r.json();
    } catch (e) { /* 静态文件不可用时回退后端 */ }
    if (!data) {
      try {
        const r = await fetch('/api/graph?strategy=single', {cache: 'no-cache'});
        if (!r.ok) throw new Error('接口返回 ' + r.status);
        data = await r.json();
      } catch (e) {
        host.replaceChildren(make('p', '执行图加载失败：' + e.message, 'graph-fallback'));
        return;
      }
    }
    try {
      const holder = make('div');
      holder.innerHTML = data.svg || '';
      const svg = holder.querySelector('svg');
      if (svg) {
        svg.setAttribute('aria-label', '分析执行图');
        svgCache = svg;
        host.replaceChildren(svg);
      } else {
        host.replaceChildren(make('p', '执行图数据缺失，请确认 graph.json 或 /api/graph 可用。', 'graph-fallback'));
      }
    } catch (e) {
      host.replaceChildren(make('p', '执行图渲染失败：' + e.message, 'graph-fallback'));
    }
    highlightGraph(currentItem());
  }

  /* 执行图节点高亮：当前工作项 nodes 对应的 g[data-node] 高亮 */
  function highlightGraph(item) {
    const svg = el('exec-graph').querySelector('svg');
    if (!svg || !item) return;
    const active = new Set(item.nodes || []);
    svg.querySelectorAll('g[data-node]').forEach(g => {
      const rect = g.querySelector('rect'), text = g.querySelector('text');
      if (active.has(g.getAttribute('data-node'))) {
        if (rect) { rect.setAttribute('fill', '#e7f7f7'); rect.setAttribute('stroke', '#087f8c'); rect.setAttribute('stroke-width', '2'); }
        if (text) { text.setAttribute('fill', '#065f68'); text.setAttribute('font-weight', '700'); }
      } else {
        if (rect) { rect.setAttribute('fill', '#f4f6ef'); rect.setAttribute('stroke', '#95b1a5'); rect.setAttribute('stroke-width', '1'); }
        if (text) { text.setAttribute('fill', '#294b44'); text.removeAttribute('font-weight'); }
      }
    });
  }

  /* 模块3：全链路节点图（节点卡片链，点击弹出浮窗） */
  function nodeNote(item, name) {
    const io = item.io.find(x => x.node === name);
    return (io && io.note) || '点击查看该节点的输入输出与实例代码';
  }

  function renderNodeChain(item) {
    const host = el('node-chain'); host.replaceChildren();
    el('node-count').textContent = item.nodes.length ? item.nodes.length + ' 个节点' : '无图节点';
    if (!item.nodes.length) {
      host.append(make('p', '该工作项主要涉及工程化与评测能力，不绑定具体执行图节点。', 'node-empty'));
      return;
    }
    item.nodes.forEach((name, i) => {
      const card = make('button', undefined, 'node-card');
      card.setAttribute('aria-pressed', 'false');
      card.append(make('span', String(i + 1).padStart(2, '0'), 'node-badge'));
      const body = make('div', undefined, 'node-card-body');
      body.append(make('h3', labels[name] || name));
      body.append(make('p', nodeNote(item, name)));
      card.append(body, make('span', name, 'node-index'));
      card.onclick = () => openNodeDialog(name);
      card.tabIndex = 0;
      card.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openNodeDialog(name); } };
      host.append(card);
    });
  }

  /* 节点浮窗：输入输出 + 实例代码 */
  function openNodeDialog(name) {
    const item = currentItem();
    if (!item) return;
    el('node-dialog-title').textContent = (labels[name] || name) + ' · ' + name;
    const body = el('node-dialog-body'); body.replaceChildren();
    const ios = item.io.filter(x => x.node === name);
    let hasContent = false;
    for (const io of ios) {
      hasContent = true;
      const d = make('details', undefined, 'io-block'); d.open = ios.length === 1;
      const summary = make('summary');
      summary.append(make('span', '输入 / 输出', 'io-tag'), make('span', 'Trace 报告（真实输入输出）'));
      d.append(summary);
      const ioBody = make('div', undefined, 'io-body');
      ioBody.append(make('h4', '输入 input'));
      ioBody.append(make('pre', JSON.stringify(io.input, null, 2)));
      ioBody.append(make('h4', '输出 output'));
      ioBody.append(make('pre', JSON.stringify(io.output, null, 2)));
      if (io.note) ioBody.append(make('p', io.note, 'io-note'));
      d.append(ioBody); body.append(d);
    }
    if (item.codeRefs.length) {
      const refs = item.codeRefs.filter(ref => ref.node === name);
      if (refs.length) {
        hasContent = true;
        body.append(make('h3', '实例代码'));
        refs.forEach(ref => body.append(renderCode(ref)));
      }
    }
    if (!hasContent) body.append(make('p', '该节点暂无输入输出与实例代码，可在「内容介绍」中学习其思路。', 'dialog-empty'));
    el('node-dialog').showModal();
  }

  /* 模块4：内容介绍（实习复盘手册完整章节，来自 work-items.json introHtml/subTopics.html） */
  function renderStory(item) {
    const host = el('story-content'); host.replaceChildren();
    if (!item) { host.append(make('p', '选择一个工作项查看内容介绍', 'small muted')); return; }
    if (item.subTopics && item.subTopics.length) {
      const tabs = make('div', undefined, 'subtopic-tabs');
      const allTab = make('button', '工作项总览', 'subtopic-tab' + (activeSub === null ? ' active' : ''));
      allTab.onclick = () => { activeSub = null; renderStory(item); };
      tabs.append(allTab);
      item.subTopics.forEach((st, i) => {
        const t = make('button', '子主题 · ' + st.title, 'subtopic-tab' + (activeSub === i ? ' active' : ''));
        t.onclick = () => { activeSub = i; renderStory(item); };
        tabs.append(t);
      });
      host.append(tabs);
      const html = activeSub === null ? item.introHtml : item.subTopics[activeSub].html;
      const body = make('div', undefined, 'guide-html');
      body.innerHTML = html || '';
      host.append(body);
    } else {
      const body = make('div', undefined, 'guide-html');
      body.innerHTML = item.introHtml || '';
      host.append(body);
    }
  }

  function selectWorkItem(id) {
    activeWork = id;
    activeSub = null;
    const item = currentItem();
    if (!item) return;
    renderTabs();
    renderNodeChain(item);
    renderStory(item);
    highlightGraph(item);
    document.dispatchEvent(new CustomEvent('teaching:work', {detail: {id}}));
  }

  /* 词法着色与代码渲染（V1 复用）：源码通过 textContent 创建，不作为 HTML 执行 */
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

  function renderCode(ref) {
    const file = files[ref.path];
    const lines = ref.text !== undefined ? ref.text.replace(/\r\n/g, '\n').split('\n')
      : (file ? file.text.replace(/\r\n/g, '\n').split('\n') : []);
    if (lines.length && lines.at(-1) === '') lines.pop();
    const start = ref.text !== undefined ? 1 : ref.start;
    const end = ref.text !== undefined ? lines.length : Math.min(ref.end, lines.length);
    if (!lines.length) return make('p', '源码文件缺失：' + ref.path, 'code-empty');
    const block = make('div', undefined, 'code-block');
    const head = make('div', undefined, 'code-head');
    head.append(make('span', ref.path, 'code-path'), make('span', 'L' + start + '–' + end, 'code-range'));
    const copy = make('button', '复制代码');
    copy.onclick = async () => {
      try { await navigator.clipboard.writeText(lines.slice(start - 1, end).join('\n')); copy.textContent = '已复制'; }
      catch { copy.textContent = '请选中代码复制'; }
      setTimeout(() => { copy.textContent = '复制代码'; }, 2000);
    };
    head.append(copy); block.append(head);
    if (ref.note) block.append(make('p', ref.note, 'io-note'));
    const scroll = make('div', undefined, 'code-scroll'), listing = make('div', undefined, 'code-lines');
    const lexical = {quote: null};
    for (let i = start; i <= end; i++) {
      const row = make('div', undefined, 'code-line');
      row.append(make('span', String(i), 'ln'));
      const code = make('code'); code.append(colorLine(lines[i - 1], ref.path, lexical)); row.append(code);
      listing.append(row);
    }
    scroll.append(listing); block.append(scroll);
    return block;
  }

  window.Teaching = {
    async init() {
      try {
        await loadData();
        if (workItems.length) selectWorkItem(workItems[0].id);
        renderExecGraph();
      } catch (e) {
        const host = el('teaching-view'); host.replaceChildren();
        host.append(make('p', '数据加载失败：' + e.message, 'learning-error'));
      }
    },
    // 切换项目后清缓存重载
    async reload() {
      workItems = []; files = {}; activeWork = null; activeSub = null; svgCache = null;
      await this.init();
    },
    selectWorkItem,
    openNodeDialog,
    getCurrent: () => currentItem(),
    getNodeRefs: name => {
      const item = currentItem();
      return item ? item.codeRefs : [];
    }
  };

  el('node-dialog-close').onclick = () => el('node-dialog').close();
  el('node-dialog').addEventListener('click', e => { if (e.target === el('node-dialog')) el('node-dialog').close(); });
  el('metric-dialog-close').onclick = () => el('metric-dialog').close();
  el('metric-dialog').addEventListener('click', e => { if (e.target === el('metric-dialog')) el('metric-dialog').close(); });
  // 执行图放大：克隆 SVG 进大图浮窗（保留高亮）
  el('graph-zoom').onclick = () => {
    const src = el('exec-graph').querySelector('svg');
    if (!src) return;
    const body = el('graph-dialog-body'); body.replaceChildren();
    const clone = src.cloneNode(true);
    clone.removeAttribute('id');
    body.append(clone);
    el('graph-dialog').showModal();
  };
  el('graph-dialog-close').onclick = () => el('graph-dialog').close();
  el('graph-dialog').addEventListener('click', e => { if (e.target === el('graph-dialog')) el('graph-dialog').close(); });
})();
