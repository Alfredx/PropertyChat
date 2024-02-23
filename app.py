import pandas as pd
import streamlit as st

from scenario.agents import ChatMessage
from scenario.intention_checkbot import intention_check
from scenario.rent import chat_on_info
from scenario.rent_step_by_step import rent_step_by_step

st.set_page_config(page_title="Property Chat", layout="wide")


if "messages" not in st.session_state:
    st.session_state.messages = []

if "df" not in st.session_state:
    df = pd.read_excel("zjw_based_companies_slim.xlsx")
    st.session_state.df = df
    st.session_state.current_df = df
    df_full = pd.read_excel("zjw_based_companies.xlsx")
    st.session_state.df_full = df_full


if "file_processing" not in st.session_state:
    st.session_state.file_processing: bool = False

if "llm_model" not in st.session_state:
    st.session_state.llm_model = "gpt-4-turbo"

if "new_user_input" not in st.session_state:
    st.session_state.new_user_input = False


for message in st.session_state.messages:
    with st.chat_message(message.role):
        st.markdown(message.content)

initial_message = """您好，我是您专属的出租顾问。您可以这么问我：

如：我有一套位于尚嘉中心的办公单元要出租，面积共2000平米，请帮我找到合适的租户。

或者您也可以这么问：
                     
告诉我有关乐歌信息科技（上海）有限公司这家公司的更多信息。"""
with st.chat_message("assistant"):
    st.markdown(initial_message)

if prompt := st.chat_input(":>", key="chat_input"):

    # st.chat_message("user").markdown(prompt)
    # st.session_state.messages.append(ChatMessage(role="user", content=prompt))
    intention = intention_check(prompt)
    if intention == "RENT":
        st.session_state.current_df = st.session_state.df
        # initiate_chats(prompt)
        rent_step_by_step(prompt)
    elif intention == "INFO":
        chat_on_info(prompt)
    else:
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append(
            ChatMessage(role="user", content=prompt))
        with st.chat_message("assistant"):
            st.markdown(initial_message)
            st.session_state.messages.append(ChatMessage(
                role="assistant", content=initial_message))


# with st.sidebar:
#     if uploaded_file := st.file_uploader("Choose a file", type=["xlsx", "xls"]):
#         st.session_state.file_processing = True
#         df = pd.read_excel(uploaded_file)
#         st.session_state.file_record = df
#         st.session_state.file_processing = False

#     llm_model = st.radio("大语言模型", ["gpt-4-turbo", "gpt-3.5-turbo"])
#     st.session_state.llm_model = llm_model
