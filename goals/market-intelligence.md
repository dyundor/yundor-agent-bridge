# Yundor Market Intelligence — Supervisor Goal

## Ultimate Goal

持续开发 Yundor Market Intelligence，直至形成可实际用于发现、联系、跟进并转化
北美卫浴买家的完整销售情报闭环（end-to-end sales intelligence loop）。

## Business Objective

帮助 Yundor 更快找到真实客户。

> Every feature must answer: 这个功能是否帮助 Yundor 更快找到真实客户？

## Priorities

```
P0 (核心)
├── 买家发现        Buyer discovery from trade data
├── 买家排序        Buyer ranking & qualification
├── 产品机会        Product opportunity & hot-selling intelligence
├── 可联系性        Contactability & verified contact routes
├── 买家画像        Buyer profiles & qualification cards
├── 开发策略        OEM/ODM, private label, distribution strategy
└── CRM 转化跟进    Lead pipeline, outreach drafts, follow-up tasks

P1 (支撑)
├── 数据清洗        Data normalization & deduplication
├── 企业匹配        Company identity resolution
├── 官网验证        Website discovery & verification pipeline
├── 贸易关系准确性  Trade relationship accuracy
└── 评分模型        Scoring & ranking models

P2 (基础设施)
├── 架构优化        Architecture improvements
└── 性能与重构      Performance & refactoring
    (仅当直接支撑 P0/P1 时进行)
```

## Current Sprint Status

- **已完成**: Sprint 15.69 — Product → Qualified Buyer Linkage
  - 热卖产品买家列表 API（身份验证 + 商业适配 + 联系方式）
  - 前端产品买家面板（合格买家前置，排除者单独标记）
  - 157 tests pass

- **下一步**: Sprint 15.70 — 代表产品资源覆盖
  - 将官方产品页扩大到全部 9 个归一化品类
  - 为每条资源保留品牌、型号、产品 URL、图片 URL、来源类型和核验日期
  - 图片加载失败必须有占位状态

- **后续**: Sprint 15.71 — 产品趋势和数据可信度

## Constraints

### 数据保护
- NULL 永远不得覆盖现有非空值
- 简略地址不得覆盖完整地址
- 缺少官网的新数据不得删除旧官网
- 较低质量数据不得覆盖更丰富的 enrichment 数据
- 不通过把值清空来"纠错"；改为标记 unverified 并保留原始值与证据
- 保留原始外部数据，使分类、聚合和排名可重建

### API 预算
- ImportYeti 总预算: 100 credits
- 默认最低保留: 25 credits
- 任何付费 API 调用前必须: 查缓存 → 查免费源 → 估算费用 → 获取明确审批
- 未获审批绝对不能调用
- 测试只能使用 mock/fixture，不得调用付费 API

### 开发纪律
- 按 Sprint 小步增量开发
- 只做有明确业务价值的最小改动
- 每个 Sprint: 检查状态 → 最小改动 → 构建+测试 → Git 提交 → 报告
- 不重写已完成模块
- 不伪造联系人、邮箱、电话、产品图片、销量数据
- 不把聚合贸易统计宣称为企业级提单

### Git
- 提交格式: `Sprint XX.XX: Short description`
- 不覆盖用户未提交改动
- 不用 `git reset --hard` 或其他破坏性操作
- 每个 Sprint 只暂存明确相关文件

### 环境
- 项目路径: `/Users/yundor/Downloads/windows 迁移过来的/站点搭建/market-intelligence`
- 构建: `npm run build`
- 测试: `npm test`
- Lint: `npm run lint`
- 数据库: `.wrangler/state/v3/d1/miniflare-D1DatabaseObject/*.sqlite`

## Acceptance Criteria (Sprint Level)

每个 Sprint 完成后:
1. `npm test` 全部通过
2. `npm run build` 通过
3. 无调用付费 API
4. Git commit 含 hash
5. 报告: 文件变化 / 技术改动 / 验证 / Credit 用量 / 风险 / 下一步
