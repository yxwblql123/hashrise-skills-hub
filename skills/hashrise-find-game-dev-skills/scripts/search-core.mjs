/**
 * Hashrise 游戏开发 Skill 导航 · 检索核心
 *
 * 该文件同时被站点前端与安装后的导航 Skill 共用：
 * 站点构建时内联进单文件 HTML；Skill 打包时复制为 scripts/search-core.mjs。
 * 保持纯 ESM、无外部依赖、Node.js 22+ 可直接运行。
 */

/** 分类别名：把用户口语映射到目录分类 */
export const categoryAliases = {
  '概念与策划': ['概念', '策划', 'gdd', '设计文档', '世界观', '玩法', '数值', '平衡', '经济', '成长', '关卡', '新手', '留存', '叙事', '剧情', '变现', '内购', '广告', '支柱', '循环', '里程碑', '试玩'],
  '引擎与实现': ['godot', 'unity', 'unreal', '引擎', '代码', '架构', '场景', '节点', '信号', '事件', '状态机', 'ui', '界面', '输入', '存档', '本地化', 'i18n', '移动端', '适配', '资源', 'resource', 'gdscript', '反射'],
  '美术与音频': ['美术', 'art', '像素', 'pixel', '2d', '3d', 'blender', '精灵', 'sprite', '图集', 'atlas', '动画', 'vfx', '特效', '音频', '音效', 'bgm', '材质', 'shader', 'ui素材', '风格'],
  '商业化与发行': ['steam', '商店页', 'store', '发行', '发布', '上架', '营销', 'marketing', '定价', '价格', '标签', 'tag', '预告片', 'trailer', '愿望单', '社区', '版本', '试玩', 'demo', 'playtest', 'steamworks', 'steamdeck'],
  '工程与交付': ['ci', 'cd', '构建', 'build', '流水线', 'pipeline', '导出', 'export', '发版', 'release', '测试', 'test', 'qa', 'tdd', '性能', 'perf', '优化', '打包', '签名', '自动化'],
  '质量与运营': ['质量', '评审', 'review', '埋点', '遥测', '分析', '无障碍', 'accessibility', '平衡检查', 'jam', '本地化'],
  '平台与后端': ['后端', 'backend', 'api', '云存档', 'cloud', '联机', '多人', 'multiplayer', '服务器', 'server', '导航', 'npc', '相机', '程序生成']
};

/** 引擎别名 → 目录中的引擎名 */
export const engineAliases = {
  'Godot': ['godot', 'gdscript', 'gd'],
  'Unity': ['unity', 'c#', 'csharp', 'mono'],
  'Unreal': ['unreal', 'ue4', 'ue5', 'blueprint'],
  'Web': ['web', '浏览器', 'threejs', 'html5', 'canvas'],
  'Blender': ['blender'],
  'Steam': ['steam', 'steamworks', 'steamdeck', 'valve'],
  '通用': []
};

export function inferCategory(q) {
  const t = (q || '').toLowerCase();
  return Object.entries(categoryAliases)
    .filter(([, words]) => words.some((w) => t.includes(w)))
    .map(([k]) => k);
}

export function inferEngines(q) {
  const t = (q || '').toLowerCase();
  return Object.entries(engineAliases)
    .filter(([k, words]) => k !== '通用' && words.some((w) => t.includes(w)))
    .map(([k]) => k);
}

/**
 * 目录检索。
 * @param {Array} skills 目录条目
 * @param {Object} opts q / category / engine / capability / origin / sort
 */
export function searchCatalog(skills, opts = {}) {
  const {
    q = '', category = '全部', engine = '全部', capability = '全部',
    origin = '全部', sort = 'recommended'
  } = opts;
  const query = q.toLowerCase().trim();
  const cats = inferCategory(query);
  const engines = inferEngines(query);

  let out = skills.filter((s) =>
    (category === '全部' || s.category === category) &&
    (engine === '全部' || s.platforms.includes(engine)) &&
    (capability === '全部' || s.capability === capability) &&
    (origin === '全部' || s.origin === origin)
  ).map((s) => {
    let score = s.featured ? 1 : 0;
    if (!query) return { s, score };
    const hay = [s.title, s.name, s.summary, s.author, ...(s.tags || [])].join(' ').toLowerCase();
    const exact = hay.includes(query);
    let match = exact;
    if (cats.length) {
      match = cats.includes(s.category);
      score += match ? 6 : 0;
    }
    if (engines.length) {
      const specific = s.platforms.some((p) => engines.includes(p));
      const general = s.platforms.includes('通用');
      match = (cats.length ? match : true) && (specific || general);
      score += specific ? 8 : 0;
    }
    if (!cats.length && !engines.length && !exact) {
      const tokens = query.split(/\s+/).filter(Boolean);
      match = tokens.every((t) => hay.includes(t));
    }
    if (exact) score += 20;
    return { s, score, match };
  }).filter((x) => !query || x.match);

  out.sort((a, b) => {
    if (sort === 'name') return a.s.title.localeCompare(b.s.title, 'zh-CN');
    if (sort === 'updated') return b.s.checked_at.localeCompare(a.s.checked_at) || a.s.title.localeCompare(b.s.title, 'zh-CN');
    if (sort === 'first-party') {
      const d = (b.s.origin === 'first-party') - (a.s.origin === 'first-party');
      return d || b.score - a.score;
    }
    return b.score - a.score || a.s.title.localeCompare(b.s.title, 'zh-CN');
  });
  return out.map((x) => x.s);
}

