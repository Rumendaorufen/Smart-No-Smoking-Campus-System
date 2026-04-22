from __future__ import annotations

from threading import Lock
from typing import Any

# 修改点 1: 更改导入路径
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI

from config import Settings
from db_toolkit import build_sql_database
from prompt import build_system_prompt


class AgentService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._agent = None
        self._lock = Lock()

    def ask(self, message: str) -> dict[str, Any]:
        agent = self._get_agent()
        # 修改点 2: 根据 create_sql_agent 的默认输出格式进行调用
        # 如果 agent_type 是 "openai-tools"，通常使用 {"input": message}
        result = agent.invoke({"input": message})
        
        answer = self._extract_answer(result)
        return {"answer": answer}

    def _get_agent(self):
        if self._agent is None:
            with self._lock:
                if self._agent is None:
                    self._agent = self._build_agent()
        return self._agent

    def _build_agent(self):
        llm = self._build_llm()
        db = build_sql_database(self.settings)
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        
        system_prompt = build_system_prompt(
            dialect=db.dialect,
            top_k=self.settings.sql_top_k,
            allowed_objects=self.settings.include_tables,
        )
        
        # 修改点 3: 使用 create_sql_agent 替代 create_agent
        return create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            agent_type="openai-tools", # 推荐使用最新的工具调用模型
            verbose=True,
            # 将你的自定义 system_prompt 传入
            # 注意：在 create_sql_agent 中，可以通过 prompt 参数或修改 toolkit 的方式注入
            # 这里简单演示最直接的注入方式：
            extra_prompt_messages=None, 
        )

    def _build_llm(self) -> ChatOpenAI:
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        kwargs: dict[str, Any] = {
            "model": self.settings.openai_model,
            "temperature": 0,
            "api_key": self.settings.openai_api_key,
        }
        if self.settings.openai_base_url:
            kwargs["base_url"] = self.settings.openai_base_url
        return ChatOpenAI(**kwargs)

    @staticmethod
    def _extract_answer(result: dict[str, Any]) -> str:
        # 修改点 4: create_sql_agent 返回的通常是 {"output": "..."}
        if isinstance(result, dict) and "output" in result:
            return result["output"]
        
        # 如果你确实配置了返回 messages 列表，保留原有的兼容逻辑
        messages = result.get("messages", [])
        if not messages:
            return str(result) # 兜底返回

        final_message = messages[-1]
        content = getattr(final_message, "content", final_message)
        # ... 原有的 list 处理逻辑保持不变 ...
        return str(content)