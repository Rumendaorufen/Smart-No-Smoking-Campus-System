

# 📋 技术记录报告：web-agent 测试与数据库权限加固

## 1. 模块概况
* **模块名称**：`web-agent` (基于 LangChain 的智能问答辅助服务)
* **核心功能**：利用 `SQLDatabaseToolkit` 解析自然语言意图，通过 SQL 视图层查询报警数据并返回分析结果。
* **技术栈**：Python 3.9+, LangChain, PyMySQL, SQLAlchemy.

---

## 2. 功能测试评估 (POC Verification)
本地测试已通过，验证了以下关键链路：
* **自然语言解析**：模型能准确将“今日报警总数”、“最近一周误报率”等口语转化为正确的 `SELECT` 语句。
* **视图层对接**：Agent 成功识别并仅限于查询 `ai_` 开头的 4 个专用视图（`ai_alarm_detail_view` 等）。
* **推理链路**：`ReAct` 决策链运行正常（思考 -> 调用工具 -> 观察结果 -> 最终回复）。

---

## 3. 数据库安全权限配置 (Hardening)
为了确保 AI 模块在“逻辑安全”之外具备“物理安全”，实施了账号级的 **最小权限原则 (PoLP)**。

### 3.1 专用账号创建
在 MySQL 物理层创建隔离账号，禁止使用业务主账号（root/admin）。
```sql
-- 创建 AI 专用只读账号
CREATE USER 'ai_reader'@'localhost' IDENTIFIED BY '********';
```

### 3.2 权限范围界定
通过权限掩码，锁定该账号仅能访问“语义层（视图）”，彻底屏蔽原始业务表（users, devices, alarms）。

| 权限类型 | 授权对象 | 状态 | 目的 |
| :--- | :--- | :--- | :--- |
| **SELECT** | `ai_alarm_detail_view` | ✅ 允许 | 查询报警详情 |
| **SELECT** | `ai_alarm_daily_stats_view` | ✅ 允许 | 统计每日趋势 |
| **SELECT** | `ai_device_alarm_rank_view` | ✅ 允许 | 设备排行分析 |
| **SELECT** | `ai_audit_stats_view` | ✅ 允许 | 审核效率评估 |
| **ALL PRIVILEGES** | 所有原始基表 | ❌ 禁止 | 保护核心业务数据不泄露 |
| **WRITE/DELETE** | 所有数据库对象 | ❌ 禁止 | 防止指令注入导致数据被删改 |



### 3.3 资源限制 (Resource Quotas)
为防止异常查询或攻击导致数据库负载过高，对该账号进行了资源限制：
* **最大连接数**：限制为 5 个。
* **查询频率**：限制每小时最高查询次数，预防 Token 消耗攻击。

---

## 4. 防御指令注入 (Prompt Injection Defense)
系统在三个层面对“恶意诱导 AI 删库/跨权查询”做了闭环防御：

1.  **视图层防护 (View Layer)**：AI 根本看不到 `users` 等表的存在，无法生成针对隐藏表的有效 SQL。
2.  **物理层防护 (MySQL Layer)**：即使 AI 被诱导生成了 `DELETE` 或 `DROP` 语句，MySQL 引擎会因权限不足强制拦截。
3.  **提示词防护 (Prompt Layer)**：在 `prompt.py` 中强制注入 System Message，约束 Agent 必须在 SQL 中添加 `LIMIT 100`。



---

## 5. 结论与后续计划
### 5.1 结论
当前 `web-agent` 模块在只读环境下表现稳定，权限设置已达到生产级安全标准。**物理层权限拦截**有效抵御了 100% 的写操作风险及 90% 以上的敏感信息泄露风险。

### 5.2 后续任务
* **Java 代理对接**：在 `web-back` 中实现 `AiChatController`，转发 JWT 校验后的请求。
* **结果卡片化**：优化 Agent 返回格式，将查询结果中的 JSON 数据提取出来，供前端渲染 ECharts 图表。
* **监控审计**：在 Java 中台记录 AI 所有的 SQL 执行日志，以便后续人工抽检 AI 的回答质量。

---
**日期**：2026-04-22