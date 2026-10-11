/* 工作台的视图与展示层。所有指标取自任务状态，不在页面中生成演示业绩。 */
(() => {
  const el = id => document.getElementById(id);
  let currentView = 'report', latestState = null;
  const names = {report:'分析工作台',graph:'执行过程',trace:'执行记录',history:'历史任务',actions:'工单收件箱'};
  const make = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };

  function syncNavigation() {
    const learn = !el('learning-panel').hidden;
    el('page-crumb').textContent = learn ? '实现教程' : names[currentView];
    el('nav-workspace').classList.toggle('active', !learn && ['report','graph','trace'].includes(currentView));
    el('nav-workspace').setAttribute('aria-pressed', String(!learn && ['report','graph','trace'].includes(currentView)));
    document.querySelectorAll('[data-view]').forEach(b => {
      const selected = !learn && b.dataset.view === currentView;
      b.classList.toggle('active', selected); b.setAttribute('aria-pressed', String(selected));
    });
  }

  function selectView(view) {
    if (!names[view]) return;
    currentView = view;
    for (const name of Object.keys(names)) el('panel-' + name).hidden = name !== view;
    document.querySelector('.workbench-tabs').hidden = ['history','actions'].includes(view);
    document.querySelectorAll('[data-panel]').forEach(b => {
      const selected = b.dataset.panel === view;
      b.classList.toggle('active', selected); b.setAttribute('aria-selected', String(selected));
      b.tabIndex = selected ? 0 : -1;
    });
    syncNavigation();
  }

  document.querySelectorAll('[data-panel]').forEach(b => {
    b.onclick = () => selectView(b.dataset.panel);
    b.onkeydown = event => {
      const keys = ['ArrowLeft','ArrowRight','Home','End'];
      if (!keys.includes(event.key)) return;
      event.preventDefault();
      const tabs = Array.from(document.querySelectorAll('[data-panel]')), i = tabs.indexOf(b);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length-1 : (i+(event.key === 'ArrowRight' ? 1 : -1)+tabs.length)%tabs.length;
      selectView(tabs[next].dataset.panel); tabs[next].focus();
    };
  });
  document.querySelectorAll('[data-view]').forEach(b => {
    b.onclick = () => {
      el('nav-workspace').click(); selectView(b.dataset.view);
      window.scrollTo({top:0,behavior:'instant'});
    };
  });
  el('nav-workspace').addEventListener('click', () => selectView('report'));
  document.addEventListener('agent:view', syncNavigation);
  document.querySelectorAll('.app-sidebar .nav-tab').forEach(b => {
    const label=b.querySelector('span')?.textContent.trim()||b.textContent.trim();
    b.setAttribute('aria-label',label); b.title=label;
  });
  el('focus-question').onclick = () => {
    el('question').scrollIntoView({block:'center',behavior:'instant'}); el('question').focus({preventScroll:true});
  };

  function resetOverview() {
    el('overview-status').textContent = '提交中';
    el('overview-steps').textContent = '—'; el('overview-evidence').textContent = '—';
    el('overview-verification').textContent = '—'; el('overview-id').textContent = '正在创建分析任务';
    el('trace-count').textContent = '0'; el('trace-placeholder').hidden = false;
    el('empty').hidden = false;
    el('empty').classList.add('is-running');
    el('empty').querySelector('h3').textContent='正在准备分析';
    el('empty').querySelector('p').textContent='任务提交后，可切换到执行过程查看实时进度。';
    el('focus-question').hidden=true;
    selectView('report');
  }
  el('run').addEventListener('click', resetOverview);
  document.addEventListener('agent:submit-error', () => {
    el('overview-status').textContent = '提交失败'; el('overview-id').textContent = '请查看错误信息后重试';
    el('empty').classList.remove('is-running');
    el('empty').querySelector('h3').textContent='本次分析未能开始';
    el('empty').querySelector('p').textContent='请检查上方错误信息，调整设置后重新提交。';
    el('focus-question').hidden=false;
  });

  function updateOverview(state) {
    latestState = state;
    el('overview-status').textContent = statuses[state.status] || state.status;
    el('overview-id').textContent = state.run_id ? 'ID ' + state.run_id : '当前分析任务';
    el('overview-steps').textContent = String((state.trace || []).length);
    el('trace-count').textContent = String((state.trace || []).length);
    el('trace-placeholder').hidden = !!state.trace?.length;
    el('overview-evidence').textContent = state.report ? String(state.report.knowledge?.length || 0) : '—';
    el('overview-verification').textContent = state.verification ? (state.verification.passed ? '已通过' : '待复核') : '待校验';
    // render() 同步构造报告 DOM；微任务在它结束之后加入派生图表，避免重复插入。
    queueMicrotask(() => {
      if (latestState !== state) return;
      if(!state.report){
        const running=['running','queued'].includes(state.status);
        el('empty').hidden=false;el('empty').classList.toggle('is-running',running);
        el('empty').querySelector('h3').textContent=running?'分析正在进行':state.status==='waiting'?'等待补充信息':'任务尚未生成报告';
        el('empty').querySelector('p').textContent=running?'可切换到执行过程或 Trace 查看节点进度。':'请查看上方提示，补充信息或调整问题后继续。';
        el('focus-question').hidden=running;
      }else el('empty').classList.remove('is-running');
      renderComparison(state.report);
      document.querySelectorAll('#result>details').forEach(d => d.classList.add('evidence-card'));
    });
  }

  function renderComparison(report) {
    document.querySelector('#result .comparison-chart')?.remove();
    if (!report?.facts?.length) return;
    const rows = report.facts;
    const numbers = rows.flatMap(f => [f.previous_rate, f.current_rate]).filter(Number.isFinite);
    if (!numbers.length) return;
    // 两个时期共用同一个零起点坐标轴，避免各自归一化造成误读。
    const maximum = Math.max(.1, Math.ceil(Math.max(...numbers) * 10) / 10);
    const chart = make('section', undefined, 'comparison-chart'); chart.setAttribute('aria-label','门店指标前后期对比');
    const heading = make('div', undefined, 'chart-heading'), legend = make('div', undefined, 'chart-legend');
    for (const label of ['前期','本期']) { const span = make('span'); span.append(make('i'),make('span',label)); legend.append(span); }
    heading.append(make('h3',report.metric_label+' · 门店对比'),legend); chart.append(heading);
    for (const fact of rows) {
      const row = make('div',undefined,'bar-row'), pair = make('div',undefined,'bar-pair');
      row.setAttribute('role','img'); row.setAttribute('aria-label',fact.name+'：前期'+pct(fact.previous_rate)+'，本期'+pct(fact.current_rate));
      for (const value of [fact.previous_rate,fact.current_rate]) {
        const track=make('div',undefined,'bar-track'), fill=make('span',undefined,'bar-fill');
        fill.style.width=Number.isFinite(value)?Math.max(0,value/maximum*100)+'%':'0%'; track.append(fill); pair.append(track);
      }
      row.append(make('span',fact.name),pair,make('b',pct(fact.current_rate))); chart.append(row);
    }
    const axis=make('div',undefined,'chart-axis');
    for(const value of [0,maximum/2,maximum])axis.append(make('span',Math.round(value*100)+'%'));
    chart.append(axis,make('div','同一坐标轴 · 数值来自本次 SQL 聚合与指标计算 [SQL-01]','chart-foot'));
    const table = document.querySelector('#result .table-wrap');
    if(table)table.before(chart);else el('result').append(chart);
  }

  document.addEventListener('agent:state', e => updateOverview(e.detail));
  document.addEventListener('agent:task-open', () => selectView('report'));
  // 处理快速接口响应先于本脚本初始化的情况。
  if (typeof last !== 'undefined' && last) updateOverview(last);
  syncNavigation();
})();
