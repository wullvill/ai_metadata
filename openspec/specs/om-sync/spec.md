# Capability: OpenMetadata 同步 (om-sync)

## Overview

管理系统与外部 OpenMetadata 平台之间的双向数据同步：定时从 OpenMetadata 拉取元数据更新本地索引，审核确认后将补全结果回写 OpenMetadata。

## Requirements

### Requirement: 元数据拉取

定时从 OpenMetadata 拉取元数据，更新本地 Milvus 向量库和 ES 索引。

#### Scenario: 增量同步

- **GIVEN** OpenMetadata 中有新的元数据变更
- **WHEN** Celery 定时任务每 15 分钟执行增量同步
- **THEN** 拉取增量变更的实体
- **AND** 更新本地 Milvus 向量库和 ES 索引

#### Scenario: 全量同步

- **GIVEN** 系统需要全量重建索引
- **WHEN** 每日凌晨执行全量同步 Job
- **THEN** 拉取所有已纳管元数据实体
- **AND** 重新向量化并写入 Milvus
- **AND** 重新索引到 ES

#### Scenario: 同步状态查询

- **GIVEN** 用户需要了解同步状态
- **WHEN** GET /api/v1/sync/status
- **THEN** 返回最近同步时间、同步实体数量、失败数量

### Requirement: 补全结果回写

审核确认后将补全结果以 JSON Patch 格式回写 OpenMetadata。

#### Scenario: 表级回写

- **GIVEN** 一条表补全记录 review_status = "approved"
- **WHEN** 触发 OM 回写
- **THEN** 通过 OM API 以 JSON Patch 格式更新表的 tags、description、displayName
- **AND** 更新 completion_records.synced_to_om = true

#### Scenario: 字段级回写

- **GIVEN** 一条字段补全记录 review_status = "approved"
- **WHEN** 触发 OM 回写
- **THEN** 通过 OM API 更新字段的 tags、description、displayName
- **AND** 更新 completion_records.synced_to_om = true

#### Scenario: 回写重试机制

- **GIVEN** OpenMetadata API 暂时不可用导致回写失败
- **WHEN** 首次回写失败
- **THEN** 自动重试 3 次，间隔递增（1s, 5s, 15s）
- **AND** 3 次后仍失败则记录错误详情并触发告警

#### Scenario: 回写状态监控

- **GIVEN** 回写失败累计超过阈值
- **WHEN** 连续 3 次同步失败
- **THEN** 触发通知告警

### Requirement: 同步状态查询

提供同步任务的状态查询接口。

#### Scenario: 查询同步状态

- **GIVEN** 最近一次增量同步在 5 分钟前完成
- **WHEN** GET /api/v1/sync/status
- **THEN** 返回 last_sync_time、synced_count、failed_count

## Non-Goals

- OpenMetadata 平台本身的运维管理
- 元数据版本管理和回滚
- 跨多个 OpenMetadata 实例的聚合同步
