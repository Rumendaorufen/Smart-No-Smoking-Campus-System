import uuid
# 🚀 导入 get_settings 工厂函数
from config import get_settings
from agent_service import AgentService

def main():
    # 1. 🚀 调用工厂函数获取配置实例
    settings = get_settings()
    
    print("正在初始化 AI 分析助手，请稍候...")
    # 2. 传入 settings 实例化 AgentService
    service = AgentService(settings)
    
    print("\n✅ SQLDatabaseToolkit CLI 已启动，输入 exit 退出。")
    
    # 固定的测试会话 ID
    test_conversation_id = "test-cli-session-001"

    while True:
        question = input("\n你: ")
        if question.lower() == 'exit':
            break
            
        try:
            result = service.ask(question, test_conversation_id)
            print(f"\nAI: {result['answer']}")
        except Exception as e:
            print(f"\n报错啦: {e}")

if __name__ == "__main__":
    main()