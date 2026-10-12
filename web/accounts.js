/* 子账号体系：批量创建 / 草稿 / 导出（纯前端，不可逆哈希，无回溯凭证）。
 *
 * 契约（与 tests/test_account_system.py 完全一致）：
 * - hash 格式：sha256$<salt>$<hex>，hex = SHA-256(salt + ':' + account + ':' + password)
 * - salt：16 字节随机 hex（32 hex 字符）
 * - 过期：expiresAt = createdAt + 60 天
 * - 数据文件：web/sub-accounts.json，字段白名单 version/algorithm/accounts[]
 *   每项仅 id/note/createdAt/expiresAt/hash，禁止明文/密文/密钥
 * - 系统内无可回溯凭证：明文只在创建时一次性展示
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'agent_tutorial_draft_accounts';
  const MASTER_ACCOUNT = 'chaoyang';
  const EXPIRY_DAYS = 60;
  // 排除易混淆字符 0O1lI
  const ACCOUNT_CHARS = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789';
  const PASSWORD_CHARS = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789!@#$%^&*';

  function randChars(len, charset) {
    const out = [];
    const buf = new Uint32Array(len);
    crypto.getRandomValues(buf);
    for (let i = 0; i < len; i++) out.push(charset[buf[i] % charset.length]);
    return out.join('');
  }

  function saltHex() {
    const buf = new Uint8Array(16);
    crypto.getRandomValues(buf);
    return Array.from(buf, b => b.toString(16).padStart(2, '0')).join('');
  }

  async function sha256Hex(str) {
    const data = new TextEncoder().encode(str);
    const digest = await crypto.subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
  }

  async function hashOf(account, password, salt) {
    return 'sha256$' + salt + '$' + await sha256Hex(salt + ':' + account + ':' + password);
  }

  function now() { return Date.now(); }

  function expiresAtOf(createdAtMs) {
    return createdAtMs + EXPIRY_DAYS * 86400000;
  }

  function pad3(i) { return String(i).padStart(3, '0'); }

  function dateTag(ms) {
    const d = new Date(ms);
    return d.getFullYear() + String(d.getMonth() + 1).padStart(2, '0') + String(d.getDate()).padStart(2, '0');
  }

  function generateId(i) {
    return 'stu-' + dateTag(now()) + '-' + pad3(i);
  }

  /* 批量生成 1~10 个账号：返回明文对象数组（仅本次展示用）。 */
  async function generateBatch(n) {
    n = Math.max(1, Math.min(10, Math.floor(n) || 1));
    const out = [];
    for (let i = 1; i <= n; i++) {
      let account;
      do {
        account = randChars(8, ACCOUNT_CHARS);
      } while (account === MASTER_ACCOUNT || account.toLowerCase() === MASTER_ACCOUNT);
      const password = randChars(12, PASSWORD_CHARS);
      const createdAt = now();
      const salt = saltHex();
      const h = await hashOf(account, password, salt);
      out.push({
        id: generateId(i),
        note: '',
        account, password,
        createdAt, expiresAt: expiresAtOf(createdAt),
        hash: h
      });
    }
    return out;
  }

  /* 草稿区（localStorage）：只存无明文字段的账号条目。 */
  function loadDraft() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
    catch (e) { return []; }
  }

  function saveDraft(list) {
    const stripped = list.map(a => ({
      id: a.id, note: a.note || '', createdAt: a.createdAt, expiresAt: a.expiresAt, hash: a.hash
    }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stripped));
    return stripped;
  }

  function clearDraft() {
    localStorage.removeItem(STORAGE_KEY);
  }

  /* 合并：按 id 去重，保留全部旧账号（与 tests/test_account_system.py::merge_with_published 同规则）。 */
  function mergeWithPublished(draft, publishedAccounts) {
    const byId = {};
    (publishedAccounts || []).forEach(a => { byId[a.id] = a; });
    draft.forEach(a => { byId[a.id] = a; });
    return Object.keys(byId).sort().map(k => byId[k]);
  }

  /* 导出：合并已发布文件 + 草稿，仅含无明文字段。 */
  async function buildExport(draftAccounts) {
    let published = [];
    try {
      const r = await fetch('static/sub-accounts.json', {cache: 'no-store'});
      if (r.ok) {
        const d = await r.json();
        published = d.accounts || [];
      }
    } catch (e) { /* 无已发布文件则仅导出草稿 */ }
    const merged = mergeWithPublished(draftAccounts, published);
    return {
      version: 2,
      algorithm: 'sha256$salt$hash(salt:account:password)',
      accounts: merged.map(a => ({
        id: a.id, note: a.note || '', createdAt: a.createdAt, expiresAt: a.expiresAt, hash: a.hash
      }))
    };
  }

  function downloadExport(jsonObj) {
    const a = document.createElement('a');
    const url = URL.createObjectURL(new Blob([JSON.stringify(jsonObj, null, 2)], {type: 'application/json'}));
    a.href = url;
    a.download = 'sub-accounts.json';
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  /* 登录校验（与 tests/test_account_system.py::verify 同规则）：主账号优先，子账号哈希 + 过期。 */
  function expired(createdAtMs, nowMs) { return nowMs - createdAtMs >= EXPIRY_DAYS * 86400000; }

  window.Accounts = {
    generateBatch, hashOf, now, expiresAtOf, loadDraft, saveDraft, clearDraft,
    mergeWithPublished, buildExport, downloadExport, expired,
    EXPIRY_DAYS, MASTER_ACCOUNT
  };

  /* —— 创建子账号面板 UI 绑定 —— */
  function el(id) { return document.getElementById(id); }

  function fmtTime(ms) {
    const d = new Date(ms);
    const p = n => String(n).padStart(2, '0');
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
  }

  function renderDraft() {
    const host = el('draft-list');
    const draft = window.Accounts.loadDraft();
    if (!draft.length) {
      host.innerHTML = '<p class="small muted">暂无草稿。生成后账号会进入草稿区，导出时一并写入数据文件。</p>';
      return;
    }
    host.replaceChildren();
    draft.forEach(a => {
      const row = document.createElement('div');
      row.className = 'draft-row';
      row.innerHTML = '<span class="draft-id">' + a.id + '</span><span class="small muted">创建 ' + fmtTime(a.createdAt) + ' · 过期 ' + fmtTime(a.expiresAt) + '</span>';
      host.append(row);
    });
  }

  function copyText(text) {
    return navigator.clipboard.writeText(text).then(() => true).catch(() => false);
  }

  async function onGenerate() {
    const n = Math.max(1, Math.min(10, parseInt(el('batch-count').value, 10) || 1));
    const batch = await window.Accounts.generateBatch(n);
    // 一次性明文展示
    const rows = el('cred-rows');
    rows.replaceChildren();
    batch.forEach(b => {
      const row = document.createElement('div');
      row.className = 'cred-line';
      const code = document.createElement('code');
      code.textContent = b.account + '　' + b.password;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'secondary';
      btn.textContent = '复制';
      btn.onclick = () => { copyText(b.account + ' ' + b.password); btn.textContent = '已复制'; setTimeout(() => { btn.textContent = '复制'; }, 1500); };
      row.append(code, btn);
      rows.append(row);
    });
    el('batch-result').hidden = false;
    // 写入草稿（仅哈希等无明文字段）
    window.Accounts.saveDraft(batch);
    renderDraft();
  }

  function initCreatePanel() {
    const btn = el('create-account-btn');
    const panel = el('account-panel');
    if (!btn || !panel) return;
    btn.onclick = () => { renderDraft(); panel.showModal(); };
    el('account-panel-close').onclick = () => panel.close();
    el('batch-minus').onclick = () => { const v = parseInt(el('batch-count').value, 10) || 1; el('batch-count').value = Math.max(1, v - 1); };
    el('batch-plus').onclick = () => { const v = parseInt(el('batch-count').value, 10) || 1; el('batch-count').value = Math.min(10, v + 1); };
    el('gen-batch-btn').onclick = onGenerate;
    el('copy-all-btn').onclick = () => {
      const texts = Array.from(el('cred-rows').querySelectorAll('code')).map(c => c.textContent.replace(/\u3000/g, ' '));
      copyText(texts.join('\n')).then(ok => {
        el('copy-all-btn').textContent = ok ? '已复制全部' : '复制失败';
        setTimeout(() => { el('copy-all-btn').textContent = '一键复制全部'; }, 1500);
      });
    };
    el('draft-clear-btn').onclick = () => { window.Accounts.clearDraft(); renderDraft(); };
    el('export-accounts-btn').onclick = async () => {
      const out = await window.Accounts.buildExport(window.Accounts.loadDraft());
      window.Accounts.downloadExport(out);
      el('export-status').textContent = '已导出 ' + out.accounts.length + ' 个账号（仅哈希）。请放入 web/ 目录 push 部署。';
    };
    // 确认提交 · 自动部署：本地后端模式由 app.js 控制可见性（仅主账号）
    const pubBtn = el('publish-accounts-btn');
    if (pubBtn) {
      pubBtn.onclick = async () => {
        const draft = window.Accounts.loadDraft();
        if (!draft.length) { el('export-status').textContent = '请先生成账号，再点击确认提交。'; return; }
        if (!confirm('确认提交 ' + draft.length + ' 个新账号并自动部署到 GitHub 线上？\n提交后立即生效、不可撤销。')) return;
        pubBtn.disabled = true;
        pubBtn.textContent = '提交部署中…';
        try {
          const r = await fetch('static/sub-accounts.json', {cache: 'no-store'});
          const published = r.ok ? await r.json() : {version: 2, algorithm: 'sha256$salt$hash(salt:account:password)', accounts: []};
          const merged = window.Accounts.mergeWithPublished(draft, published.accounts || []);
          const res = await fetch('/api/accounts/publish', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({version: 2, algorithm: 'sha256$salt$hash(salt:account:password)', accounts: merged})
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || ('HTTP ' + res.status));
          window.Accounts.clearDraft();
          renderDraft();
          el('export-status').textContent = data.no_changes
            ? '已是最新（无变更）。当前线上共 ' + data.count + ' 个账号。'
            : '部署成功！commit ' + data.commit + '，线上共 ' + data.count + ' 个账号。';
        } catch (err) {
          el('export-status').textContent = '提交失败：' + (err.message || err) + '（数据已写入本地 web/sub-accounts.json，可稍后重试或手动 push）';
        } finally {
          pubBtn.disabled = false;
          pubBtn.textContent = '确认提交 · 自动部署';
        }
      };
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCreatePanel);
  } else {
    initCreatePanel();
  }
})();
