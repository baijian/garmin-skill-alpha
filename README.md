# garmin-skill-alpha

这个技能的出发点是将 `garmin-health-analysis`、`garmin-connect-cn-data`、`garmin-sync-cn-to-global` 三个技能合并为一个本地统一入口，以满足个人 Garmin/佳明使用场景下更便捷的健康分析、CN 原始数据查询、活动文件导出解析和 CN 到 Global 同步需求。

## 来源

- `garmin-health-analysis`: 基于 [eversonl/ClawdBot-garmin-health-analysis](https://github.com/eversonl/ClawdBot-garmin-health-analysis)
- `garmin-connect-cn-data`: 本地 Garmin Connect CN 数据查询技能
- `garmin-sync-cn-to-global`: 本地 Garmin CN 到 Global 活动同步技能

## 当前定位

- `health` route: 健康、恢复、睡眠、HRV、Body Battery、训练状态和趋势分析。
- `cn` route: Garmin Connect CN 原始查询、`detail`/`run`、CSV 导出和标准化 FIT 解析。
- `sync` route: Garmin CN 到 Global 的单向活动同步。

## 说明

`garmin-skill-alpha` 是一个面向个人使用便利性的 alpha 合并版本。它尽量保留原始脚本，只通过 `scripts/garmin.py` 提供统一调度入口。

这个技能不是上述原始项目或技能的上游替代品；它只是为了本地个人工作流更顺手而做的整合。
