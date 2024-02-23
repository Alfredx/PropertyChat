import json
from typing import Dict

import arrow
import autogen
import pandas as pd
import requests
import streamlit as st
from autogen import AssistantAgent, UserProxyAgent
from fuzzywuzzy import process
from typing_extensions import Annotated

from scripts.transform import transform2texttable

from .agents import (ChatMessage, TrackableAssistantAgent,
                     TrackableGroupChatManager, TrackableUserProxyAgent)
from .agents import llm_config as llm_config
from .agents import llm_config_gpt3


def is_termination_msg(msg):
    content: str = msg.get("content", "")
    if not content:
        return False
    return "terminate" in content.lower()


def initiate_chats(message):

    rent_planner = AssistantAgent(
        name="Planner",
        llm_config=llm_config,
        is_termination_msg=is_termination_msg,
        system_message=f"""
        你是Planner。提出一个计划，帮助Admin找到最适合租赁给定的商业楼宇办公单元的若干潜在租户。
        一个计划通常有以下5个步骤，但如果需要，Planner可以添加更多步骤：
        1. 根据给定的商业楼宇，定位附近的同类商业楼宇。
        2. 筛选出当前位置在第一步给出的商业楼宇中的公司。
        3. 根据Admin给定的办公单元面积，计算出最大员工数量。
        4. 找出公司规模小于计算出的最大员工数量，同时大于计算数的三分之一，并且"最后装修完成日期"早于{str(arrow.get().shift(years=-1).date())}的公司。
        5. 给出这些公司的具体信息，包括名字，人数，当前位置，电话，邮箱等。
        该计划可能会涉及到一个Analyst提供信息。
        首先解释这个计划。并让Analyst一步一步执行。
        回复TERMINATE如果你觉得已经得到最终的报告了。
    """
    )

    query_assistant = AssistantAgent(
        name="QueryAssistant",
        llm_config=llm_config,
        system_message=f"""
        你是用于数据分析的QueryAssistant。你按照Analyst的指示执行。
        1. 你可以使用许多功能来验证和获取数据。
        2. 你可以使用一个叫做data_query的函数来执行动态查询。
        3. 你查询的数据包含以下列:{st.session_state.df.columns}，这是一个预览:{st.session_state.df.head()}。
        只使用你被提供的功能。 
    """
    )

    analyst = AssistantAgent(
        name="Analyst",
        llm_config=llm_config,
        system_message=f"""
        你是一个Analyst。你不需要询问其他人的意见，按照Planner给定的一个计划进行分析和/或提供所需的信息。
        你可以使用许多工具来验证和获取信息。
        所有的信息都存储在一个DataFrame中，这是一个例子：
        {st.session_state.df.head(2)}
    """
    )
    # 你有一个QueryAssistant来帮助你收集或验证信息。每当你没有信息时，向QueryAssistant询问。

    reporter = AssistantAgent(
        name="Reporter",
        llm_config=llm_config,
        system_message="""
        你是一名Reporter，以洞察力强和良好的语言技巧而知名。你将按照给定的计划生成最终报告。
        Analyst将给你提供所需的信息。
        记得在你的报告中保留每一个可能的表格和引用。
        当所有的事情都完成时，最后回复"TERMINATE"。
        """,
    )

    user_proxy = UserProxyAgent(
        name="Admin",
        human_input_mode="NEVER",
        system_message="""你作为人类将向群聊管理员提供必要的信息。
        如果Analyst或Planner表示他们的任务已经完成，或者用户没有进一步的问题，回复TERMINATE""",
        llm_config=llm_config,
        is_termination_msg=is_termination_msg,
        code_execution_config={
            "last_n_messages": 3,
            "work_dir": "tasks",
            "use_docker": False,
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )

    @user_proxy.register_for_execution()
    # @query_assistant.register_for_llm(description="Use this function to return a list of nearby business buildings around the given one.")
    @analyst.register_for_llm(description="Use this function to return a list of nearby business buildings around the given one.")
    def locate_business_building(location: Annotated[str, "the name of a certain business building"]) -> str:
        buildings = [
            "金虹桥国际中心",
            "SOHO天山广场",
            "兆丰广场",
            "舜元企业发展大厦",
            "尚嘉中心"
        ]
        if location in buildings:
            return str([b for b in buildings if b != location])
        return []

    @user_proxy.register_for_execution()
    # @query_assistant.register_for_llm(description="Use this function to caculate maximum employee number for certain renting unit.")
    @analyst.register_for_llm(description="Use this function to caculate maximum employee number for certain renting unit.")
    def calculate_maximum_employee_by_area(area: Annotated[float, "the area of a renting unit."]) -> int:
        return int(area / 6)

    # @query_assistant.register_for_llm(description="Use this function to query data from DataFrame")
    @analyst.register_for_llm(description="使用这个函数来从DataFrame信息中根据条件查找公司清单")
    @user_proxy.register_for_execution()
    def data_query(query: Annotated[str, "用于df.query()方法的查询条件"]) -> Annotated[str, "Output"]:
        current_df = st.session_state.current_df.query(query)
        st.session_state.current_df = current_df
        return transform2texttable(current_df)

    # @query_assistant.register_for_llm(description="Use this function to filter business buildings")
    @analyst.register_for_llm(description="Use this function to filter business buildings")
    @user_proxy.register_for_execution()
    def filter_business_building(buildings: Annotated[list[str], "The list of names of business buildings in str"]) -> Annotated[str, "Output"]:
        current_df = st.session_state.current_df.query("当前写字楼==@buildings")
        return f"共筛选出{len(current_df)}家公司"

    @user_proxy.register_for_execution()
    # @query_assistant.register_for_llm(description="Use this function to fetch certain company's information.")
    @analyst.register_for_llm(description="Use this function to fetch certain company's information.")
    def company_info(name: Annotated[str, "company name or 公司名称"]) -> str:
        df = st.session_state.df
        df_filtered = df[df["公司名称"] == name]
        return transform2texttable(df_filtered)

    group_chat = autogen.GroupChat(
        admin_name="Admin",
        max_round=30,
        agents=[user_proxy, analyst, rent_planner],
        messages=[],
        allow_repeat_speaker=[analyst,]
    )
    manager = TrackableGroupChatManager(
        name="群聊管理员",
        groupchat=group_chat, llm_config=llm_config)
    result = user_proxy.initiate_chat(
        manager,
        message=f"{message}",
    )
    print(result.cost)


class BingSearch(object):
    def __init__(self) -> None:
        self.sub_key = st.secrets["BING_SEARCH_SUB_KEY"]
        self._headers = {"Ocp-Apim-Subscription-Key": self.sub_key}
        self._params = {"q": "", "textDecorations": True,
                        "textFormat": "HTML", "mkt": "zh-CN"}
        self._search_url = "https://api.bing.microsoft.com/v7.0/news/search"

    def search(self, q, mkt="zh-CN"):
        if not q:
            return []
        self._params["q"] = q
        self._params["mkt"] = mkt
        self._params["category"] = "Business"
        self._params["sortBy"] = "Relevance"
        response = requests.get(
            self._search_url, headers=self._headers, params=self._params)
        response.raise_for_status()
        return response.json()


def chat_on_info(message):
    with st.chat_message("user"):
        st.markdown(message)
        st.session_state.messages.append(ChatMessage("user", message))
    user_proxy = UserProxyAgent(
        name="Admin",
        human_input_mode="NEVER",
        system_message="A human that will provide the necessary information to the group chat manager. Execute the function decided by the QueryAssistant and report the result. Reply TERMINATE when you think everything is done.",
        llm_config=llm_config_gpt3,
        is_termination_msg=is_termination_msg,
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "tasks",
            "use_docker": False,
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )
    analyst = AssistantAgent(
        name="Analyst",
        llm_config=llm_config,
        is_termination_msg=lambda x: x.get("content", "") and x.get(
            "content", "").rstrip().endswith("TERMINATE"),
        system_message="""你是一个十分有用的助理。你可以理解表格信息和json格式的信息。
        用户会问你他想了解的公司，你需要遵循以下指示：
        1. 使用提供给你的工具搜索公司基础信息和公司的新闻。
        2. 分开回答公司信息和新闻。
        3. 确保你所回答的公司信息中至少包含：所属行业，参保人数，联系电话，电子邮箱，最新地址，当前写字楼，单元面积，上次装修工程完成时间。
        4. 确保你所回答的新闻中保留新闻地址引用（url）。
        4. 回答完毕时，在最后回复：TERMINATE
        这对我来说非常重要，你一定要认真回答。
    """
    )

    @user_proxy.register_for_execution()
    @analyst.register_for_llm(description="用这个工具来搜索公司的基础信息")
    def company_info(name: Annotated[str, "公司名称"]) -> str:
        df: pd.DataFrame = st.session_state.df_full
        df_filtered = df[df["公司名称"].str.contains(name)]
        output = process.extract(name, df['公司名称'], limit=1)
        if output:
            company_name = output[0][0]
            df_filtered = df[df["公司名称"] == company_name]
            return transform2texttable(df_filtered)
        return ""

    @user_proxy.register_for_execution()
    @analyst.register_for_llm(description="使用这个工具来搜索公司的新闻")
    def search_company(name: Annotated[str, "公司名称"]) -> str:
        search = BingSearch()
        result = search.search(f"公司最新动态：{name}")
        # json: "value" > 0 > name | url | description
        if values := result.get("value", []):
            return json.dumps(values[:5], indent=4)
        return ""

    chat_result = user_proxy.initiate_chat(
        analyst,
        is_termination_msg=is_termination_msg,
        message=message
    )
    if history := chat_result.chat_history:
        with st.chat_message("assistant"):
            st.markdown(history[-1]['content'])
            st.session_state.messages.append(
                ChatMessage("assistant", history[-1]['content']))
    return None


if __name__ == "__main__":
    initiate_chats("我有一套位于尚嘉中心的办公单元要出租，面积约为2000平米，请帮我找到合适的租户。")
