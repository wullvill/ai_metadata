# dim_customer 客户维度表设计文档

## 表基本信息

| 属性 | 值 |
|------|-----|
| 表名 | dim_customer |
| entity_type | table |
| 中文名 | 客户维度表 |
| 所属系统 | 主数据系统 |
| 数据库 | dwd_master |
| Schema | public |
| 数据库类型 | PostgreSQL |
| 表类型 | 维度表 (Dimension) |
| 存储引擎 | InnoDB |
| 字符集 | utf8mb4 |

## 表说明

客户维度表，存储客户主数据信息，包含客户基本信息、联系方式、地域属性等，为主数据系统的核心维度表之一。

## 字段设计

| 序号 | 字段名 | 中文名 | 数据类型 | 长度 | 精度 | 主键 | 非空 | 默认值 | 说明                          |
|------|--------|--------|----------|------|------|------|------|--------|-----------------------------|
| 1 | customer_id | 客户ID | VARCHAR | 32 | - | PK | NOT NULL | - | 客户唯一标识，主键                   |
| 2 | customer_name | 客户名称 | VARCHAR | 128 | - | - | NOT NULL | - | 客户姓名/企业名称                   |
| 3 | customer_type | 客户类型 | VARCHAR | 32 | - | - | - | '个人' | 客户类型：个人/企业/政府/其他            |
| 4 | gender | 性别 | VARCHAR | 8 | - | - | - | - | 性别：男/女/未知                   |
| 5 | birth_date | 出生日期 | DATE | - | - | - | - | - | 出生日期                        |
| 6 | city | 所在城市 | VARCHAR | 64 | - | - | - | - | 客户所在城市                      |
| 7 | province | 所在省份 | VARCHAR | 64 | - | - | - | - | 客户所在省份                      |
| 8 | email | 电子邮箱 | VARCHAR | 128 | - | - | - | - | 客户电子邮箱地址                    |
| 9 | phone | 联系电话 | VARCHAR | 20 | - | - | - | - | 客户联系电话                      |
| 10 | create_date | 创建日期 | DATE | - | - | - | NOT NULL | CURRENT_DATE | 记录创建日期                      |
| 11 | update_date | 更新日期 | DATE | - | - | - | - | - | 记录最后更新日期                    |
| 12 | status | 状态 | VARCHAR | 16 | - | - | NOT NULL | 'active' | 客户状态：active-活跃/inactive-非活跃 |

## 索引设计

| 索引名 | 类型 | 字段 | 说明 |
|--------|------|------|------|
| pk_customer_id | 主键 | customer_id | 客户ID主键索引 |
| idx_customer_name | 普通 | customer_name | 客户名称查询索引 |
| idx_customer_type | 普通 | customer_type | 按客户类型筛选 |
| idx_city_province | 联合 | city, province | 按城市和省份组合查询 |
| idx_status | 普通 | status | 按状态筛选活跃客户 |
| idx_create_date | 普通 | create_date | 按创建日期范围查询 |

## DDL 语句

```sql
CREATE TABLE dim_customer (
    customer_id   VARCHAR(32)   NOT NULL  COMMENT '客户ID，主键',
    customer_name VARCHAR(128)  NOT NULL  COMMENT '客户名称',
    customer_type VARCHAR(32)   DEFAULT '个人' COMMENT '客户类型：个人/企业/政府/其他',
    gender        VARCHAR(8)              COMMENT '性别：男/女/未知',
    birth_date    DATE                    COMMENT '出生日期',
    city          VARCHAR(64)             COMMENT '所在城市',
    province      VARCHAR(64)             COMMENT '所在省份',
    email         VARCHAR(128)            COMMENT '电子邮箱',
    phone         VARCHAR(20)             COMMENT '联系电话',
    create_date   DATE          NOT NULL  DEFAULT CURRENT_DATE COMMENT '创建日期',
    update_date   DATE                    COMMENT '更新日期',
    status        VARCHAR(16)   NOT NULL  DEFAULT 'active' COMMENT '状态：active-活跃/inactive-非活跃',
    PRIMARY KEY (customer_id),
    INDEX idx_customer_name (customer_name),
    INDEX idx_customer_type (customer_type),
    INDEX idx_city_province (city, province),
    INDEX idx_status (status),
    INDEX idx_create_date (create_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户维度表';
```

## 数据示例

| customer_id | customer_name | customer_type | gender | birth_date | city | province | email | phone | create_date | update_date | status |
|-------------|---------------|---------------|--------|------------|------|----------|-------|-------|-------------|-------------|--------|
| C001 | 张三 | 个人 | 男 | 1990-03-15 | 深圳 | 广东 | zhangsan@example.com | 13800138001 | 2025-01-01 | 2025-06-15 | active |
| C002 | 李四 | 个人 | 女 | 1988-07-22 | 上海 | 上海 | lisi@example.com | 13900139002 | 2025-01-05 | 2025-05-20 | active |
| C003 | 北京科技有限公司 | 企业 | - | - | 北京 | 北京 | info@bjkj.com | 010-88880001 | 2025-02-10 | 2025-06-01 | active |
| C004 | 上海金融集团 | 企业 | - | - | 上海 | 上海 | contact@shjr.com | 021-66660002 | 2025-02-15 | 2025-03-01 | inactive |
| C005 | 王五 | 个人 | 男 | 1995-11-08 | 广州 | 广东 | wangwu@example.com | 13700137003 | 2025-03-01 | 2025-06-10 | active |
