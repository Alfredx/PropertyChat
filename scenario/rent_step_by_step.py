import json
import time
from typing import Dict

import arrow
import streamlit as st
from autogen import AssistantAgent, UserProxyAgent
from typing_extensions import Annotated

from scripts.transform import transform2texttable

from .agents import ChatMessage
from .agents import llm_config as llm_config
from .agents import llm_config_gpt3


def extract_business_building(prompt):
    assistant = AssistantAgent(
        name="assistant",
        llm_config=llm_config_gpt3,
        system_message="""你是一个十分有用的助理。
        你的任务是找出用户提问中包含的商业楼宇名称。仅回复商业楼宇的名称，不需要回复其他内容。
        如果用户提问不包含商业楼宇名称，回复 无。
    """
    )

    user_proxy = UserProxyAgent(
        name="Admin",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: True,
        llm_config=llm_config_gpt3,
        code_execution_config={
            "use_docker":False
        }
    )

    chat_result = user_proxy.initiate_chat(
        assistant,
        message=prompt,
        summary_method="last_msg"
    )
    if history := chat_result.chat_history:
        return history[-1]['content']
    return None

def extract_office_area(prompt):
    assistant = AssistantAgent(
        name="assistant",
        llm_config=llm_config_gpt3,
        system_message="""你是一个十分有用的助理。
        你的任务是找出用户提问中想出租的办公单元的面积。仅回复数字，不需要回复其他内容。
        如果用户提问不包含面积，回复 0。
    """
    )

    user_proxy = UserProxyAgent(
        name="Admin",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: True,
        llm_config=llm_config_gpt3,
        code_execution_config={
            "use_docker":False
        }
    )

    chat_result = user_proxy.initiate_chat(
        assistant,
        message=prompt,
        summary_method="last_msg"
    )
    if history := chat_result.chat_history:
        return history[-1]['content']
    return None


def locate_business_building(location: Annotated[str, "the name of a certain business building"]) -> str:
    buildings = [
        "金虹桥国际中心",
        "SOHO天山广场",
        "兆丰广场",
        "舜元企业发展大厦",
        "尚嘉中心"
    ]
    if location in buildings:
        return [b for b in buildings if b != location]
    return []

def calculate_maximum_employee_by_area(area: Annotated[float, "the area of a renting unit."]) -> int:
    return int(area / 6)

def data_query(query: Annotated[str, "用于df.query()方法的查询条件"]) -> Annotated[str, "Output"]:
    current_df = st.session_state.current_df.query(query)
    st.session_state.current_df = current_df
    return transform2texttable(current_df)

def filter_business_building(buildings: Annotated[list[str], "The list of names of business buildings in str"]) -> Annotated[str, "Output"]:
    print(buildings)
    current_df = st.session_state.current_df.query("当前写字楼==@buildings")
    return f"共筛选出{len(current_df)}家公司"

def company_info(name: Annotated[str, "company name or 公司名称"]) -> str:
    df = st.session_state.df
    df_filtered = df[df["公司名称"] == name]
    return transform2texttable(df_filtered)

def generate_report(prompt:str, context: Dict):
    assistant = AssistantAgent(
        name="assistant",
        llm_config=llm_config_gpt3,
        system_message="""你是一个十分有用的助理。你使用丰富的语言和写作技能帮助用户制作报告。
        用户会给你提供他想了解的问题和针对这个问题收集的信息，根据信息生成一份针对用户问题的报告。
        仅回复报告内容，不需要回复其他内容。
    """
    )

    user_proxy = UserProxyAgent(
        name="Admin",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: True,
        llm_config=llm_config,
        code_execution_config={
            "use_docker":False
        }
    )

    chat_result = user_proxy.initiate_chat(
        assistant,
        message=f"""用户的提问是： {prompt}
用户收集的信息如下：
```json
{json.dumps(context, indent=4)}
```
""",
        summary_method="last_msg"
    )
    print(chat_result.cost)
    if history := chat_result.chat_history:
        return history[-1]['content']
    return None

