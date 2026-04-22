from __future__ import annotations
from threading import Lock
from typing import Any

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

    def ask(self, message: str, conversation_id: str) -> dict[str, Any]:
        executor = self._get_agent_executor()

        # 🚀 1. 独立连接数据库读取历史记录
        history = SQLChatMessageHistory(
            session_id=conversation_id,
            connection=self.settings.db_uri,
            table_name="ai_chat_history"
        )

        # 🚀 2. 提取最近 5 轮对话（10条消息），防止上下文超长导致 Token 爆炸
        history_context = ""
        recent_messages = history.messages[-10:]
        if recent_messages:
            history_context = "### 历史对话上下文 ###\n"
            for msg in recent_messages:
                role = "用户" if msg.type == "human" else "AI"
                history_context += f"{role}: {msg.content}\n"
            history_context += "\n"

        # 🚀 3. 强行将历史记录和当前问题合并成一段完整输入
        enriched_input = f"{history_context}### 当前新问题 ###\n{message}"

        try:
            # 🚀 4. 执行查询（AI 这次绝对能看到历史记录了）
            result = executor.invoke({"input": enriched_input})
            answer = result.get("output", str(result))

            # 🚀 5. 对话成功后，手动将一问一答存入数据库
            history.add_user_message(message)
            history.add_ai_message(answer)

            return {"answer": answer}
        except Exception as e:
            raise RuntimeError(f"AI 对话存取异常: {str(e)}")

    def _get_agent_executor(self):
        if self._agent_executor is None:
            with self._lock:
                if self._agent_executor is None:
                    self._agent_executor = self._build_agent_executor()
        return self._agent_executor

    def _build_agent_executor(self):
        llm = self._build_llm()
        db = build_sql_database(self.settings)
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        
        system_prompt = build_system_prompt(
            dialect=db.dialect,
            top_k=self.settings.sql_top_k,
            allowed_objects=self.settings.include_tables,
        )
        
        # 🚀 恢复最干净的代理结构，不再使用易错的 extra_prompt_messages
        return create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            agent_type="openai-tools",
            verbose=True,
            prefix=system_prompt
        )

    def _build_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.settings.openai_model,
            temperature=0,
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url
        )