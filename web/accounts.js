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
})();