/** 汇总各维度计数 */
export function summarize(skills, key) {
  const counts = new Map();
  for (const s of skills) {
    const vals = Array.isArray(s[key]) ? s[key] : [s[key]];
    for (const v of vals) counts.set(v, (counts.get(v) || 0) + 1);
  }
  return [...counts]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh-CN'))
    .map(([name, count]) => ({ name, count }));
}

/* ------------------------------------------------------------------ *
 * 安装方式
 * ------------------------------------------------------------------ */

/** 命令行安装器支持的客户端 */
export const installationClients = [
  { id: 'codex', label: 'Codex', mode: 'command' },
  { id: 'claude-code', label: 'Claude Code', mode: 'command' },
  { id: 'cursor', label: 'Cursor', mode: 'command' },
  { id: 'codebuddy', label: 'CodeBuddy', mode: 'command' },
  { id: 'trae-cn', label: 'TRAE 国内版', mode: 'command' },
  { id: 'trae', label: 'TRAE 国际版', mode: 'command' },
  { id: 'kimi-code-cli', label: 'Kimi Code CLI', mode: 'command' },
  { id: 'qwen-code', label: 'Qwen Code', mode: 'command' },
  { id: 'workbuddy', label: 'WorkBuddy', mode: 'import', docs: 'https://www.workbuddy.cn/docs/workbuddy/Overview' },
  { id: 'other', label: '其他 Agent', mode: 'interactive' }
];

const INSTALLER_DOCS = 'https://github.com/vercel-labs/skills/blob/main/docs/agents.md';

function installationTarget(s) {
  if (!/^[\w.-]+\/[\w.-]+$/.test(s.repo) || !s.name || !/^[a-z0-9-]+$/.test(s.name)) {
    throw new Error('Invalid install target');
  }
  return `npx skills add ${s.repo} --skill ${s.name}`;
}

export function installationCommand(s, agent = 'codex') {
  const base = installationTarget(s);
  const client = installationClients.find((c) => c.id === agent);
  if (!client || !['command', 'interactive'].includes(client.mode)) {
    throw new Error('This client requires installation guidance, not a CLI command');
  }
  return client.mode === 'interactive' ? base : `${base} -a ${agent}`;
}

export function installationGuide(s, agent = 'codex') {
  installationTarget(s);
  const client = installationClients.find((c) => c.id === agent);
  if (!client) throw new Error('Unknown client');
  const packet = `下载仓库 ZIP，解压后找到 ${s.path} 所在的技能文件夹。保留 SKILL.md、脚本、参考资料等配套文件，将这个技能文件夹单独打包成 ZIP。`;
  let steps = [];
  let note = '';
  let command = null;

  if (client.mode === 'command') {
    command = installationCommand(s, agent);
    steps = [
      '在项目目录打开终端，执行下面的安装命令。',
      '重新加载 AI 工具，确认已安装列表中能找到这个技能，再描述你的任务。'
    ];
    note = '需要 Node.js 22.20+ 及网络；命令安装到当前项目。安装后仍需准备该技能要求的账号、接口或软件。安装器支持此客户端不代表本站已实测业务效果。';
  } else if (agent === 'workbuddy') {
    steps = [
      packet,
      '打开 WorkBuddy 的「专家·技能·连接器」，进入「技能」，选择「添加技能 → 上传技能」，导入刚打包的 ZIP。',
      '在「已安装」中确认技能已启用，然后在对话里点名使用它。'
    ];
    note = '本目录中的技能不一定已上架 WorkBuddy 技能市场。通过聊天搜索市场并不能保证找到这里的每个技能；此处使用本地技能包导入。WorkBuddy 与 CodeBuddy 使用各自的安装方式。';
  } else {
    command = installationCommand(s, agent);
    steps = [
      '如果你的 Agent 支持本地 Skill 且能使用终端，执行下面的命令，再从安装器显示的列表选择你的 Agent。',
      '若安装器没有列出它，先查看该 Agent 的官方导入说明，使用完整技能文件夹或 ZIP 导入；不要猜安装目录。'
    ];
    note = '此命令会让你选择客户端。只有安装器列出的客户端才能使用这条安装路径。';
  }
  return {
    client: client.id,
    label: client.label,
    mode: client.mode,
    command,
    steps,
    note,
    docs: client.docs || INSTALLER_DOCS,
    checked_at: s.checked_at,
    tested: false
  };
}

/** 第一方技能的安装说明（不走上游仓库） */
export function firstPartyGuide(s) {
  return {
    client: 'workbuddy',
    label: 'WorkBuddy',
    mode: 'import',
    command: null,
    steps: [
      `克隆或下载 ${s.repo_url} 仓库。`,
      `找到 ${s.path} 所在的技能文件夹，连同 references/、scripts/ 等配套文件一起保留。`,
      '打开 WorkBuddy 的「专家·技能·连接器」→「技能」→「添加技能 → 上传技能」，导入该文件夹打包的 ZIP。',
      '在「已安装」中确认技能已启用，然后在对话里点名使用它。'
    ],
    note: '第一方技能来自《算力崛起 Hashrise》的真实工程实践，方法已在本项目内验证；迁移到其他引擎时，具体阈值与配置需按项目调整。',
    docs: 'https://www.workbuddy.cn/docs/workbuddy/Overview',
    checked_at: s.checked_at,
    tested: true
  };
}
