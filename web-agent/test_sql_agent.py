from agent_service import AgentService
from config import get_settings


def main():
    settings = get_settings()
    service = AgentService(settings)

    print("SQLDatabaseToolkit CLI 已启动，输入 exit 退出。")
    while True:
        question = input("\n你: ").strip()
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            break

        result = service.ask(question)
        print(f"\nAI: {result['answer']}")


if __name__ == "__main__":
    main()
