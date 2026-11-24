/**
 * Hashrise 游戏开发 Skill 导航 · 站点逻辑
 *
 * 站点模式下从 ./data/catalog.json 读取；
 * 构建便携版时，构建脚本会把这段替换为内联的 catalog 常量（见 scripts/build.mjs）。
 */

import {
  searchCatalog, summarize, installationClients,
  installationCommand, installationGuide, firstPartyGuide
} from './search.mjs';

const state = {
  q: '',
  category: '全部',
  engine: '全部',
  capability: '全部',
  origin: '全部',
  sort: 'recommended'
};

const $ = (id) => document.getElementById(id);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
};
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* ---------------- 载入目录 ---------------- */

let catalog = null;

async function loadCatalog() {
  const response = await fetch('./data/catalog.json');
  if (!response.ok) throw new Error('目录请求失败');
  catalog = await response.json();
}

/* ---------------- 渲染：统计与筛选器 ---------------- */

function renderStats() {
  const s = catalog.stats || {};
  const box = $('heroStats');
  box.innerHTML = '';
  const items = [
    [`${s.total ?? catalog.skills.length}`, '个技能'],
    [`${s.first_party ?? 0}`, '个第一方（已验证）'],
    [`${s.third_party ?? 0}`, '个第三方（核实来源）'],
    [`${s.repos ?? 0}`, '个上游仓库'],
    [`${s.categories ?? 0}`, '个开发阶段'],
    [`${s.engines ?? 0}`, '个引擎维度']
  ];
  for (const [n, label] of items) {
    const sp = el('span');
    sp.innerHTML = `<b>${esc(n)}</b>${esc(label)}`;
    box.appendChild(sp);
  }
}

function chip(label, count, on, onClick, mini = false) {
  const c = el('button', `chip${mini ? ' mini' : ''}${on ? ' on' : ''}`);
  c.type = 'button';
  c.innerHTML = `${esc(label)}<span class="n">${count}</span>`;
  c.addEventListener('click', onClick);
  return c;
}

function renderChips() {
  const { skills } = catalog;

  // 引擎维度：横排大 chips
  const engines = summarize(skills, 'platforms');
  const engBox = $('engineChips');
  engBox.innerHTML = '';
  engBox.appendChild(chip('全部引擎', skills.length, state.engine === '全部',
    () => { state.engine = '全部'; sync(); }));
  for (const { name, count } of engines) {
    engBox.appendChild(chip(name, count, state.engine === name,
      () => { state.engine = state.engine === name ? '全部' : name; sync(); }));
  }

  // 分类
  const cats = summarize(skills, 'category');
  const catBox = $('catChips');
  catBox.innerHTML = '';
  catBox.appendChild(chip('全部', skills.length, state.category === '全部',
    () => { state.category = '全部'; sync(); }, true));
  for (const { name, count } of cats) {
    catBox.appendChild(chip(name, count, state.category === name,
      () => { state.category = state.category === name ? '全部' : name; sync(); }, true));
  }

  // 能力
  const caps = summarize(skills, 'capability');
  const capBox = $('capChips');
  capBox.innerHTML = '';
  capBox.appendChild(chip('全部', skills.length, state.capability === '全部',
    () => { state.capability = '全部'; sync(); }, true));
  for (const { name, count } of caps) {
    capBox.appendChild(chip(name, count, state.capability === name,
      () => { state.capability = state.capability === name ? '全部' : name; sync(); }, true));
  }

  // 来源
  const origins = summarize(skills, 'origin');
  const oBox = $('originChips');
  oBox.innerHTML = '';
  const OMAP = { 'first-party': '第一方 · 已验证', 'third-party': '第三方 · 核实来源' };
  oBox.appendChild(chip('全部', skills.length, state.origin === '全部',
    () => { state.origin = '全部'; sync(); }, true));
  for (const { name, count } of origins) {
    oBox.appendChild(chip(OMAP[name] || name, count, state.origin === name,
      () => { state.origin = state.origin === name ? '全部' : name; sync(); }, true));
  }
}

/* ---------------- 渲染：卡片 ---------------- */

function licenseBadge(s) {
  if (s.license === 'MIT' || s.license === 'Apache-2.0') return '';
  const danger = s.license === 'CC-BY-NC-4.0' || s.license === '未声明';
  return `<span class="badge ${danger ? 'badge-lic-danger' : 'badge-lic'}"
    title="${esc(s.license_note || '')}">${esc(s.license)}</span>`;
}

function card(s) {
  const n = el('button', `card${s.featured ? ' featured' : ''}`);
  n.type = 'button';

  const top = el('div', 'card-top');
  top.appendChild(el('h3', 'card-title', esc(s.title)));
  n.appendChild(top);

  n.appendChild(el('p', 'card-repo', `${s.repo} · ${s.name}`));
  n.appendChild(el('p', 'card-sum', esc(s.summary)));

  const foot = el('div', 'card-foot');
  foot.appendChild(el('span', 'tag cat', esc(s.category)));
  for (const p of s.platforms) foot.appendChild(el('span', 'tag eng', esc(p)));
  foot.appendChild(el('span', 'tag cap', esc(s.capability)));
  foot.appendChild(el('span', s.origin === 'first-party' ? 'badge badge-first' : 'badge badge-src',
    s.origin === 'first-party' ? '已验证' : '仅核实来源'));
  const lb = licenseBadge(s);
  if (lb) foot.insertAdjacentHTML('beforeend', lb);
  n.appendChild(foot);

  n.addEventListener('click', () => openDetail(s));
  return n;
}

