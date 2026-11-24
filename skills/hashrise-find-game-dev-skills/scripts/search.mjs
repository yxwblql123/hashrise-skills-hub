#!/usr/bin/env node
/**
 * Hashrise 游戏开发 Skill 导航 · 检索命令
 *
 * 用法：
 *   node scripts/search.mjs --query "godot 场景架构"
 *   node scripts/search.mjs --category "概念与策划" --engine "Godot"
 *   node scripts/search.mjs --query "steam 商店页" --agent workbuddy
 *   node scripts/search.mjs --query "CI 构建" --offline
 *
 * 输出为 JSON：{ welcome, catalog, total_matches, results, update }
 */
import { readFileSync, existsSync, writeFileSync, mkdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

import {
  searchCatalog, installationCommand, installationGuide, firstPartyGuide
} from './search-core.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = resolve(HERE, '..');

/* ---------------- 参数解析 ---------------- */

function parseArgs(argv) {
  const out = {
    query: '', category: '全部', engine: '全部', capability: '全部',
    origin: '全部', sort: 'recommended', limit: 5, agent: 'codex',
    catalog: null, offline: false, showWeb: false, welcome: true, checkUpdates: false
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    const next = () => argv[++i];
    switch (a) {
      case '--query': case '-q': out.query = next(); break;
      case '--category': case '-c': out.category = next(); break;
      case '--engine': case '-e': out.engine = next(); break;
      case '--capability': out.capability = next(); break;
      case '--origin': out.origin = next(); break;
      case '--sort': out.sort = next(); break;
      case '--limit': case '-l': out.limit = parseInt(next(), 10) || 5; break;
      case '--agent': case '-a': out.agent = next(); break;
      case '--catalog': out.catalog = next(); break;
      case '--offline': out.offline = true; break;
      case '--no-welcome': out.welcome = false; break;
      case '--show-web': out.showWeb = true; break;
      case '--check-updates': out.checkUpdates = true; break;
      case '--help': case '-h': out.help = true; break;
      default: break;
    }
  }
  return out;
}

const args = parseArgs(process.argv);

if (args.help) {
  console.log(`Hashrise 游戏开发 Skill 导航 · 检索

  --query, -q <文本>      关键词
  --category, -c <分类>   概念与策划 / 引擎与实现 / 美术与音频 / 商业化与发行 / 工程与交付 / 质量与运营 / 平台与后端
  --engine, -e <引擎>     Godot / Unity / Unreal / Web / Blender / Steam / 通用
  --capability <能力>     方法指导 / 代码生成 / 自动化 / 平台接入
  --origin <来源>         first-party / third-party
  --sort <方式>           recommended / first-party / updated / name
  --limit, -l <数量>      返回条数，默认 5
  --agent, -a <客户端>    codex / claude-code / cursor / codebuddy / trae / workbuddy / other
  --catalog <路径>        指定外部目录 JSON（不联网、不覆盖缓存）
  --offline               完全离线，不联网检查更新
  --no-welcome            不输出欢迎语
  --show-web              再次输出本地网页链接
`);
  process.exit(0);
}

/* ---------------- 目录载入 + 完整性校验 ---------------- */

function loadCatalog() {
  const path = args.catalog
    ? resolve(args.catalog)
    : join(SKILL_ROOT, 'references', 'catalog.json');

  if (!existsSync(path)) {
    console.error(`目录文件不存在：${path}`);
    process.exit(2);
  }

  const raw = readFileSync(path);
  const sha256 = createHash('sha256').update(raw).digest('hex');

  // 完整性校验：与 release.json 记录的比对；不一致则明确告知而不是静默使用
  const releasePath = join(SKILL_ROOT, 'references', 'release.json');
  let integrity = { checked: false };
  if (existsSync(releasePath) && !args.catalog) {
    try {
      const rel = JSON.parse(readFileSync(releasePath, 'utf8'));
      const expected = rel.catalog?.sha256;
      if (expected) {
        integrity = {
          checked: true,
          ok: expected === sha256,
          expected,
          actual: sha256,
          note: expected === sha256
            ? '目录哈希与发布记录一致'
            : '目录哈希与发布记录不一致，目录可能已被修改或换行符被转换'
        };
      }
    } catch { /* release.json 解析失败不阻断检索 */ }
  }

  const catalog = JSON.parse(raw.toString('utf8'));
  return { catalog, sha256, integrity, path };
}

/* ---------------- 更新检查 ---------------- */

const CACHE_DIR = process.env.HASHRISE_SKILLS_CACHE_DIR
  || join(homedir(), '.cache', 'hashrise-find-game-dev-skills');

function checkUpdates(localCatalog) {
  if (args.offline) {
    return { status: 'offline', message: '离线模式，使用本机已有目录' };
  }
  if (args.catalog) {
    return { status: 'skipped', message: '指定了外部目录，未联网检查更新' };
  }
  const stampPath = join(CACHE_DIR, 'last-check.json');
  const now = Date.now();
  const DAY = 24 * 60 * 60 * 1000;

  let last = 0;
  if (existsSync(stampPath)) {
    try { last = JSON.parse(readFileSync(stampPath, 'utf8')).at || 0; } catch { /* ignore */ }
  }
  if (!args.checkUpdates && now - last < DAY) {
    return { status: 'cached', message: '24 小时内已检查过更新' };
  }

  try {
    mkdirSync(CACHE_DIR, { recursive: true });
    writeFileSync(stampPath, JSON.stringify({ at: now }));
  } catch { /* 缓存不可写不阻断 */ }

  // 目录随仓库发布，客户端不做自动拉取；这里只如实说明状态
  return {
    status: 'checked',
    message: '目录随技能包一起分发，升级技能即更新目录',
    catalog_updated_at: localCatalog.updated_at
  };
}

/* ---------------- 欢迎语 ---------------- */

function buildWelcome(catalog) {
  const htmlPath = join(SKILL_ROOT, 'assets', 'hashrise-skills.html');
  const statePath = join(CACHE_DIR, 'welcome.json');
  let shown = false;
  try {
    if (existsSync(statePath)) {
      const st = JSON.parse(readFileSync(statePath, 'utf8'));
      shown = st.catalog === catalog.updated_at;
    }
  } catch { /* ignore */ }

  if (!shown) {
    try {
      mkdirSync(CACHE_DIR, { recursive: true });
      writeFileSync(statePath, JSON.stringify({ catalog: catalog.updated_at, at: Date.now() }));
    } catch { /* ignore */ }
  }

  return {
    show: !shown,
    message: [
      '欢迎使用 Hashrise 游戏开发 Skill 导航！',
      '',
      '独立游戏开发的 AI 技能索引：GDD 起草、Godot 场景与架构、Steam 商店页、CI 构建，以及 180+ 个已核实的开源技能。',
      '',
      '第一方技能来自《算力崛起 Hashrise》的真实工程实践，已在项目内验证。'
    ].join('\n'),
    url: `file://${htmlPath.replace(/\\/g, '/')}`,
    online_url: 'https://hashrise.devs.li/',
    path: htmlPath
  };
}

/* ---------------- 主流程 ---------------- */

const { catalog, sha256, integrity, path: catalogPath } = loadCatalog();

const results = searchCatalog(catalog.skills, {
  q: args.query,
  category: args.category,
  engine: args.engine,
  capability: args.capability,
  origin: args.origin,
  sort: args.sort
}).slice(0, Math.max(1, args.limit));

const enriched = results.map((s) => {
  let guide;
  let installCommand = null;
  try {
    if (s.origin === 'first-party') {
      guide = firstPartyGuide(s);
    } else {
      guide = installationGuide(s, args.agent);
      installCommand = installationCommand(s, args.agent);
    }
  } catch (e) {
    guide = { error: e.message };
  }
  return {
    ...s,
    install_command: installCommand,
    installation_guide: guide
  };
});

const out = {
  welcome: args.welcome ? buildWelcome(catalog) : { show: false },
  catalog: {
    updated_at: catalog.updated_at,
    total: catalog.skills.length,
    first_party: catalog.stats?.first_party ?? 0,
    third_party: catalog.stats?.third_party ?? 0,
    sha256,
    path: catalogPath,
    integrity
  },
  query: args.query || null,
  filters: {
    category: args.category, engine: args.engine,
    capability: args.capability, origin: args.origin, sort: args.sort
  },
  total_matches: searchCatalog(catalog.skills, {
    q: args.query, category: args.category, engine: args.engine,
    capability: args.capability, origin: args.origin, sort: args.sort
  }).length,
  results: enriched,
  update: checkUpdates(catalog),
  coverage: catalog.coverage
};

if (args.showWeb) {
  out.web = out.welcome.url;
}

console.log(JSON.stringify(out, null, 2));
