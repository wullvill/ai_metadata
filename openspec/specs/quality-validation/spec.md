# Capability: 质量校验 (quality-validation)

## Overview

对 LLM 生成的补全结果进行多维度质量校验，包括置信度修正、规则引擎校验和冲突检测，最终根据综合评分将结果分流为自动采纳、待审核或拒绝。

## Requirements

### Requirement: 置信度修正

基于客观因子对 LLM 自评置信度进行修正，降低 LLM 过度自信导致的误采纳风险。

#### Scenario: 检索质量差导致降权

- **GIVEN** LLM 自评 confidence=0.82，但检索上下文平均分数 < 0.05
- **WHEN** 置信度修正计算
- **THEN** 置信度降权 0.15，修正为 0.67

#### Scenario: 描述过短导致降权

- **GIVEN** LLM 生成的 description 长度 < 10 字符
- **WHEN** 置信度修正计算
- **THEN** 置信度额外降权 0.20

#### Scenario: 描述过长导致降权

- **GIVEN** LLM 生成的 description 长度 > 300 字符
- **WHEN** 置信度修正计算
- **THEN** 置信度额外降权 0.10

#### Scenario: 中文名含特殊字符降权

- **GIVEN** display_name 包含 `{}`、`[]`、`()` 等特殊字符
- **WHEN** 置信度修正计算
- **THEN** 置信度额外降权 0.15

#### Scenario: 标签数量异常降权

- **GIVEN** 生成的 tags 为空数组 → 降权 0.10
- **AND** 生成的 tags 超过 8 个 → 降权 0.05

### Requirement: 规则引擎校验

基于预定义规则校验 LLM 输出质量，规则按严重级别分为 CRITICAL / WARNING / INFO 三级。

#### Scenario: 必填字段缺失 (CRITICAL)

- **GIVEN** LLM 输出缺少 display_name 或 description
- **WHEN** required_fields 规则检查
- **THEN** 标记 CRITICAL，直接拒绝

#### Scenario: 中文名包含代码 (WARNING)

- **GIVEN** display_name = "t_user_order表"
- **WHEN** display_name_no_code 规则检查
- **THEN** 标记 WARNING（中文名不应包含大段英文）

#### Scenario: 描述复制中文名 (WARNING)

- **GIVEN** display_name = "用户订单表"，description = "用户订单表"
- **WHEN** description_not_copy_name 规则检查
- **THEN** 标记 WARNING

#### Scenario: 敏感级别无效 (WARNING)

- **GIVEN** sensitive_level = "L5"
- **WHEN** sensitive_level_valid 规则检查
- **THEN** 标记 WARNING（有效范围为 L1-L4）

#### Scenario: 标签重复 (INFO)

- **GIVEN** tags = ["订单", "用户", "订单"]
- **WHEN** tag_no_duplicates 规则检查
- **THEN** 标记 INFO（存在重复标签）

#### Scenario: 表名一致性 (WARNING)

- **GIVEN** table_name = "t_user_order"，display_name = "t_user_order"
- **WHEN** table_name_consistency 规则检查
- **THEN** 标记 WARNING（中文名不应与英文表名完全相同）

### Requirement: 冲突检测

检测新生成的补全结果与已有元数据的冲突，仅标记不自动拒绝。

#### Scenario: 描述分歧检测

- **GIVEN** 表中已有 description "记录用户下单信息"，新生成 description "存储客户交易流水"
- **WHEN** 计算文本语义重叠度
- **THEN** 重叠度 < 0.3 → 标记 description_divergence (warning)

#### Scenario: 标签覆盖检测

- **GIVEN** 已有 tags = ["订单", "交易"]，新生成 tags = ["用户", "会员"]
- **WHEN** 计算标签集合交集
- **THEN** 交集为空 → 标记 tag_overhaul (info)

### Requirement: 分流路由

根据综合评分将补全结果路由到不同处理路径。

#### Scenario: 自动采纳

- **GIVEN** 修正后 confidence ≥ 0.80，且无 CRITICAL/WARNING 级规则命中
- **WHEN** 分流判断
- **THEN** review_status = "auto_approved"，直接回写 OpenMetadata 并记录审计日志

#### Scenario: 待人工审核

- **GIVEN** 修正后 confidence ≥ 0.60，且无 CRITICAL 级规则命中
- **WHEN** 分流判断
- **THEN** review_status = "pending_review"，进入审核队列并高亮问题标记

#### Scenario: 拒绝

- **GIVEN** 修正后 confidence < 0.60 或存在 CRITICAL 级规则命中
- **WHEN** 分流判断
- **THEN** review_status = "rejected"，记录拒绝原因

## Non-Goals

- 规则和阈值的 UI 动态配置（后续版本）
- 基于历史审核反馈自动调整规则/阈值
- 跨实体的批量质量一致性校验
