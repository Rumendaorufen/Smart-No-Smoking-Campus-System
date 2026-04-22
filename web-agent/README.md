# web-agent

独立的报警数据 AI 问答服务脚手架，使用 `SQLDatabaseToolkit` 连接 MySQL 只读视图。

## 目录

- `app.py`: Flask 启动入口
- `config.py`: 环境变量配置
- `db_toolkit.py`: `SQLDatabase` 初始化
- `prompt.py`: SQL Agent 系统提示词
- `agent_service.py`: Agent 构建与问答封装
- `test_sql_agent.py`: 本地命令行测试入口
- `.env.example`: 环境变量示例

## 启动前准备

1. 先执行数据库脚本：
   - `db/init.sql`
   - `db/ai_views.sql`
2. 准备一个只读数据库账号，推荐只开放 AI 专用视图
3. 配置 `.env`

## 安装依赖

```bash
cd web-agent
pip install -r requirements.txt
```

## 配置环境变量

复制 `.env.example` 为 `.env`，至少填写：

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `DB_URI`

如果你使用 OpenAI 兼容平台，也可以配置：

- `OPENAI_BASE_URL`

## 启动 HTTP 服务

```bash
cd web-agent
python app.py
```

默认接口：

- `GET /health`
- `POST /api/agent/chat`

请求体示例：

```json
{
  "message": "今天有多少报警？"
}
```

## 启动命令行测试

```bash
cd web-agent
python test_sql_agent.py
```

## 当前边界

- 只做报警数据问答
- 只读数据库
- 只允许访问 AI 专用视图
- 默认中文回答