def rent_step_by_step(prompt: str, sleep_interval: float = 1) -> None:
    with st.chat_message("user"):
        st.markdown(prompt)
        st.session_state.messages.append(ChatMessage("user", prompt))
    with st.chat_message("assistant"):
        content = """
为了替您找到合适的潜在租户，我们需要将整个过程划分为以下五步：

**1. 确定商业楼宇名称和出租面积**

**2. 根据商业楼宇名称，定位该楼附近的同类商业楼宇**

**3. 根据附近的同类商业楼宇，初步筛选公司**

**4. 根据给定的出租面积，计算出租单元能够容纳的最大员工人数**

**5. 根据计算人数，找出当前办公单元装修至少完工一年，且符合最大人数的公司**

最终，将根据符合条件的公司为您生产一份报告。请耐心等待。
"""
        st.markdown(content)
        st.session_state.messages.append(ChatMessage("assistant", content))
        time.sleep(sleep_interval*2)
    with st.chat_message("assistant"):
        content = f"#### 第一步\n\n确定商业楼宇名称和出租面积"
        st.markdown(content)
        time.sleep(sleep_interval)
        st.session_state.messages.append(ChatMessage("assistant", content))
    business_building = extract_business_building(prompt)
    office_area = extract_office_area(prompt)
    with st.chat_message("assistant"):
        content = f"商业楼宇名称为：{business_building}\n\n出租面积为：{office_area}"
        st.markdown(content)
        time.sleep(sleep_interval)
        st.session_state.messages.append(ChatMessage("assistant", content))

    with st.chat_message("assistant"):
        content = f"#### 第二步\n\n根据给定的商业楼宇，定位附近的同类商业楼宇"
        st.markdown(content)
        time.sleep(sleep_interval)
        st.session_state.messages.append(ChatMessage("assistant", content))

    nearby_buildings = locate_business_building(location=business_building)
    with st.chat_message("assistant"):
        content = f"已定位到周围的同类商业楼宇：{','.join(nearby_buildings)}"
        st.markdown(content)
        time.sleep(sleep_interval)
        st.session_state.messages.append(ChatMessage("assistant", content))

    with st.chat_message("assistant"):
        content = f"#### 第三步\n\n筛选出当前位置在上一步给出的商业楼宇中的公司"
        st.markdown(content)
        time.sleep(sleep_interval)
        st.session_state.messages.append(ChatMessage("assistant", content))
    
    filter_result = filter_business_building(buildings=nearby_buildings)
    with st.chat_message("assistant"):
        content = f"{filter_result}"
        st.markdown(content)
        time.sleep(sleep_interval)
        st.session_state.messages.append(ChatMessage("assistant", content))

    with st.chat_message("assistant"):
        content = f"#### 第四步\n\n根据给定的办公单元面积，计算出最大员工数量"
        st.markdown(content)
        time.sleep(sleep_interval)
        st.session_state.messages.append(ChatMessage("assistant", content))

    max_employee = calculate_maximum_employee_by_area(float(office_area))
    with st.chat_message("assistant"):
        content = f"根据最小人均办公面积（6平米每人），已计算出面积{office_area}平米的办公单元最大可容纳{max_employee}名员工。"
        st.markdown(content)
        time.sleep(sleep_interval)
        st.session_state.messages.append(ChatMessage("assistant", content))

    with st.chat_message("assistant"):
        content = f"#### 第五步\n\n找出公司规模小于计算出的最大员工数量，同时大于计算数的三分之一，并且'最后装修完成日期'早于一年前的公司"
        st.markdown(content)
        time.sleep(sleep_interval)
        st.session_state.messages.append(ChatMessage("assistant", content))

    query_result = data_query(f"参保人数<{max_employee} and 参保人数 > {max_employee/3} and 上次装修工程完成时间<'{str(arrow.get().shift(years=-1).date())}'")
    with st.chat_message("assistant"):
        content = f"已完成分析，正在为您生成报告，请稍候。"
        st.markdown(content)
        st.session_state.messages.append(ChatMessage("assistant", content))

    context = {
        "办公单元所在商业楼宇": business_building,
        "办公单元面积": office_area,
        "潜在租户清单": query_result
    }
    
    report = generate_report(prompt, context)
    with st.chat_message("assistant"):
        content = f"{report}"
        st.markdown(content)
        st.session_state.messages.append(ChatMessage("assistant", content))
    # 0. 确定商业楼宇名称和出租面积
    # 1. 根据给定的商业楼宇，定位附近的同类商业楼宇。
    # 2. 筛选出当前位置在第一步给出的商业楼宇中的公司。
    # 3. 根据Admin给定的办公单元面积，计算出最大员工数量。
    # 4. 找出公司规模小于计算出的最大员工数量，同时大于计算数的三分之一，并且"最后装修完成日期"早于{str(arrow.get().shift(years=-1).date())}的公司。
    # 5. 给出这些公司的具体信息，包括名字，人数，当前位置，电话，邮箱等。
    return report

if __name__ == "__main__":
    extract_business_building("我有一套位于尚嘉中心的办公单元要出租，面积共2000平米，请帮我找到合适的租户")