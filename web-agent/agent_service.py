from __future__ import annotations
import asyncio
import re
from threading import Thread, Lock
from queue import Queue
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import SQLChatMessageHistory
from config import Settings
from db_toolkit import build_sql_database
from prompt import build_system_prompt

class AgentService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._agent_executor = None
        self._lock = Lock()

    # 🚀 修复之前的 AttributeError
    def _get_history(self, conversation_id: str):
        return SQLChatMessageHistory(
            session_id=conversation_id,
            connection=self.settings.db_uri,
            table_name="ai_chat_history"
        )

    def ask_stream(self, message: str, conversation_id: str):
        executor = self._get_agent_executor()
        history = self._get_history(conversation_id)
        
        # 🚀 核心修复：提取数据库里的历史记录并喂给大模型
        history_context = ""
        # 为了防止 Token 爆炸或 AI 混淆，我们只取最近的 6 条消息（即最近 3 轮对话）
        if history.messages:
            recent_messages = history.messages[-6:]
            for msg in recent_messages:
                # 区分是用户说的还是 AI 说的
                role = "用户" if msg.type == "human" else "AI"
                history_context += f"{role}：{msg.content}\n"

        # 根据是否有历史记录，动态构建丢给大模型的 Prompt
        if history_context.strip():
            enriched_input = f"【以下是你和用户的近期对话历史】\n{history_context}\n【当前用户的新问题】\n{message}\n\n请结合历史上下文回答当前问题。"
        else:
            enriched_input = f"【当前用户的问题】\n{message}"

        q = Queue()

        def _run_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def _astream():
                full_answer = ""
                is_thinking = False # 🚀 核心：思考状态拦截
                try:
                    async for event in executor.astream_events({"input": enriched_input}, version="v2"):
                        kind = event["event"]
                        
                        if kind == "on_tool_start":
                            is_thinking = True
                            q.put(f"\n> 🔍 *AI 正在分析：{event['name']}...*\n\n")

                        elif kind == "on_tool_end":
                            is_thinking = False

                        elif kind == "on_chat_model_stream":
                            content = event["data"]["chunk"].content
                            if not content: continue
                            
                            # 只判断思考状态，彻底移除易误伤的 is_sql
                            if not is_thinking:
                                if not event["data"]["chunk"].tool_call_chunks:
                                    full_answer += content
                                    q.put(content)

                    if full_answer.strip():
                        history.add_user_message(message)
                        history.add_ai_message(full_answer.strip())
                finally:
                    # 通知队列结束
                    q.put(None)
            
            try:
                # 正常运行异步流
                loop.run_until_complete(_astream())
            finally:
                # 安全清理事件循环
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception: 
                    pass
                loop.close()

        # 1. 启动后台线程执行推理
        Thread(target=_run_task, daemon=True).start()
        
        # 2. 🌟 这里是最关键的！必须定义生成器并 return 出来
        def generate():
            while True:
                chunk = q.get()
                if chunk is None: break
                yield chunk
                
        return generate()

    def _get_agent_executor(self):
        if self._agent_executor is None:
            with self._lock:
                if self._agent_executor is None:
                    self._agent_executor = self._build_agent_executor()
        return self._agent_executor

    def _build_agent_executor(self):
        llm = self._build_llm()
        db = build_sql_database(self.settings)
        # toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        # 🚀 1. 核心修复：创建一个局部的自定义 Toolkit 类
        # 通过继承原生的 SQLDatabaseToolkit，重写 get_tools 方法来强行拦截
        class FastSQLToolkit(SQLDatabaseToolkit):
            def get_tools(self):
                # 获取原本所有的工具
                all_tools = super().get_tools()
                # 强行过滤，只交出查询和检查语法的工具
                return [t for t in all_tools if t.name in ["sql_db_query", "sql_db_query_checker"]]
        
        # 🚀 2. 实例化我们自定义的“极速版” Toolkit
        toolkit = FastSQLToolkit(db=db, llm=llm)

        prompt = build_system_prompt(db.dialect, self.settings.sql_top_k, self.settings.include_tables)
        return create_sql_agent(llm=llm, 
                                # toolkit=toolkit, 
                                toolkit=toolkit, # 传入精简后的工具
                                agent_type="openai-tools", 
                                verbose=True, 
                                prefix=prompt)

    def _build_llm(self) -> ChatOpenAI:
        return ChatOpenAI(model=self.settings.openai_model, temperature=0, streaming=True, 
                          api_key=self.settings.openai_api_key, base_url=self.settings.openai_base_url)