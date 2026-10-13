/* 面试板块：自我介绍/反问 + 模版简历（全站级，不随项目切换）。
 * 数据来源：2.2 自我介绍模板 / 2.3 技术面反问 / 2.4 HR面反问（用户提供截图）；
 *           优秀简历模版（用户提供 PDF，2 页）。导出 PDF 直接下载文件（html-to-image + jsPDF 生成）。 */
window.Prep = (() => {
  const $ = id => document.getElementById(id);
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  };
  const icon = p => {
    const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    s.setAttribute('viewBox', '0 0 24 24');
    s.setAttribute('fill', 'none');
    s.setAttribute('stroke', 'currentColor');
    s.setAttribute('stroke-width', '1.6');
    s.setAttribute('stroke-linecap', 'round');
    s.setAttribute('stroke-linejoin', 'round');
    s.classList.add('icon');
    s.innerHTML = p;
    return s;
  };

  /* ============ 数据：自我介绍 / 反问 ============ */
  const INTRO_TEMPLATE = {
    title: '2.2 自我介绍模板',
    note: '按「开场 → 校园与团队 → 赛事与学术 → 实习 → 收尾」四段式讲，每段 20~30 秒，总时长控制在 1.5~2 分钟。括号内为可替换占位符，填自己的真实经历。',
    steps: [
      { label: '开场问候', text: '面试官您好！我是今天的求职者【姓名】，今年【年龄】岁，来自【学校】【专业】专业，目前【年级】在读，今天应聘的岗位是【目标岗位】。' },
      { label: '校园与团队经历', text: '我在【大X学期/具体时间】加入学校【团队/实验室名称】，【时间】起担任【团队职务，如队长/后端负责人/技术组长】，带领团队承接校内外创新、创业类竞赛与项目落地，累计取得【团队核心成果，X项省级以上奖项】。期间我主导负责过【数量】个校级重点项目，代表性项目包括【项目1名称】、【项目2名称】等，覆盖【领域，如智能硬件、业务系统开发】等场景。' },
      { label: '赛事与学术成果', text: '课余时间我独立完成了【数量】个个人项目，累计获得【数量】项软件著作权、【数量】篇期刊/会议论文；竞赛方面，获得过【最高级别竞赛+奖项，如全国大学生数学建模竞赛国家级二等奖】，以及【数量】余项国家级、省级赛事奖项。学业上连续【年限】年综测排名专业前【排名比例，如5%】，先后获得【荣誉，如一等奖学金、校级三好学生】等荣誉。' },
      { label: '实习经历', text: '最后是我的实习经历：我先后有【数量】段相关实习经历：第一段是【起止时间】，在【公司名称】担任【岗位】，负责【核心业务方向】；第二段是【起止时间】，在【公司名称】担任【岗位】，参与【核心业务方向】。两段实习让我积累了工程落地、业务理解和团队协作的实战经验，也让我能更快地适配岗位要求。' },
      { label: '收尾', text: '以上是我的个人介绍，感谢面试官的聆听。' }
    ]
  };

  const TECH_QUESTIONS = {
    title: '2.3 反问环节（技术面）',
    note: '技术面反问围绕「部门业务、技术栈、岗位要求、自身差距、成长路径」展开，展示你的技术判断力与学习意愿。',
    items: [
      '部门承担的项目业务是有哪些？',
      '部门项目的技术栈有哪些？',
      '针对现在面试的这个岗位，您希望候选人有哪些方面的特质？',
      '跟你们的预期相比，我有哪些优势或者不足？（感觉没戏或者不知道有没有戏的时候可以问）',
      '公司对新人的培育方案是什么样的？（怎么让我们快速融入到公司，进入到工作的节奏里）'
    ]
  };

  const HR_QUESTIONS = {
    title: '2.4 反问环节（HR面）',
    note: 'HR 面重点确认「发展空间 + 钱 + 工作状态」，把不稳定因素在入职前问清楚。带 ⚠ 的条目需特别注意。',
    groups: [
      { name: '部门项目发展', items: ['目标、挑战是什么？（OKR 短期 or 长期）'] },
      { name: '公司业务', items: ['公司当前的核心业务与市场定位？部门的业务在整个公司中的位置？'] },
      {
        name: '薪资', warn: true,
        items: [
          { t: '底薪、绩效、年终奖是怎么分配的？' },
          { t: '绩效考核的标准是什么？' },
          { t: '薪资结构（是否有绩效，绩效比例多少）' },
          { t: '五险一金（保险档数，公积金缴纳比例、缴纳基数）' },
          { t: '每个月几号发薪水', mark: '15号以后的慎重' },
          { t: '工作时间（强度，弹性的话问平均）' },
          { t: '试用期', mark: '大于6个月慎重；跟正式员工的区别（薪资必须>=80%）' },
          { t: '福利待遇（年假病假、餐补/房补/打车报销）' },
          { t: '涨薪/晋升机制', mark: '多久一次涨薪 · 晋升机会' }
        ]
      }
    ]
  };

  /* ============ 数据：优秀简历模版（PDF 2 页） ============ */
  const RESUME = {
    head: { name: 'XXX', intent: 'AI Agent 应用开发工程师', contact: ['电话：1xxx', '邮箱：xxx', '籍贯：xxx'] },
    education: {
      school: 'xxx 大学 · xxx 专业', tag: '本科 | 成绩：专业前 30%', range: '2023.09 - 2027.06',
      awards: ['第十七届蓝桥杯省级一等奖', '2025 年全国大学生数学建模竞赛省级一等奖', '第十五届软件杯省级银奖']
    },
    skills: {
      note: '思路：背概念，引导到实习/项目经历',
      items: [
        { k: 'Agent', v: 'ReAct、工具调用（Function Calling、Pydantic 校验）、LangGraph / Function Calling' },
        { k: 'RAG', v: '向量检索/召回（BM25、Embedding）、融合与精排（RRF、Cross-Encoder）、向量库（Milvus）' },
        { k: 'LLM', v: 'Transformer（MHA, FFN）、大模型微调（SFT、LoRA）、Harness Engineering、强化学习（GRPO）' },
        { k: '中间件', v: 'MySQL（索引，事务隔离）、Redis（持久化，缓存一致性）' }
      ]
    },
    internship: {
      note: '主要强调：为什么做？怎么做的？成果？',
      company: '去哪儿旅行 · 机票售后经营组', role: 'AI Agent 开发实习生', range: '2026.03 - 2026.08',
      background: '面向机票退改签咨询与办理场景，解决通用大模型「政策记错、差价报错、多轮咨询断片、费用金额编造」四类问题，构建覆盖「意图理解 → 检索 → 记忆 → 生成」全链路的垂直领域智能体。',
      items: [
        { t: 'ReAct 规划编排', m: '工具调用准确率 ≥92%',
          d: '将航班状态查询、差价计算、退改签规则检索、方案生成、出票封装为 Function Calling 工具，基于 ReAct 做多步推理与工具调度，并用 LangGraph 编排「解析→检索→确认→生成→校验」状态机（含置信度阈值与 human-in-the-loop）。',
          ps: '让系统自己会「查状态 → 找政策 → 算差价 → 讲清楚」：用户一句口语诉求，拆成可单独调用的工具，让系统自己判断先做哪一步、出错如何重试，减少调错和跳步，工具调用准确率做到 92%。' },
        { t: '多模态/增强 Query 理解', m: '复杂场景检索解决率提升 25%',
          d: '自然语言诉求经订单字段对齐后，再做上下文改写、一句话多诉求拆解、HyDE、Step-back 政策泛化，输出「意图/航司/舱位/票价产品」结构化字段驱动下游 filter。',
          ps: '先把诉求读懂，再去检索：解决「一句话里又想退又想改」「『它』指哪张票」这类情况——先把诉求拆清、把没说完整的追问补全，复杂场景下正确匹配到政策的比例提升 25%。' },
        { t: '混合检索与结果精排', m: '政策命中率提升 18%',
          d: '搭建语义检索 BGE 与关键词检索 BM25 双路并行、融合排序 RRF 与相关性精排的规则库匹配方案。',
          ps: '让政策搜得到、也搜得准：针对「用户口语和规则文档写法差很远」，把「按语义搜」和「按关键词搜」结合，再对结果重新排序。可细化：稠密向量召回（BGE + HNSW）+ 稀疏 BM25 双路（各 topK=60）经 RRF 融合取 Top 40，BGE-Reranker（Cross-Encoder）精排至 Top 10，再叠加多维度排序 + MMR 去冗余；粗召回 Recall@100 84%→96%。' },
        { t: '上下文与记忆系统', m: '多轮追问理解准确率提升 30%，Token 成本下降约 70%',
          d: '建设多轮会话短期记忆与用户长期画像，配合上下文动态注入与压缩。',
          ps: '让它记得住上下文，也越用越懂这个用户：既记得上一轮讲了哪张票、哪个方案（多轮追问不断片），也逐步记住该用户的常出行航线与退改偏好（越用越贴合），同时控制每次携带的信息量。短期会话记忆（多轮指代消解 + 滑动窗口摘要压缩，Redis 缓存会话状态）与长期用户画像（常旅客等级、历史退改偏好，向量化存储、检索时作个性化 boost）；设计 token 预算分配与上下文动态注入。' },
        { t: '方案生成与质量保障', m: '方案正确率提升至 96%',
          d: '以检索政策与工具返回差价为唯一依据约束模型输出，引入金额结构化校验、政策事实核查与人工兜底，并建设分航司/舱位的「金标准」评测集。',
          ps: '保证答得对、不编价：只允许模型依据检索到的真实政策和引擎算的差价作答，再加一道金额与政策引用的核查，拿不准就转人工；并整理了一套覆盖多航司/舱位的用例用于验证效果。以检索/工具命中内容为唯一数据源，LLM 强制 JSON 结构化输出 + 金额逐项校验（正则抽金额与工具字段比对）；引入 Fact-Checker（阈值 0.85）+ 硬规则后过滤，低于阈值触发 Self-Refinement；构建分航司/舱位评测集（金标准 + 禁止错误类型），方案正确率 ≥96%，单次对话 Token 成本降 60%–80%、P99 ≤ 1.2s。' }
      ],
      stack: 'Python、LangGraph、Function Calling、检索增强（向量 + 关键词混合检索、融合排序、精排/重排）、自然语言 + 订单结构化输入理解、Prompt 工程、事实核查与结构化输出、Redis。'
    },
    project: {
      note: '主要强调：个人方案设计？技术深度？',
      name: 'AI 图像开放平台（个人开发）', range: '2025.06 - 2025.09',
      stack: 'Java · Spring Cloud Gateway · Redis（Lua 脚本）· RabbitMQ · MySQL · Prometheus · Grafana · JMeter',
      background: '个人开发 AI 图像开放平台，对外提供文生图、智能抠图、图像超分等 API 服务，后端依赖 GPU 推理集群，单次推理成本高、容量有限。调用方分为免费版、专业版、企业版三个等级，需防止单个用户超量调用导致 GPU 成本失控，同时保护后端推理集群不被突发流量打垮，保证多网关实例场景下计数准确；图像生成采用异步任务模式，提交任务后经消息队列由 Worker 执行推理。',
      items: [
        '双维度限流模型：用户维度按等级配置差异化算力配额，超限返回 429；URL 维度设置接口级全局水位保护 GPU 集群容量；按能力分组统计配额，防止将同一能力拆成多个 URL 绕过限流。',
        '分布式计数一致性：使用 Redis Lua 脚本原子执行「检查 + 计数」操作，在本地多实例测试环境中验证并发场景无超配额放行；计数 Key 惰性创建并加 TTL 随机抖动，避免整点过期压力。',
        'Redis Key 结构与算法组合：以固定窗口为主（INCR + EXPIRE），热点接口（文生图、抠图）切换滑动窗口或令牌桶支持短时突发；分钟、天两级窗口分别控制瞬时峰值与全天成本。',
        '异步任务闭环：网关通过限流后生成 taskId 投递消息队列，GPU Worker 消费执行推理并写对象存储，客户端轮询/回调获取结果；任务提交时即扣减配额，防止恶意刷算力。',
        '配置热加载与降级策略：配置变更后定时刷新，规则约 10 秒生效无需重启；按接口成本分级降级，Redis 故障时高成本接口拒绝、低成本接口放行，配合本地内存限流兜底。'
      ],
      result: '限流判定延迟本地实测约 3–5ms，每次判定仅 1–2 次 Redis 调用；压测验证各等级分别在各自水位被精确拦截，无超配额放行；配置变更约 10 秒生效、无需重启；按能力分组统计有效防止 URL 拆分绕过限流；异步任务链路跑通「提交→排队→推理→回调」全流程，任务状态流转正确。'
    }
  };

  /* ============ 渲染：自我介绍 / 反问 ============ */
  function renderIntro() {
    const card = el('section', 'card');
    const head = el('div', 'card-heading');
    const htitle = el('div', 'heading-title');
    const secIcon = el('span', 'section-icon');
    secIcon.append(icon('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'));
    htitle.append(secIcon, el('h2', undefined, INTRO_TEMPLATE.title));
    head.append(htitle, el('span', 'eyebrow', 'SELF INTRO'));
    card.append(head, el('p', 'panel-description', INTRO_TEMPLATE.note));
    const steps = el('div', 'intro-steps');
    INTRO_TEMPLATE.steps.forEach((s, i) => {
      const row = el('div', 'intro-step');
      row.append(el('span', 'intro-step-no', String(i + 1).padStart(2, '0')), el('b', 'intro-step-label', s.label), el('p', 'intro-step-text', s.text));
      steps.append(row);
    });
    card.append(steps);
    return card;
  }

  function renderTech() {
    const card = el('section', 'card');
    const head = el('div', 'card-heading');
    const htitle = el('div', 'heading-title');
    const secIcon = el('span', 'section-icon');
    secIcon.append(icon('<path d="M8 9l-4 3 4 3M16 9l4 3-4 3m-2-9-4 12"/>'));
    htitle.append(secIcon, el('h2', undefined, TECH_QUESTIONS.title));
    head.append(htitle, el('span', 'eyebrow', 'TECH ROUND'));
    card.append(head, el('p', 'panel-description', TECH_QUESTIONS.note));
    const list = el('ol', 'ask-list');
    TECH_QUESTIONS.items.forEach((q, i) => {
      const li = el('li', 'ask-item');
      li.append(el('span', 'ask-no', String(i + 1)), el('span', 'ask-text', q));
      list.append(li);
    });
    card.append(list);
    return card;
  }

  function renderHr() {
    const card = el('section', 'card');
    const head = el('div', 'card-heading');
    const htitle = el('div', 'heading-title');
    const secIcon = el('span', 'section-icon');
    secIcon.append(icon('<path d="M3 3h18v18H3z"/><path d="M3 9h18M9 21V9"/>'));
    htitle.append(secIcon, el('h2', undefined, HR_QUESTIONS.title));
    head.append(htitle, el('span', 'eyebrow', 'HR ROUND'));
    card.append(head, el('p', 'panel-description', HR_QUESTIONS.note));
    const groups = el('div', 'hr-groups');
    HR_QUESTIONS.groups.forEach(g => {
      const box = el('div', 'hr-group' + (g.warn ? ' hr-warn' : ''));
      const ghead = el('div', 'hr-group-head');
      ghead.append(el('b', undefined, g.name), g.warn ? el('span', 'pill', '薪资敏感区 · 入职前问清') : null);
      box.append(ghead);
      const ul = el('ul', 'ask-list hr-ask-list');
      g.items.forEach((it, i) => {
        const q = typeof it === 'string' ? { t: it, mark: null } : it;
        const li = el('li', 'ask-item');
        li.append(el('span', 'ask-no', String(i + 1)), el('span', 'ask-text', undefined));
        li.lastChild.append(document.createTextNode(q.t));
        if (q.mark) li.lastChild.append(el('em', 'ask-mark', q.mark));
        ul.append(li);
      });
      box.append(ul);
      groups.append(box);
    });
    card.append(groups);
    return card;
  }

  /* ============ 渲染：模版简历 ============ */
  function resumeSection(title, note, body) {
    const sec = el('section', 'resume-sec');
    const head = el('div', 'resume-sec-head');
    head.append(el('h3', undefined, title));
    if (note) head.append(el('small', 'resume-sec-note', note));
    sec.append(head, body);
    return sec;
  }

  function resumeWorkItem(item, index) {
    const wrap = el('div', 'rwi');
    const head = el('div', 'rwi-head');
    head.append(el('span', 'rwi-no', String(index).padStart(2, '0')), el('b', 'rwi-title', item.t), el('span', 'rwi-metric', item.m));
    wrap.append(head, el('p', 'rwi-desc', item.d));
    if (item.ps) {
      const det = el('details', 'rwi-ps');
      det.append(el('summary', undefined, '怎么讲（PS 讲解）'));
      det.append(el('p', undefined, item.ps));
      wrap.append(det);
    }
    return wrap;
  }

  function buildResumeView() {
    const root = el('div', 'resume-doc');

    const head = el('div', 'resume-headbar');
    const h1 = el('h2', 'resume-name', RESUME.head.name);
    const intent = el('div', 'resume-intent', RESUME.head.intent);
    const contact = el('div', 'resume-contact');
    RESUME.head.contact.forEach(c => contact.append(el('span', undefined, c)));
    head.append(h1, intent, contact);
    root.append(head);

    // 教育经历
    const edu = el('div');
    const eduLine = el('div', 'edu-line');
    eduLine.append(el('b', undefined, RESUME.education.school), el('span', 'edu-tag', RESUME.education.tag), el('span', 'edu-range', RESUME.education.range));
    const awards = el('div', 'award-row');
    RESUME.education.awards.forEach(a => awards.append(el('span', 'tag', a)));
    edu.append(eduLine, awards);
    root.append(resumeSection('教育经历', null, edu));

    // 专业技能
    const sk = el('div', 'skill-list');
    RESUME.skills.items.forEach(s => {
      const row = el('div', 'skill-row');
      row.append(el('b', undefined, s.k + '：'), el('span', undefined, s.v));
      sk.append(row);
    });
    root.append(resumeSection('专业技能', RESUME.skills.note, sk));

    // 实习经历
    const inSec = el('div');
    const inHead = el('div', 'org-line');
    inHead.append(el('b', undefined, RESUME.internship.company + ' · ' + RESUME.internship.role), el('span', 'edu-range', RESUME.internship.range));
    inSec.append(inHead, el('p', 'rwi-bg', RESUME.internship.background));
    const items = el('div');
    RESUME.internship.items.forEach((it, i) => items.append(resumeWorkItem(it, i + 1)));
    const stack1 = el('p', 'rwi-stack');
    stack1.append(el('b', undefined, '技术栈：'), document.createTextNode(RESUME.internship.stack));
    inSec.append(items, stack1);
    root.append(resumeSection('实习经历', RESUME.internship.note, inSec));

    // 项目经历
    const pj = el('div');
    const pjHead = el('div', 'org-line');
    pjHead.append(el('b', undefined, RESUME.project.name), el('span', 'edu-range', RESUME.project.range));
    const stack2 = el('p', 'rwi-stack');
    stack2.append(el('b', undefined, '技术栈：'), document.createTextNode(RESUME.project.stack));
    pj.append(pjHead, stack2, el('p', 'rwi-bg', RESUME.project.background));
    const plist = el('ol', 'proj-list');
    RESUME.project.items.forEach((it, i) => {
      const li = el('li', 'proj-item');
      li.append(el('span', 'proj-no', String(i + 1)), el('span', undefined, it));
      plist.append(li);
    });
    const resultP = el('p', 'proj-result');
    resultP.append(el('b', undefined, '核心成果：'), document.createTextNode(RESUME.project.result));
    pj.append(plist, resultP);
    root.append(resumeSection('项目经历', RESUME.project.note, pj));

    return root;
  }

  /* ============ 导出 PDF（直接下载文件；html2pdf 不可用时回退打印） ============ */
  function printHtml() {
    const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const jobs = RESUME.internship.items.map((it, i) => `
      <div class="rj">
        <div class="rj-h"><b>${i + 1}. ${esc(it.t)}</b><span class="rj-m">${esc(it.m)}</span></div>
        <p class="rj-d">${esc(it.d)}</p>
        <p class="rj-ps">怎么讲：${esc(it.ps)}</p>
      </div>`).join('');
    const projs = RESUME.project.items.map((it, i) => `<li>${i + 1}. ${esc(it)}</li>`).join('');
    return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>优秀简历模版</title>
<style>
  @page { size: A4; margin: 16mm 15mm; }
  * { box-sizing: border-box; }
  body { margin: 0; color: #1d2a35; font: 12px/1.75 -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; }
  .resume-print { width: 190mm; max-width: 190mm; margin: 0 auto; }
  .rs { page-break-inside: avoid; }
  .rj { page-break-inside: avoid; }
  .rh { border-bottom: 2.5px solid #17324d; padding-bottom: 10px; margin-bottom: 14px; }
  .rh h1 { margin: 0 0 2px; font-size: 22px; color: #17324d; }
  .rh .ri { font-size: 13px; color: #087f8c; font-weight: 700; }
  .rh .rc { font-size: 10px; color: #5f6d78; margin-top: 3px; }
  .rs { margin: 13px 0 6px; font-size: 14px; color: #17324d; border-left: 4px solid #087f8c; padding-left: 8px; }
  .rs-note { font-size: 9px; color: #5f6d78; font-weight: 400; margin-left: 8px; }
  .org { font-size: 12.5px; margin-bottom: 3px; }
  .org b { color: #17324d; }
  .org .range { float: right; color: #5f6d78; font-size: 11px; }
  .bg { color: #2c3b46; margin: 5px 0; }
  .rj { margin: 7px 0; }
  .rj-h b { color: #17324d; font-size: 12px; }
  .rj-m { float: right; font-size: 10px; color: #087f8c; font-weight: 700; }
  .rj-d { margin: 2px 0; }
  .rj-ps { margin: 2px 0 0; font-size: 10px; color: #6d5528; background: #fffaf0; border-left: 3px solid #ead3a6; padding: 4px 8px; }
  .sk p { margin: 3px 0; } .sk b { color: #17324d; }
  .awards { margin: 4px 0 0; color: #315848; }
  ul { margin: 5px 0; padding-left: 18px; }
  li { margin: 4px 0; }
  .stack { font-size: 11px; margin: 6px 0 0; }
  .stack b { color: #17324d; }
  .result { font-size: 11.5px; background: #f2fafb; border-left: 3px solid #b9d5d8; padding: 6px 9px; margin-top: 7px; }
</style></head>
<body><div class="resume-print">
  <div class="rh"><h1>${esc(RESUME.head.name)}</h1><div class="ri">求职意向：${esc(RESUME.head.intent)}</div>
    <div class="rc">${RESUME.head.contact.map(esc).join('　·　')}</div></div>

  <div class="rs">教育经历</div>
  <div class="org"><b>${esc(RESUME.education.school)}</b> <span class="range">${esc(RESUME.education.range)}</span><span>（${esc(RESUME.education.tag)}）</span></div>
  <div class="awards">${RESUME.education.awards.map(esc).join('；')}</div>

  <div class="rs">专业技能<span class="rs-note">（${esc(RESUME.skills.note)}）</span></div>
  <div class="sk">${RESUME.skills.items.map(s => `<p><b>${esc(s.k)}：</b>${esc(s.v)}</p>`).join('')}</div>

  <div class="rs">实习经历<span class="rs-note">（${esc(RESUME.internship.note)}）</span></div>
  <div class="org"><b>${esc(RESUME.internship.company)} · ${esc(RESUME.internship.role)}</b><span class="range">${esc(RESUME.internship.range)}</span></div>
  <p class="bg">项目背景：${esc(RESUME.internship.background)}</p>
  ${jobs}
  <div class="stack"><b>技术栈：</b>${esc(RESUME.internship.stack)}</div>

  <div class="rs">项目经历<span class="rs-note">（${esc(RESUME.project.note)}）</span></div>
  <div class="org"><b>${esc(RESUME.project.name)}</b><span class="range">${esc(RESUME.project.range)}</span></div>
  <div class="stack"><b>技术栈：</b>${esc(RESUME.project.stack)}</div>
  <p class="bg">项目背景：${esc(RESUME.project.background)}</p>
  <ul>${projs}</ul>
  <div class="result"><b>核心成果：</b>${esc(RESUME.project.result)}</div>
</div></body></html>`;
  }

  function exportPdf() {
    const html = printHtml();
    if (!window.jspdf || !window.htmlToImage) {
      // 兜底：库加载失败时退回浏览器打印
      const host = $('print-host');
      host.innerHTML = html;
      setTimeout(() => { window.print(); }, 60);
      return;
    }
    const btn = document.querySelector('#resumeview-view .page-heading button');
    if (btn) { btn.disabled = true; btn.textContent = '生成中…'; }
    // 生成期间在页面顶层显示白底简历（html-to-image 需元素真实渲染；宽 718px ≈ A4 190mm）
    const wrap = document.createElement('div');
    wrap.style.cssText = 'position:fixed;left:0;top:0;width:718px;background:#fff;z-index:9999;';
    wrap.innerHTML = html;
    document.body.appendChild(wrap);
    const done = () => {
      wrap.remove();
      if (btn) { btn.disabled = false; btn.textContent = '导出 PDF'; }
    };
    window.htmlToImage.toCanvas(wrap, { pixelRatio: 2, backgroundColor: '#ffffff', cacheBust: true })
      .then(c => {
        const pdf = new window.jspdf.jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' });
        const pageW = 210, pageH = 297, m = 12;
        const drawW = pageW - m * 2;
        const totalHmm = c.height * drawW / c.width;
        const usableH = pageH - m * 2;
        let y = 0, page = 0;
        while (y < totalHmm) {
          const sliceHmm = Math.min(usableH, totalHmm - y);
          const slicePxH = Math.max(1, Math.round(sliceHmm / totalHmm * c.height));
          const sc = document.createElement('canvas');
          sc.width = c.width; sc.height = slicePxH;
          sc.getContext('2d').drawImage(c, 0, Math.round(y / totalHmm * c.height), c.width, slicePxH, 0, 0, c.width, slicePxH);
          if (page > 0) pdf.addPage();
          pdf.addImage(sc.toDataURL('image/jpeg', 0.95), 'JPEG', m, m, drawW, sliceHmm);
          y += sliceHmm; page++;
        }
        pdf.save('优秀简历模版.pdf');
        done();
      })
      .catch(() => {
        done();
        const host = $('print-host');
        host.innerHTML = html;
        setTimeout(() => { window.print(); }, 60);
      });
  }

  /* ============ 视图 ============ */
  function renderSelfView() {
    const root = $('selfview-view');
    const heading = root.querySelector('.page-heading');
    heading.innerHTML = '';
    const wrap = el('div');
    wrap.append(el('div', 'page-overline', 'INTERVIEW PREP · SOFT SKILLS'), el('h1', undefined, '自我介绍 / 反问'));
    wrap.append(el('p', undefined, '面试两端的开口环节：先用「四段式自我介绍」把经历讲成一条线，再在反问环节用「技术面 5 问 + HR 面薪资清单」把岗位和公司摸清楚。'));
    heading.append(wrap);
    const host = $('selfview-body');
    host.replaceChildren(renderIntro(), renderTech(), renderHr());
  }

  function renderResumeView() {
    const root = $('resumeview-view');
    const heading = root.querySelector('.page-heading');
    heading.innerHTML = '';
    const wrap = el('div');
    wrap.append(el('div', 'page-overline', 'INTERVIEW PREP · RESUME TEMPLATE'), el('h1', undefined, '模版简历'));
    wrap.append(el('p', undefined, '一份「照着填就能用」的优秀简历范本：教育、技能、实习、项目四块齐全，实习经历与「机票退改签 Agent」项目一一对应。导出 PDF 后可自行修改投递。'));
    heading.append(wrap);
    const btn = el('button', 'secondary');
    btn.type = 'button';
    btn.append(icon('<path d="M12 3v12m-4-4 4 4 4-4M5 21h14"/>'), document.createTextNode('导出 PDF'));
    btn.onclick = exportPdf;
    heading.append(btn);
    const host = $('resumeview-body');
    host.replaceChildren(buildResumeView());
  }

  return { init() { renderSelfView(); renderResumeView(); } };
})();
