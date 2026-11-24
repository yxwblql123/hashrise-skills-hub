/**
 * 构建静态站点 + 可导入的导航 Skill 包。
 *
 * 产物：
 *   dist/index.html                 站点（需 dist/data/catalog.json）
 *   dist/preview.html               便携单文件版（目录/CSS/JS/图标全部内联）
 *   dist/llms.txt                   机器可读说明
 *   dist/downloads/*.zip            导航 Skill 包 / 完整源码包
 *   skills/hashrise-find-game-dev-skills/assets/hashrise-skills.html  安装包内的单文件页面
 */
import { mkdir, cp, writeFile, readFile, rm } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import path from 'node:path';

const root = fileURLToPath(new URL('..', import.meta.url));
process.chdir(root);

const SKILL = 'skills/hashrise-find-game-dev-skills';
const CATALOG = 'data/catalog.json';

await mkdir(`${SKILL}/references`, { recursive: true });
await mkdir(`${SKILL}/scripts`, { recursive: true });
await mkdir(`${SKILL}/assets`, { recursive: true });

/* ---------- 1. 目录完整性自检（构建前） ---------- */

const catalogBytes = await readFile(CATALOG);
const catalogHash = createHash('sha256').update(catalogBytes).digest('hex');
const catalog = JSON.parse(catalogBytes.toString('utf8'));

if (catalogBytes.includes(0x0d)) {
  console.error('✗ catalog.json 含 CRLF 换行，会破坏内容哈希。');
  console.error('  修复：git config core.autocrlf false && git checkout HEAD -- data/catalog.json');
  process.exit(1);
}
if (!catalog.skills?.length) {
  console.error('✗ catalog.skills 为空');
  process.exit(1);
}
console.log(`目录校验通过：${catalog.skills.length} 条，sha256 ${catalogHash.slice(0, 16)}…`);

await cp(CATALOG, `${SKILL}/references/catalog.json`);
await cp('src/search.mjs', `${SKILL}/scripts/search-core.mjs`);

/* ---------- 2. 发布元信息 ---------- */

const version = '0.1.0';
await writeFile(`${SKILL}/version.json`, JSON.stringify({
  version, updated_at: catalog.updated_at, catalog_sha256: catalogHash
}, null, 1) + '\n');

await writeFile(`${SKILL}/references/release.json`, JSON.stringify({
  version,
  released_at: catalog.updated_at,
  catalog: { updated_at: catalog.updated_at, skills: catalog.skills.length, sha256: catalogHash },
  download: 'hashrise-skills-hub/releases',
  notes: '首个版本：收录 8 个第一方技能与 181 个已核实的第三方游戏开发 Skill。'
}, null, 1) + '\n');

await writeFile(`${SKILL}/references/website.json`, JSON.stringify({
  name: 'Hashrise 游戏开发 Skill 导航',
  title: '独立游戏开发 AI 技能索引',
  repo: 'hashrise-studio/hashrise-skills-hub',
  homepage: 'https://github.com/hashrise-studio/hashrise-skills-hub',
  stats: catalog.stats,
  facets: catalog.facets,
  coverage: catalog.coverage
}, null, 1) + '\n');

/* ---------- 3. 站点 ---------- */

await rm('dist', { recursive: true, force: true });
await mkdir('dist/data', { recursive: true });
await mkdir('dist/downloads', { recursive: true });
await cp('src', 'dist', { recursive: true });
await cp(CATALOG, 'dist/data/catalog.json');

await writeFile('dist/llms.txt',
`# Hashrise 游戏开发 Skill 导航

机器可读目录：/data/catalog.json
导航技能下载：/downloads/hashrise-find-game-dev-skills.zip
目录条目含来源 commit 与内容 sha256，可逐条核实。
第一方技能 tested=true，第三方技能 tested=false（仅核实来源，不等于业务实测）。
目录是精选快照，并非全网索引。
`);

/* ---------- 4. 便携单文件版 ---------- */

const html = await readFile('src/index.html', 'utf8');
const css = (await readFile('src/style.css', 'utf8'))
  .replace(/^@import[ \t]+url\([^\r\n]*\);[ \t]*(?:\r?\n|$)/gm, '');
const favicon = await readFile('src/favicon.svg');
const searchCore = (await readFile('src/search.mjs', 'utf8')).replace(/^export /gm, '');
let app = (await readFile('src/app.mjs', 'utf8'))
  .replace(/^import[\s\S]*?from '\.\/search\.mjs';\n/m, '')
  .replace(
    "const response = await fetch('./data/catalog.json');\n  if (!response.ok) throw new Error('目录请求失败');\n  catalog = await response.json();",
    'catalog = /* HASHRISE_CATALOG_START */' +
    JSON.stringify(catalog).replace(/</g, '\\u003c') +
    '/* HASHRISE_CATALOG_END */;'
  );

if (!app.includes('HASHRISE_CATALOG_START')) {
  console.error('✗ 未能内联目录（app.mjs 的 fetch 片段与构建脚本不匹配）');
  process.exit(1);
}

const portable = html
  .replace('<link rel="stylesheet" href="./style.css">',
    () => '<style>' + css + '</style>')
  .replace('href="./favicon.svg"',
    () => 'href="data:image/svg+xml;base64,' + favicon.toString('base64') + '"')
  .replace('<script type="module" src="./app.mjs"></script>', '')
  .replace('</body>', () =>
    '<script type="module">' + searchCore + '\n' + app + '</script></body>');

await writeFile('dist/preview.html', portable);

/* ---------- 5. 安装包内的单文件页面 ---------- */

const skillHTML = portable
  .replaceAll('href="./downloads/hashrise-find-game-dev-skills.zip" download',
    'href="https://github.com/hashrise-studio/hashrise-skills-hub/tree/main/skills/hashrise-find-game-dev-skills" target="_blank" rel="noopener noreferrer"')
  .replaceAll('href="./downloads/hashrise-skills-hub-source.zip" download',
    'href="https://github.com/hashrise-studio/hashrise-skills-hub" target="_blank" rel="noopener noreferrer"');

await writeFile(`${SKILL}/assets/hashrise-skills.html`, skillHTML);

/* ---------- 6. 打包 ---------- */

execFileSync('python', ['-c', `
import pathlib, zipfile
r = pathlib.Path('.')
def add(zf, files, base):
    for f in files:
        if f.is_file() and '__pycache__' not in f.parts:
            zf.write(f, pathlib.Path(base) / f.relative_to(r))

with zipfile.ZipFile('dist/downloads/hashrise-find-game-dev-skills.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    add(z, sorted((r/'skills/hashrise-find-game-dev-skills').rglob('*')), 'skills')

with zipfile.ZipFile('dist/downloads/hashrise-skills-hub-source.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for b in ['src', 'data', 'scripts', 'skills', 'tests', 'docs', '.github',
              'README.md', 'CONTRIBUTING.md', 'AGENTS.md', 'LICENSE',
              'package.json', '.gitignore']:
        p = r / b
        if not p.exists():
            continue
        add(z, [p] if p.is_file() else sorted(p.rglob('*')), 'hashrise-skills-hub')
`], { stdio: 'inherit' });

console.log(`构建完成：${catalog.skills.length} 条目录 · 站点 + 便携页 + 技能 ZIP + 源码 ZIP`);
console.log(`目录 sha256: ${catalogHash}`);