function renderGrid() {
  const list = searchCatalog(catalog.skills, state);
  const grid = $('grid');
  grid.innerHTML = '';
  for (const s of list) grid.appendChild(card(s));

  $('empty').hidden = list.length > 0;

  const total = catalog.skills.length;
  $('resultCount').innerHTML = `显示 <b>${list.length}</b> / ${total} 个技能`;

  const parts = [];
  if (state.q) parts.push(`关键词「${state.q}」`);
  if (state.category !== '全部') parts.push(state.category);
  if (state.engine !== '全部') parts.push(state.engine);
  if (state.capability !== '全部') parts.push(state.capability);
  if (state.origin !== '全部') parts.push(state.origin === 'first-party' ? '第一方' : '第三方');
  $('activeFilter').textContent = parts.length ? `筛选：${parts.join(' · ')}` : '';

  const fp = list.filter((s) => s.origin === 'first-party').length;
  if (fp) {
    $('activeFilter').textContent += parts.length ? ` · 含 ${fp} 个第一方` : `其中 ${fp} 个为第一方技能（已验证）`;
  }
}

/* ---------------- 详情面板 ---------------- */

let detailSkill = null;

function openDetail(s) {
  detailSkill = s;
  const body = $('detailBody');
  body.innerHTML = '';

  body.appendChild(el('p', 'd-eyebrow',
    s.origin === 'first-party' ? 'Hashrise 第一方技能' : '第三方开源技能'));

  const h = el('h2', 'd-title', esc(s.title));
  h.id = 'dTitle';
  body.appendChild(h);

  body.appendChild(el('p', 'd-name', `${s.repo} · ${s.name}`));
  body.appendChild(el('p', 'd-sum', esc(s.summary)));

  const tags = el('div', 'd-tags');
  tags.appendChild(el('span', 'tag cat', esc(s.category)));
  for (const p of s.platforms) tags.appendChild(el('span', 'tag eng', esc(p)));
  tags.appendChild(el('span', 'tag cap', esc(s.capability)));
  tags.appendChild(el('span', s.origin === 'first-party' ? 'badge badge-first' : 'badge badge-src',
    s.origin === 'first-party' ? '已验证' : '仅核实来源'));
  if (s.license !== 'MIT' && s.license !== 'Apache-2.0') {
    tags.appendChild(el('span', s.license === 'MIT' ? 'badge badge-src' : 'badge badge-lic', esc(s.license)));
  }
  body.appendChild(tags);

  // 关键信息
  const kv = el('dl', 'd-kv');
  const rows = [
    ['能力形态', esc(s.capability)],
    ['许可证', esc(s.license) + (s.license_url ? ` · <a href="${esc(s.license_url)}" target="_blank" rel="noopener noreferrer">查看</a>` : '')],
    ['核对日期', esc(s.checked_at)],
    ['文件哈希', `<span class="mono">${esc((s.content_sha256 || '').slice(0, 24))}…</span>`],
    ['来源 commit', `<span class="mono">${esc((s.source_commit || '').slice(0, 12))}…</span>`],
    ['文件路径', `<span class="mono">${esc(s.path)}</span>`]
  ];
  for (const [k, v] of rows) {
    kv.appendChild(el('dt', null, k));
    kv.appendChild(el('dd', k === '文件哈希' || k === '来源 commit' || k === '文件路径' ? 'mono' : null, v));
  }
  const sec1 = el('div', 'd-sec');
  sec1.appendChild(el('h3', null, '关键信息'));
  sec1.appendChild(kv);
  body.appendChild(sec1);

  // 限制说明
  if (s.limitations) {
    const sec2 = el('div', 'd-sec');
    sec2.appendChild(el('h3', null, '能力边界与限制'));
    sec2.appendChild(el('div', 'd-note', esc(s.limitations)));
    body.appendChild(sec2);
  }
  if (s.license_note) {
    const sec2b = el('div', 'd-sec');
    sec2b.appendChild(el('h3', null, '许可证提示'));
    sec2b.appendChild(el('div', 'd-note d-warn', esc(s.license_note)));
    body.appendChild(sec2b);
  }
  if (s.evidence) {
    const sec2c = el('div', 'd-sec');
    sec2c.appendChild(el('h3', null, '验证证据'));
    sec2c.appendChild(el('div', 'd-note', esc(s.evidence)));
    body.appendChild(sec2c);
  }

  // 安装
  body.appendChild(buildInstall(s));

  // 链接
  const sec4 = el('div', 'd-sec');
  sec4.appendChild(el('h3', null, '来源'));
  const links = el('div', 'd-links');
  if (s.source_url) {
    links.innerHTML += `<a class="btn btn-ghost" href="${esc(s.source_url)}" target="_blank" rel="noopener noreferrer">查看源文件 ↗</a>`;
  }
  if (s.repo_url) {
    links.innerHTML += `<a class="btn btn-ghost" href="${esc(s.repo_url)}" target="_blank" rel="noopener noreferrer">上游仓库 ↗</a>`;
  }
  sec4.appendChild(links);
  body.appendChild(sec4);

  $('detail').hidden = false;
  document.body.style.overflow = 'hidden';
}

