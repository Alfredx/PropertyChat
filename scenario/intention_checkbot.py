from .agents import TrackableAssistantAgent, llm_config_gpt3
from autogen import AssistantAgent, UserProxyAgent

intention_checkbot = AssistantAgent(
    name="intention_checkbot",
    llm_config=llm_config_gpt3,
    system_message="""You are a helpful assistant. 
    Your job is to check Admin's intention of his question.
    You must choose one of the following intention and no others:
    1. If the admin want to rent a unit or find a tenant, reply RENT
    2. If the admin want to learn about certain companies, reply INFO
    3. None of the above
    Reply with one of the following answer:
    RENT, INFO, NONE
"""
)

def intention_is_termination_msg(message):
    content = message.get("content", "")
    return content in ["RENT", "INFO", "NONE"]
    

intention_user_proxy = UserProxyAgent(
    name="Admin",
    human_input_mode="NEVER",
    llm_config=llm_config_gpt3,
    is_termination_msg=intention_is_termination_msg,
    code_execution_config={
        "last_n_messages": 1,
        "work_dir": "tasks",
        "use_docker": False,
    },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
)

def intention_check(intention: str) -> str:
    if not intention:
        return None
    chat_result = intention_user_proxy.initiate_chat(
        intention_checkbot,
        message=intention
    )
    if history := chat_result.chat_history:
        return history[-1]['content']
    return None

if __name__ == "__main__":
    intention_check()