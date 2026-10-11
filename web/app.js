const $ = id => document.getElementById(id);
const labels = {understand:'理解与鉴权',clarify:'澄清',agent_node:'规划下一步',schema_retrieval:'Schema 检索',query_sql:'SQL 查询',calculate:'指标计算',analyze:'漏斗分析',rag_search:'RAG 混合检索',generate_report:'生成报告',validate:'结果校验',human_approval:'人工审批',execute_action:'执行业务动作',finish:'保存记忆',retry_node:'重试',checkpoint_gate:'检查点'};
function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
async function api(url, options={}){const response=await fetch(url,{...options,headers:{'Content-Type':'application/json',...options.headers}});const body=await response.json();if(!response.ok)throw new Error(typeof body.detail==='string'?body.detail:JSON.stringify(body.detail||body));return body;}
function post(url,body){return api(url,{method:'POST',body:JSON.stringify(body)});}
function download(text,name,type){const a=node('a');const url=URL.createObjectURL(new Blob([text],{type}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function error(e){const box=$('login-error');box.hidden=false;box.textContent=e.message||String(e);}

// 视图切换：项目导读、实习项目教程、高频面试题三个 Tab。
function showView(view){
  const hidden = {guide: 'guide', teaching: 'teaching', interview: 'interview'}[view] !== view;
  $('guide-view').hidden = view !== 'guide';
  $('teaching-view').hidden = view !== 'teaching';
  $('interview-view').hidden = view !== 'interview';
  $('page-crumb').textContent = view === 'guide' ? '项目导读' : view === 'teaching' ? '实习项目' : '面试题库';
  for (const [id, v] of [['nav-guide','guide'], ['nav-teaching','teaching'], ['nav-interview','interview']]) {
    $(id).classList.toggle('active', v === view); $(id).setAttribute('aria-pressed', String(v === view));
  }
}
$('nav-guide').onclick = () => showView('guide');
$('nav-teaching').onclick = () => showView('teaching');
$('nav-interview').onclick = () => showView('interview');

function loggedIn(user){
  document.body.classList.remove('logged-out');
  $('who').textContent = user.user_id + ' · 学员';
  $('login-card').hidden = true;
  $('logout').hidden = false;
  showView('guide');
  if (window.Guide) window.Guide.init();
  if (window.Teaching) window.Teaching.init();
  if (window.Interview) window.Interview.init();
}

// —— Pages 静态模式支持 ——
// GitHub Pages 无法运行 FastAPI 后端，登录改为前端校验（账号密码与本地 accounts.json 一致）。
// 后端模式（本地部署）：走真实 /api/login 会话；静态模式（Pages）：前端比对后本地标记登录。
const STATIC_ACCOUNT = {username: 'chaoyang', password: 'demo-chaoyang'};
let staticMode = false;

async function detectModeAndRestore() {
  try {
    const r = await fetch('/api/session', {headers: {'Content-Type': 'application/json'}});
    if (r.status === 404) { staticMode = true; }          // 无后端（Pages）
    else {
      const value = await r.json();
      if (value && value.user) { loggedIn(value.user); return; }
    }
  } catch (e) { staticMode = true; }
  if (staticMode && localStorage.getItem('agent_tutorial_login') === '1') {
    loggedIn({user_id: STATIC_ACCOUNT.username});
  }
}

$('login').onclick = async () => {
  const username = $('username').value.trim();
  const password = $('password').value;
  if (staticMode) {
    if (username === STATIC_ACCOUNT.username && password === STATIC_ACCOUNT.password) {
      localStorage.setItem('agent_tutorial_login', '1');
      loggedIn({user_id: STATIC_ACCOUNT.username});
    } else {
      error({message: '账号或密码错误'});
    }
    return;
  }
  try { loggedIn(await post('/api/login', {username, password})); }
  catch (e) { error(e); }
};
$('logout').onclick = async () => {
  if (staticMode) localStorage.removeItem('agent_tutorial_login');
  else await post('/api/logout', {});
  location.reload();
};

detectModeAndRestore();
