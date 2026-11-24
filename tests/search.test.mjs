import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  searchCatalog, summarize, inferCategory, inferEngines,
  installationCommand, installationGuide, firstPartyGuide
} from '../src/search.mjs';

const catalog = JSON.parse(readFileSync(new URL('../data/catalog.json', import.meta.url)));
const skills = catalog.skills;

test('目录非空且 id 唯一', () => {
  assert.ok(skills.length > 0);
  assert.equal(new Set(skills.map((s) => s.id)).size, skills.length);
});

test('分类别名能把中文口语映射到目录分类', () => {
  assert.ok(inferCategory('写 gdd').includes('概念与策划'));
  assert.ok(inferCategory('steam 商店页').includes('商业化与发行'));
  assert.ok(inferCategory('数值平衡').includes('概念与策划'));
  assert.ok(inferCategory('ci 构建').includes('工程与交付'));
});

test('引擎别名能识别引擎', () => {
  assert.ok(inferEngines('godot 场景').includes('Godot'));
  assert.ok(inferEngines('steamworks 商店页').includes('Steam'));
  assert.ok(inferEngines('blender 建模').includes('Blender'));
});

test('按分类筛选返回该分类的全部条目', () => {
  for (const cat of [...new Set(skills.map((s) => s.category))]) {
    const r = searchCatalog(skills, { category: cat });
    assert.ok(r.length > 0, `${cat} 应有结果`);
    assert.ok(r.every((s) => s.category === cat));
  }
});

test('按引擎筛选同时包含通用条目', () => {
  const r = searchCatalog(skills, { engine: 'Godot' });
  assert.ok(r.every((s) => s.platforms.includes('Godot')));
  assert.ok(r.some((s) => s.platforms.includes('通用')));
});

test('按来源筛选：第一方条目全部 tested 且有证据', () => {
  const r = searchCatalog(skills, { origin: 'first-party' });
  assert.ok(r.length > 0);
  for (const s of r) {
    assert.equal(s.origin, 'first-party');
    assert.equal(s.tested, true);
    assert.ok(s.evidence);
  }
});

test('第三方条目一律 tested=false', () => {
  for (const s of skills.filter((x) => x.origin === 'third-party')) {
    assert.equal(s.tested, false, s.id);
  }
});

test('关键词搜索能命中标题或摘要', () => {
  const r = searchCatalog(skills, { q: '离线收益' });
  assert.ok(r.length > 0);
  assert.ok(r.some((s) => /离线/.test(s.title + s.summary)));
});

test('无匹配时返回空数组而不是全部', () => {
  const r = searchCatalog(skills, { q: 'zzzz不存在的关键词zzzz' });
  assert.equal(r.length, 0);
});

test('推荐排序把第一方与 featured 排前面', () => {
  const r = searchCatalog(skills, {});
  assert.equal(r[0].origin, 'first-party');
});

test('first-party 排序第一方全在前', () => {
  const r = searchCatalog(skills, { sort: 'first-party' });
  const firstIdx = r.findIndex((s) => s.origin === 'first-party');
  const lastIdx = r.map((s) => s.origin).lastIndexOf('first-party');
  assert.ok(firstIdx >= 0);
  assert.equal(firstIdx, 0);
  // 第一方全部排在第三方之前
  const thirdIdx = r.findIndex((s) => s.origin === 'third-party');
  if (thirdIdx >= 0) assert.ok(lastIdx < thirdIdx);
});

test('summarize 按维度计数且降序', () => {
  const cats = summarize(skills, 'category');
  assert.equal(cats.reduce((a, b) => a + b.count, 0), skills.length);
  for (let i = 1; i < cats.length; i++) assert.ok(cats[i - 1].count >= cats[i].count);
});

test('安装命令生成合法 npx 调用', () => {
  const s = skills.find((x) => x.origin === 'third-party');
  const cmd = installationCommand(s, 'codex');
  assert.match(cmd, /^npx skills add .+ --skill .+ -a codex$/);
});

test('WorkBuddy 返回导入指引而非命令', () => {
  const s = skills.find((x) => x.origin === 'third-party');
  const guide = installationGuide(s, 'workbuddy');
  assert.equal(guide.command, null);
  assert.equal(guide.mode, 'import');
  assert.ok(guide.steps.length >= 2);
});

test('第一方技能给出仓库克隆式安装指引', () => {
  const s = skills.find((x) => x.origin === 'first-party');
  const guide = firstPartyGuide(s);
  assert.equal(guide.command, null);
  assert.equal(guide.tested, true);
  assert.ok(guide.steps.length >= 3);
});

test('非宽松许可证条目都带 license_note', () => {
  for (const s of skills) {
    if (!['MIT', 'Apache-2.0'].includes(s.license)) {
      assert.ok(s.license_note, `${s.id} 缺少 license_note`);
    }
  }
});
