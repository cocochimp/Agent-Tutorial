/* V2 导出：将工作项学习页 / 面试题清单导出为单文件、正文可编辑（contenteditable）的 HTML。
   导出的页面不依赖本服务，可直接用浏览器打开、修改后另存；样式沿用旧手册墨绿青主题。 */
(() => {
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  const shell = (title, body) => `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)}</title>
<style>
  :root{--ink:#1d2a35;--muted:#5f6d78;--line:#d7e0e5;--paper:#ffffff;--wash:#f4f7f8;--navy:#17324d;--teal:#087f8c;--orange:#c7682e;--green:#2d7c61;--shadow:0 14px 38px rgba(23,50,77,.10)}
  *{box-sizing:border-box}body{margin:0;background:var(--wash);color:var(--ink);font:14px/1.8 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;-webkit-font-smoothing:antialiased}
  .page{max-width:1080px;margin:0 auto;padding:36px 28px 60px}
  .page-head{margin-bottom:28px;padding:26px 30px;border-radius:10px;background:var(--navy);color:#fff;box-shadow:var(--shadow)}
  .page-head h1{font-size:26px;margin:0 0 8px;letter-spacing:-.5px;color:#fff}
  .page-head p{margin:0;color:#d9e7ef;font-size:12px}
  h2{font-size:17px;margin:30px 0 12px;color:var(--navy)}
  h3{font-size:14px;margin:18px 0 8px;color:var(--teal)}
  p{margin:8px 0}
  .card{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:20px 22px;margin:14px 0;box-shadow:0 5px 18px rgba(23,50,77,.04)}
  .resume{border-bottom:2px solid var(--navy);padding-bottom:12px}
  .resume .who{font-size:16px;font-weight:800;color:var(--navy)}
  .resume .who span{color:var(--teal)}
  .score{display:inline-flex;align-items:center;gap:6px;margin:4px 6px 0 0;padding:6px 10px;border-radius:5px;color:#315848;background:#e5f4eb;font-weight:700;font-size:12px}
  .story{border:1px solid #b8d5d8;border-radius:10px;overflow:hidden;background:#fbfefe;margin:14px 0}
  .story-head{padding:11px 15px;background:#dff1f2;color:var(--navy);font-weight:800;font-size:14px}
  .story-head small{margin-left:8px;color:var(--teal);font-weight:650}
  .story-body{padding:13px 16px 15px}
  .story-step{display:grid;grid-template-columns:96px 1fr;gap:11px;padding:9px 0;border-bottom:1px dashed #d8e5e7}
  .story-step:last-child{border-bottom:0}
  .story-step .badge{height:fit-content;padding:3px 7px;border-radius:4px;text-align:center;font-size:12px;font-weight:800;background:#e9f5f5;color:#245d65}
  .story-step.problem .badge{background:#fbe7d9;color:#9c4a1e}
  .story-step.action .badge{background:#e5eef8;color:#315d84}
  .story-step.result .badge{background:#e5f4eb;color:#315848}
  .story-step.interview .badge{background:#f4ebfa;color:#6b4682}
  .story-step .step-text{font-size:13px;line-height:1.85;color:#2c3b46}
  .qa-item{padding:8px 0;border-bottom:1px solid var(--line)}
  .qa-item:last-child{border-bottom:0}
  .qa-item strong{color:var(--navy)}
  .qa-item p{font-size:12px;color:#2c3b46;line-height:1.8;margin:4px 0 0}
  .io-block{border:1px solid #cfe0e2;border-radius:9px;margin:12px 0;overflow:hidden;background:#fbfefe}
  .io-block summary{padding:12px 15px;font-weight:700;font-size:13px;color:var(--navy);background:#eef3f5;border-bottom:1px solid #d8e5e7;cursor:pointer}
  .io-block summary .io-tag{font:10px Consolas,monospace;color:var(--teal);background:#e2f2f3;border-radius:4px;padding:2px 7px;margin-right:8px}
  .io-block .io-body{padding:12px 15px}
  .io-block h4{font-size:11px;color:var(--muted);margin:12px 0 6px;font-weight:700;text-transform:uppercase}
  pre{font:12px/1.7 "SFMono-Regular",Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#f6f8fc;border:1px solid #e3ebee;border-radius:8px;padding:13px;margin:0;color:#2c3b46}
  .code-block{border:1px solid #cfe0e2;border-radius:9px;overflow:hidden;margin:12px 0;background:#fff}
  .code-head{padding:9px 14px;background:#eef3f5;border-bottom:1px solid #d8e5e7;font:11px/1.6 Consolas,monospace;color:var(--teal)}
  .note{font-size:12px;color:var(--muted);background:#f7fafb;border-left:3px solid #9ab5be;padding:10px 13px;border-radius:4px;margin:12px 0}
  .tag{display:inline-block;font:10px Consolas,monospace;color:#245d65;background:#e2f2f3;border-radius:4px;padding:2px 8px;margin:0 6px 6px 0}
  .q-card{border:1px solid #cfe0e2;border-radius:10px;padding:18px 20px;background:#fbfefe;margin:14px 0;page-break-inside:avoid}
  .q-card .q{font-size:15px;color:var(--navy);font-weight:700;margin-bottom:10px}
  .q-tips{color:#8a6d3a;background:#fffaf0;border:1px solid #ead3a6;border-radius:8px;padding:12px 14px;margin:10px 0}
  .q-answer{color:#2c3b46;background:#f7fafb;border:1px solid #d8e5e7;border-radius:8px;padding:12px 14px}
  .q-step{display:flex;gap:8px;align-items:flex-start;margin:7px 0;padding:7px 10px;background:#fbfefe;border-left:3px solid var(--teal);border-radius:4px}
  .q-step .q-step-no{font:11px Consolas,monospace;color:var(--teal);padding-top:2px;flex:none}
  .q-step .q-step-label{flex:none;font-size:12px;font-weight:700;color:#1d4a52;background:#e2f2f3;border-radius:5px;padding:1px 8px;height:fit-content}
  .q-step p{margin:0;font-size:12.5px;line-height:1.8;color:#2c3b46}
  .editable{outline:1px dashed rgba(8,127,140,.28);outline-offset:2px;border-radius:3px;transition:outline-color .2s}
  .editable:focus{outline:2px solid #6db8be;background:#fffef5}
  .guide-html{font-size:13px;line-height:1.9;color:#2c3b46}
  .guide-html h3{font-size:16px;color:var(--teal);margin:26px 0 8px}.guide-html h4{font-size:14px;color:var(--orange);margin:20px 0 7px}
  .guide-html p{margin:9px 0}.guide-html ul,.guide-html ol{margin:9px 0 13px 22px;padding:0}.guide-html li{margin:5px 0}
  .guide-html code{padding:1px 5px;border-radius:4px;color:#8c431d;background:#fff1e8;font-family:Consolas,monospace;font-size:.92em}
  .guide-html pre{overflow:auto;margin:13px 0;padding:15px 17px;color:#e9f2f5;background:#172833;border-radius:6px;font:12.5px/1.65 Consolas,monospace;white-space:pre}
  .guide-html table{width:100%;border-collapse:collapse;margin:13px 0;font-size:12.5px}
  .guide-html th,.guide-html td{padding:9px 10px;text-align:left;vertical-align:top;border:1px solid var(--line)}
  .guide-html th{color:var(--navy);background:#eef3f5}
  .guide-html .mini{padding:14px 15px;border:1px solid var(--line);border-radius:6px;background:#fbfcfc;margin:13px 0}
  .guide-html .grid-2,.guide-html .grid-3{display:grid;gap:14px;margin:13px 0}
  .guide-html .grid-2{grid-template-columns:repeat(2,minmax(0,1fr))}.guide-html .grid-3{grid-template-columns:repeat(3,minmax(0,1fr))}
  .guide-html .case{margin:15px 0;border:1px solid #cfe0e2;border-radius:8px;background:#fbfdfd;overflow:hidden}
  .guide-html .case-title{padding:10px 14px;background:#e7f1f2;color:var(--navy);font-weight:800;border-bottom:1px solid #cfe0e2}
  .guide-html .case-body{padding:8px 16px 12px}
  .guide-html .case-body .row{display:flex;gap:10px;margin:9px 0}
  .guide-html .case-body .lbl{flex:0 0 84px;height:fit-content;padding:2px 8px;border-radius:4px;background:#e2f2f3;color:#245d65;font-size:12px;font-weight:700;text-align:center}
  .guide-html .truth-note{margin:16px 0;padding:12px 15px;border:1px solid #ead3a6;border-radius:6px;background:#fffaf0;color:#6d5528}
  .guide-html .qa details{padding:10px 0;border-bottom:1px solid var(--line)}
  .guide-html .qa summary{cursor:pointer;color:var(--navy);font-weight:700}
  .guide-html .answer{margin:9px 0 2px;padding:12px 14px;background:#f7fafb;border-left:3px solid #9ab5be;border-radius:4px}
  .guide-html mark{padding:0 2px;background:#ffe18e}
  .metric-detail{display:inline-block;margin:0 6px 6px 0;vertical-align:top}
  .metric-detail summary{list-style:none;cursor:pointer}
  .metric-detail summary .metric-hint{font-size:10px;color:var(--muted);font-weight:600}
  .metric-detail .metric-block{margin-top:8px;max-width:460px;padding:10px 13px;background:#f7fafb;border-left:3px solid var(--teal);border-radius:5px;font-size:12px;line-height:1.75;color:#2c3b46}
  .metric-detail .metric-block strong{display:block;color:var(--teal);margin:6px 0 3px;font-size:11px}
  .metric-detail .metric-block p{margin:0}
  .guide-html .flow{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:13px 0}
  .guide-html .flow span{padding:7px 10px;border:1px solid #b9d5d8;border-radius:5px;color:var(--navy);background:#f0fbfb;font-weight:700;font-size:12px}
  .foot{margin-top:34px;padding-top:14px;border-top:1px solid var(--line);font-size:11px;color:var(--muted)}
  @media print{.page{padding:20px 8px}}
  @media (max-width:700px){.story-step{grid-template-columns:1fr;gap:4px}}
</style>
</head>
<body>
<div class="page">
  <div class="page-head">
    <h1 contenteditable="true" class="editable">${esc(title)}</h1>
    <p contenteditable="true" class="editable">导出自教学网站 · 本页正文均可直接编辑修改</p>
  </div>
  ${body}
  <div class="foot">导出于豆包 · 学员教学网站</div>
</div>
</body>
</html>`;

  function workBody(item, files) {
    const out = [];
    out.push(`<h2>实习经历模版 · 对应条目</h2>`);
    out.push(`<div class="card" contenteditable="true" class="editable"><div class="resume"><div class="who">实习经历模版 · <span>${esc(item.resume.label)}</span></div></div><p>${esc(item.resume.text)}</p>`);
    if (item.resume.metrics) {
      const details = item.resume.metricDetails || [];
      out.push(`<div>` + item.resume.metrics.split('·').map(s => s.trim()).filter(Boolean).map((m, i) => {
        const d = details[i];
        return d
          ? `<details class="metric-detail"><summary class="score">${esc(m)} <span class="metric-hint">▸ 设计思路与数据来源</span></summary><div class="metric-block"><strong>设计思路 · 这个指标怎么定义和衡量</strong><p>${esc(d.design)}</p><strong>数据来源 · 数据从哪来、样本多大</strong><p>${esc(d.source)}</p></div></details>`
          : `<span class="score">${esc(m)}</span>`;
      }).join('') + `</div>`);
    }
    out.push(`</div>`);
    out.push(`<h2>内容介绍 · 实习复盘手册完整章节</h2>`);
    out.push(`<div class="card guide-html" contenteditable="true" class="editable">${item.introHtml || ''}</div>`);
    if (item.subTopics && item.subTopics.length) {
      item.subTopics.forEach(st => {
        out.push(`<h2>子主题 · ${esc(st.title)}</h2>`);
        out.push(`<div class="card guide-html" contenteditable="true" class="editable">${st.html || ''}</div>`);
      });
    }
    out.push(`<h2>执行节点（${item.nodes.length}）</h2>`);
    out.push(`<div class="card">` + (item.nodes.length ? item.nodes.map(n => `<span class="tag">${esc(n)}</span>`).join('') : '<span class="note" style="display:block">该工作项主要涉及工程化与评测能力，不绑定具体执行图节点。</span>') + `</div>`);
    out.push(`<h2>节点输入输出</h2>`);
    for (const io of item.io) {
      out.push(`<details class="io-block"${item.io.length === 1 ? ' open' : ''}><summary><span class="io-tag">输入 / 输出</span>${esc(io.node)}</summary><div class="io-body" contenteditable="true" class="editable">`);
      out.push(`<h4>输入 input</h4><pre>${esc(JSON.stringify(io.input, null, 2))}</pre>`);
      out.push(`<h4>输出 output</h4><pre>${esc(JSON.stringify(io.output, null, 2))}</pre>`);
      if (io.note) out.push(`<div class="note">${esc(io.note)}</div>`);
      out.push(`</div></details>`);
    }
    if (!item.io.length) out.push(`<div class="note">该工作项暂无绑定节点的输入输出记录。</div>`);
    if (item.codeRefs.length) {
      out.push(`<h2>实例代码</h2>`);
      for (const ref of item.codeRefs) {
        const file = files[ref.path];
        if (!file) { out.push(`<div class="note">源码文件缺失：${esc(ref.path)}</div>`); continue; }
        const lines = file.text.replace(/\r\n/g, '\n').split('\n');
        if (lines.at(-1) === '') lines.pop();
        const end = Math.min(ref.end, lines.length);
        out.push(`<div class="code-block"><div class="code-head">${esc(ref.path)} · L${ref.start}–${end}${ref.note ? ' · ' + esc(ref.note) : ''}</div>`);
        out.push(`<pre contenteditable="true" class="editable">${esc(lines.slice(ref.start - 1, end).join('\n'))}</pre></div>`);
      }
    }
    return out.join('\n');
  }

  function renderQ(q, i) {
    const out = [`<div class="q-card"><div class="q">${i + 1}. ${esc(q.q)}</div>`];
    if (q.points && q.points.length) {
      out.push(`<div class="q-tips" contenteditable="true" class="editable"><b>要点说明：</b><ul style="margin:6px 0 0 18px;padding:0">${q.points.map(p => `<li>${esc(p)}</li>`).join('')}</ul></div>`);
    }
    if (q.qa && q.qa.length) {
      for (const pair of q.qa) {
        const lines = String(pair.a).split('\n').map(s => s.trim()).filter(Boolean);
        if (lines.length > 1) {
          const steps = lines.map(line => {
            const m = line.match(/^(\d+)\.\s*(.*)$/);
            if (!m) return `<p>${esc(line)}</p>`;
            const body = m[2];
            const lm = body.match(/^([^：:]{1,12})[：:]\s*(.*)$/);
            return `<div class="q-step"><span class="q-step-no">${esc(m[1])}.</span><span class="q-step-label">${esc(lm ? lm[1] : '')}</span><p>${esc(lm ? lm[2] : body)}</p></div>`;
          }).join('');
          out.push(`<div class="q-answer" contenteditable="true" class="editable"><b>问：${esc(pair.q)}</b><br><b>参考回答：</b>${steps}</div>`);
        } else {
          out.push(`<div class="q-answer" contenteditable="true" class="editable"><b>问：${esc(pair.q)}</b><br><b>参考回答：</b>${esc(pair.a)}</div>`);
        }
      }
    }
    out.push(`</div>`);
    return out.join('\n');
  }

  function interviewBody(questions, topicTitle) {
    const out = [`<p><span class="tag">${esc(topicTitle)}</span><span class="tag">共 ${questions.length} 题</span></p>`];
    questions.forEach((q, i) => out.push(renderQ(q, i)));
    return out.join('\n');
  }

  // 按工作项分组全量导出（项目面试题 5 组共 54 题）
  function groupsBody(groups, topicTitle) {
    const total = groups.reduce((s, g) => s + g.questions.length, 0);
    const out = [`<p><span class="tag">${esc(topicTitle)}</span><span class="tag">共 ${total} 题（${groups.length} 个工作项）</span></p>`];
    let no = 0;
    groups.forEach(g => {
      out.push(`<h3 style="margin-top:26px">${esc(g.title)} <span class="tag" style="margin-left:6px">${g.questions.length} 题</span></h3>`);
      g.questions.forEach(q => { no += 1; out.push(renderQ(q, no)); });
    });
    return out.join('\n');
  }

  const download = (text, name) => {
    const a = document.createElement('a');
    const url = URL.createObjectURL(new Blob([text], {type: 'text/html;charset=utf-8'}));
    a.href = url; a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const nameOf = item => '工作' + item.id.replace('work-', '') + '_' + item.title.replace(/[^·\u4e00-\u9fa5A-Za-z0-9]/g, '').slice(0, 12) + '_学习页.html';
  const pid = () => (window.App && window.App.projectId()) || 'estate-agent';
  const projectName = () => (window.App && window.App.getProject() && window.App.getProject().name) || '';

  window.Export = {
    async guide() {
      // 导出「完整实习复盘手册」：动态拼最新内容（导读 + 五个工作项 + 指标展开 + 节点 io + 代码）
      const [guideRes, workRes, tutRes] = await Promise.all([
        fetch('static/projects/' + pid() + '/guide-data.json', {cache: 'no-cache'}),
        fetch('static/projects/' + pid() + '/work-items.json', {cache: 'no-cache'}),
        fetch('static/projects/' + pid() + '/tutorial-data.json', {cache: 'no-cache'})
      ]);
      if (!guideRes.ok || !workRes.ok) throw new Error('数据加载失败');
      const guide = await guideRes.json();
      const work = await workRes.json();
      const tut = tutRes.ok ? await tutRes.json() : {files: {}};
      const files = tut.files || {};

      const out = [];
      // Hero
      if (guide.hero) {
        out.push(`<div class="page-head" style="margin-top:0">`);
        out.push(`<p style="font-size:11px;letter-spacing:2px;color:#7fb3bb;margin:0 0 8px">${esc(guide.hero.eyebrow || '')}</p>`);
        out.push(`<h1 contenteditable="true" class="editable">${esc(guide.hero.title || projectName() || '')}</h1>`);
        out.push(`<p contenteditable="true" class="editable" style="margin:10px 0 0">${esc(guide.hero.desc || '')}</p>`);
        if (guide.hero.facts && guide.hero.facts.length) {
          out.push(`<div style="display:flex;gap:10px;margin-top:14px;flex-wrap:wrap">`);
          guide.hero.facts.forEach(f => out.push(`<div style="background:rgba(255,255,255,.12);border-radius:6px;padding:8px 14px"><div style="font-size:10px;color:#9fc4cb">${esc(f.label)}</div><div style="font-size:12px;color:#fff;font-weight:700">${esc(f.value)}</div></div>`));
          out.push(`</div>`);
        }
        out.push(`</div>`);
      }
      // 导读章节
      out.push(`<h2 style="margin-top:30px">📖 项目导读</h2>`);
      (guide.chapters || []).forEach((ch, idx) => {
        out.push(`<div class="card guide-html" contenteditable="true" class="editable">`);
        out.push(`<h3 style="margin-top:0">${esc(ch.title || ('第' + (idx+1) + '章'))}</h3>`);
        out.push(ch.html || '');
        out.push(`</div>`);
      });
      // 五个工作项
      out.push(`<h2 style="margin-top:36px">💼 实习项目 · 五个工作项</h2>`);
      (work.workItems || []).forEach(item => {
        out.push(`<div style="margin-top:24px;padding-top:18px;border-top:3px solid var(--navy)">`);
        out.push(`<h3 style="font-size:18px;color:var(--navy);margin:0 0 10px">${esc(item.title || item.id)}</h3>`);
        // 简历简介
        if (item.resume) {
          out.push(`<div class="card" contenteditable="true" class="editable">`);
          out.push(`<p style="margin:0;color:#2c3b46;line-height:1.85">${esc(item.resume.text || '')}</p>`);
          out.push(`</div>`);
        }
        // 指标展开（直接展开，不折叠）
        if (item.resume && item.resume.metricDetails && item.resume.metricDetails.length) {
          out.push(`<h4 style="margin:18px 0 8px;color:var(--teal);font-size:14px">📊 量化指标详解</h4>`);
          item.resume.metricDetails.forEach(md => {
            out.push(`<div class="card" style="border-left:3px solid var(--teal)" contenteditable="true" class="editable">`);
            out.push(`<div style="font-weight:800;color:var(--navy);margin-bottom:8px">${esc(md.title)}</div>`);
            // 面试话术（多段）
            String(md.design || '').split(/\n\n+/).filter(Boolean).forEach(p => out.push(`<p style="margin:8px 0;font-size:13px;line-height:1.85;color:#2c3b46">${esc(p)}</p>`));
            // 关键数字
            const nums = md.numbers || [];
            if (nums.length) {
              out.push(`<ul style="margin:10px 0 0 20px;padding:0">`);
              nums.forEach(n => out.push(`<li style="font-size:12.5px;color:#2c3b46;margin:4px 0">${esc(n)}</li>`));
              out.push(`</ul>`);
            }
            out.push(`</div>`);
          });
        }
        // 内容介绍（原手册章节）
        out.push(`<h4 style="margin:18px 0 8px;color:var(--teal);font-size:14px">📝 内容介绍</h4>`);
        out.push(`<div class="card guide-html" contenteditable="true" class="editable">${item.introHtml || ''}</div>`);
        // 子主题
        if (item.subTopics && item.subTopics.length) {
          item.subTopics.forEach(st => {
            out.push(`<h4 style="margin:16px 0 6px;color:var(--orange);font-size:13px">📌 ${esc(st.title)}</h4>`);
            out.push(`<div class="card guide-html" contenteditable="true" class="editable">${st.html || ''}</div>`);
          });
        }
        out.push(`</div>`);
      });
      download(shell(projectName() + ' · 实习复盘手册', out.join('\n')), (projectName() || '项目') + '_实习复盘手册.html');
    },
    workItem() {
      const item = window.Teaching && window.Teaching.getCurrent();
      if (!item) return;
      const r = fetch('static/projects/' + pid() + '/tutorial-data.json', {cache: 'no-cache'});
      r.then(res => res.ok ? res.json() : {files: {}}).then(({files}) => {
        download(shell(item.title + ' · 学习页', workBody(item, files)), nameOf(item));
      });
    },
    async interview() {
      // 项目面试题：一次导出全部工作项题目（分组展示）；八股题：导出该子题库全部题目。
      const t = window.Interview ? window.Interview.getCurrentTopic() : null;
      if (!t) return;
      const catName = t.title;
      const [proj, common] = await Promise.all([
        fetch('static/projects/' + pid() + '/interview-topics.json', {cache: 'no-cache'}).then(r => r.ok ? r.json() : {topics: []}),
        fetch('static/interview-common.json', {cache: 'no-cache'}).then(r => r.ok ? r.json() : {topics: []})
      ]);
      const topic = [...(proj.topics || []), ...(common.topics || [])].find(x => x.id === t.id);
      if (!topic) return;
      if (topic.groups) {
        download(shell(catName, groupsBody(topic.groups, catName)), (projectName() ? projectName() + '_' : '') + catName + '_练习清单.html');
      } else if (topic.questions && topic.questions.length) {
        download(shell(catName, interviewBody(topic.questions, catName)), (projectName() ? projectName() + '_' : '') + catName + '_练习清单.html');
      }
    }
  };
  const bind = () => {
    const g = document.getElementById('export-guide');
    if (g) g.onclick = () => window.Export.guide();
    const i = document.getElementById('export-interview');
    if (i) i.onclick = () => window.Export.interview();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
})();
