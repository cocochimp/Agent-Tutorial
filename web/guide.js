/* 项目导读：加载 guide-data.json（实习复盘手册非工作章节完整内容），左侧目录 + 右侧内容。 */
(() => {
  const el = id => document.getElementById(id);
  const make = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  let chapters = [], active = 0;

  async function load() {
    if (chapters.length) return;
    const r = await fetch('/static/guide-data.json', {cache: 'no-cache'});
    if (!r.ok) throw new Error('导读数据加载失败');
    chapters = (await r.json()).chapters || [];
  }

  function renderCats() {
    const nav = el('guide-cats'); nav.replaceChildren();
    chapters.forEach((c, i) => {
      const b = make('button', undefined, 'guide-cat' + (i === active ? ' active' : ''));
      b.setAttribute('aria-pressed', String(i === active));
      b.append(make('span', String(i + 1).padStart(2, '0'), 'g-no'), make('span', c.title));
      b.onclick = () => { active = i; renderCats(); renderContent(); };
      nav.append(b);
    });
  }

  function renderContent() {
    const host = el('guide-content'); host.replaceChildren();
    const c = chapters[active];
    if (!c) return;
    const head = make('div', undefined, 'guide-chapter-head');
    head.append(make('span', '第 ' + (active + 1) + ' 章', 'eyebrow'), make('h2', c.title));
    host.append(head);
    const body = make('div', undefined, 'guide-html');
    body.innerHTML = c.html || '<p class="small muted">（本章暂无内容）</p>';
    host.append(body);
    host.scrollIntoView({block: 'start', behavior: 'smooth'});
  }

  window.Guide = {
    async init() {
      try {
        await load();
        if (chapters.length) { renderCats(); renderContent(); }
      } catch (e) {
        const host = el('guide-view'); host.replaceChildren();
        host.append(make('p', '数据加载失败：' + e.message, 'learning-error'));
      }
    },
    select: i => { active = i; renderCats(); renderContent(); }
  };
})();
