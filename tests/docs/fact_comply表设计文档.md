# fact_comply 合规事实表设计文档

## 表基本信息

| 属性 | 值 |
|------|-----|
| 表名 | fact_comply |
| 中文名 | 合规事实表 |
| 所属系统 | 合规系统 |
| 数据库 | dwd_comply |
| Schema | public |
| 数据库类型 | PostgreSQL |
| 表类型 | 事实表 (Fact) |
| 存储引擎 | InnoDB |
| 字符集 | utf8mb4 |

## 表说明

合规事实表，记录每笔合规审查的执行事实数据，包含审查类型、审查结果、风险评级、审查人等信息，与客户维度表 (`dim_customer`) 通过 `customer_id` 关联。

## 字段设计

| 序号 | 字段名 | 中文名 | 数据类型 | 长度 | 精度 | 主键 | 非空 | 默认值 | 说明 |
|------|--------|--------|----------|------|------|------|------|--------|------|
| 1 | comply_id | 合规记录ID | VARCHAR | 32 | - | PK | NOT NULL | - | 合规记录唯一标识，主键 |
| 2 | customer_id | 客户ID | VARCHAR | 32 | - | FK | NOT NULL | - | 关联 dim_customer.customer_id |
| 3 | comply_type | 审查类型 | VARCHAR | 32 | - | - | NOT NULL | - | KYC/AML/CTF/制裁/反欺诈 |
| 4 | comply_result | 审查结果 | VARCHAR | 16 | - | - | NOT NULL | - | pass-通过/fail-不通过/pending-待定 |
| 5 | check_date | 审查日期 | DATE | - | - | - | NOT NULL | CURRENT_DATE | 合规审查执行日期 |
| 6 | auditor | 审查人 | VARCHAR | 64 | - | - | - | - | 执行审查的审核员姓名 |
| 7 | risk_level | 风险等级 | VARCHAR | 16 | - | - | NOT NULL | 'medium' | low-低/medium-中/high-高/critical-严重 |
| 8 | remark | 备注 | TEXT | - | - | - | - | - | 审查备注或补充说明 |
| 9 | regulatory_ref | 监管参考 | VARCHAR | 128 | - | - | - | - | 引用的监管法规或标准编号 |
| 10 | create_time | 创建时间 | TIMESTAMP | - | - | - | NOT NULL | CURRENT_TIMESTAMP | 记录创建时间戳 |

## 索引设计

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| pk_comply_id | 主键 | comply_id | 合规记录ID主键索引 |
| idx_customer_id | 外键 | customer_id | 关联客户维度表 |
| idx_comply_type | 普通 | comply_type | 按审查类型筛选 |
| idx_check_date | 普通 | check_date | 按审查日期范围查询 |
| idx_comply_result | 普通 | comply_result | 按审查结果筛选 |
| idx_risk_level | 普通 | risk_level | 按风险等级筛选 |
| idx_auditor_date | 联合 | auditor, check_date | 按审查人+日期组合查询 |

## 关联关系

| 外键 | 引用表 | 引用字段 | 关系说明 |
|------|--------|----------|----------|
| customer_id | dim_customer | customer_id | 多对一：多条合规记录可关联同一客户 |

## DDL 语句

```sql
CREATE TABLE fact_comply (
    comply_id      VARCHAR(32)   NOT NULL  COMMENT '合规记录ID，主键',
    customer_id    VARCHAR(32)   NOT NULL  COMMENT '客户ID，外键关联 dim_customer',
    comply_type    VARCHAR(32)   NOT NULL  COMMENT '审查类型：KYC/AML/CTF/制裁/反欺诈',
    comply_result  VARCHAR(16)   NOT NULL  COMMENT '审查结果：pass/fail/pending',
    check_date     DATE          NOT NULL  DEFAULT CURRENT_DATE COMMENT '审查日期',
    auditor        VARCHAR(64)             COMMENT '审查人',
    risk_level     VARCHAR(16)   NOT NULL  DEFAULT 'medium' COMMENT '风险等级：low/medium/high/critical',
    remark         TEXT                    COMMENT '备注',
    regulatory_ref VARCHAR(128)            COMMENT '监管法规参考',
    create_time    TIMESTAMP     NOT NULL  DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (comply_id),
    INDEX idx_customer_id (customer_id),
    INDEX idx_comply_type (comply_type),
    INDEX idx_check_date (check_date),
    INDEX idx_comply_result (comply_result),
    INDEX idx_risk_level (risk_level),
    INDEX idx_auditor_date (auditor, check_date),
    CONSTRAINT fk_fact_comply_customer FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合规事实表';
```

## 数据示例

| comply_id | customer_id | comply_type | comply_result | check_date | auditor | risk_level | remark | regulatory_ref | create_time |
|-----------|-------------|-------------|---------------|------------|---------|------------|--------|----------------|-------------|
| CP001 | C001 | KYC | pass | 2025-03-15 | 赵审核 | low | 身份验证通过 | KYC-2024-V3 | 2025-03-15 09:30:00 |
| CP002 | C002 | AML | pass | 2025-03-16 | 赵审核 | low | 无异常交易记录 | AML-2024 | 2025-03-16 10:00:00 |
| CP003 | C003 | KYC | fail | 2025-03-18 | 钱审查 | high | 企业法人信息不匹配 | KYC-2024-V3 | 2025-03-18 14:20:00 |
| CP004 | C003 | 反欺诈 | pending | 2025-03-20 | 孙核查 | critical | 存在关联风险交易，需进一步调查 | AFR-2025 | 2025-03-20 08:45:00 |
| CP005 | C004 | AML | pass | 2025-03-22 | 钱审查 | medium | 历史交易需持续监控 | AML-2024 | 2025-03-22 11:00:00 |
| CP006 | C005 | CTF | pass | 2025-04-01 | 赵审核 | low | 无涉恐融资风险 | CTF-2024 | 2025-04-01 09:15:00 |
| CP007 | C005 | 制裁 | fail | 2025-04-05 | 孙核查 | critical | 命中制裁名单 | SAN-2025-Q2 | 2025-04-05 16:30:00 |