function buildInstall(s) {
  const sec = el('div', 'd-sec');
  sec.appendChild(el('h3', null, '安装到你的 AI 工具'));

  const wrap = el('div', 'd-install');

  const sel = el('select');
  for (const c of installationClients) {
    const o = el('option', null, c.label);
    o.value = c.id;
    sel.appendChild(o);
  }
  sel.value = 'workbuddy';
  wrap.appendChild(sel);

  const out = el('div');

  const render = () => {
    out.innerHTML = '';
    const agent = sel.value;
    let guide;
    try {
      guide = s.origin === 'first-party' ? firstPartyGuide(s) : installationGuide(s, agent);
    } catch (e) {
      out.appendChild(el('div', 'd-note d-warn', `该客户端的安装方式无法自动生成：${esc(e.message)}`));
      return;
    }
    if (guide.command) {
      const code = el('div', 'code', esc(guide.command));
      const btn = el('button', 'copy-btn', '复制');
      btn.type = 'button';
      btn.addEventListener('click', () => {
        navigator.clipboard?.writeText(guide.command).then(() => toast('已复制安装命令'))
          .catch(() => toast('复制失败，请手动选中'));
      });
      code.appendChild(btn);
      out.appendChild(code);
    }
    const ol = el('ol', 'd-steps');
    for (const st of guide.steps) ol.appendChild(el('li', null, esc(st)));
    out.appendChild(ol);
    if (guide.note) out.appendChild(el('div', 'd-note', esc(guide.note)));
  };

  sel.addEventListener('change', render);
  render();
  wrap.appendChild(out);
  sec.appendChild(wrap);
  return sec;
}

function closeDetail() {
  $('detail').hidden = true;
  document.body.style.overflow = '';
  detailSkill = null;
}

/* ---------------- Toast ---------------- */

let toastTimer = null;
function toast(msg) {
  const t = $('toast');
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 2000);
}

/* ---------------- 状态同步 ---------------- */

function readHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  state.q = h.get('q') || '';
  state.category = h.get('cat') || '全部';
  state.engine = h.get('eng') || '全部';
  state.capability = h.get('cap') || '全部';
  state.origin = h.get('org') || '全部';
  state.sort = h.get('sort') || 'recommended';
}

function writeHash() {
  const p = new URLSearchParams();
  if (state.q) p.set('q', state.q);
  if (state.category !== '全部') p.set('cat', state.category);
  if (state.engine !== '全部') p.set('eng', state.engine);
  if (state.capability !== '全部') p.set('cap', state.capability);
  if (state.origin !== '全部') p.set('org', state.origin);
  if (state.sort !== 'recommended') p.set('sort', state.sort);
  const s = p.toString();
  history.replaceState(null, '', s ? `#${s}` : location.pathname);
}

function sync() {
  $('q').value = state.q;
  $('clearQ').hidden = !state.q;
  $('sortSel').value = state.sort;
  renderChips();
  renderGrid();
  writeHash();
}

/* ---------------- 启动 ---------------- */

async function main() {
  try {
    await loadCatalog();
  } catch (e) {
    document.querySelector('.main').innerHTML =
      `<div class="empty"><p class="empty-title">目录加载失败</p>
       <p class="empty-hint">${esc(e.message)}。请确认已执行构建，或使用打包后的单文件页面。</p></div>`;
    return;
  }

  renderStats();
  $('footerMeta').textContent =
    `目录版本 ${catalog.version} · 核对日期 ${catalog.updated_at} · ` +
    `收录 ${catalog.skills.length} 条 / ${catalog.stats.repos} 个上游仓库 · ` +
    `${catalog.coverage}`;

  readHash();
  sync();

  const q = $('q');
  let timer = null;
  q.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => { state.q = q.value; sync(); }, 160);
  });

  $('clearQ').addEventListener('click', () => { state.q = ''; sync(); q.focus(); });

  $('sortSel').addEventListener('change', (e) => { state.sort = e.target.value; sync(); });

  $('resetBtn').addEventListener('click', () => {
    state.q = ''; state.category = '全部'; state.engine = '全部';
    state.capability = '全部'; state.origin = '全部'; state.sort = 'recommended';
    sync();
  });

  document.addEventListener('click', (e) => {
    if (e.target.hasAttribute('data-close')) closeDetail();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !$('detail').hidden) closeDetail();
  });

  window.addEventListener('hashchange', () => { readHash(); sync(); });
}

main();
