import random
import time
from dataclasses import dataclass

import requests
import streamlit as st
from openai import OpenAI
import pandas as pd
from scripts.transform import transform2texttable

st.title("Property Chat")

@dataclass
class ChatMessage(object):
    role: str = ""
    content: str = ""


def get_response(prompt):
    def response_generator():
        response = random.choice(
            [
                "Hello there! How can I assist you today?",
                "Hi, human! Is there anything I can help you with?",
                "Do you need help?",
                f"Your prompt is {prompt}"
            ]
        )
        for word in response.split():
            yield word + " "
            time.sleep(0.05)
    return response_generator()


client = OpenAI(**{
    "api_key": st.secrets["OPENAI_API_KEY"],
    "base_url": st.secrets["OPENAI_BASE_URL"]
})

if "messages" not in st.session_state:
    st.session_state.messages: list[ChatMessage] = []

if "file_record" not in st.session_state:
    st.session_state.file_record: pd.DataFrame = None

if "file_processing" not in st.session_state:
    st.session_state.file_processing: bool = False

if "llm_model" not in st.session_state:
    st.session_state.llm_model = "gpt-4-turbo"


for message in st.session_state.messages:
    with st.chat_message(message.role):
        st.markdown(message.content)

if prompt := st.chat_input("你可以这么问我：哪几家公司最有可能要更换办公室？"):
    st.chat_message("user").markdown(prompt)
    if (df := st.session_state.file_record) is not None:
        st.session_state.messages.append(ChatMessage(role="user", content=prompt))
        # print(transform2texttable(df[:50]))
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model=st.session_state.llm_model,
                messages= [{"role": "system", "content": f"表格内容如下: \n{transform2texttable(df[:100])}\n\n" + 
                            "首先根据表格内容中的“招聘岗位增幅（%）”一列筛选出增幅最大的前10家公司，然后根据筛选结果回答用户问题。"+
                            "如果给出的答案包含具体的公司，那么也要从表格中一起带出公司联系电话和邮箱。do it step by step."},] +
                [
                    {"role": m.role, "content": m.content}
                    for m in st.session_state.messages[-1:]
                ],
                stream=True,
            )
            response = st.write_stream(stream)
    # with st.chat_message("assistant"):
    #     response = f"Echo {prompt}"
    #     st.markdown(response)

            st.session_state.messages.append(ChatMessage("assistant", response))
    else:
        with st.chat_message("assistant"):
            if file_processing := st.session_state.file_processing:
                st.write("[正在预处理数据文件，请稍候...]")
            else:
                st.write("在我回答您的问题之前，请在侧边栏上传数据文件。\n\n例如《2023年12月陆家嘴核心区域.xlsx》")

with st.sidebar:
    if uploaded_file := st.file_uploader("Choose a file", type=["xlsx", "xls"]):
        st.session_state.file_processing = True
        df = pd.read_excel(uploaded_file)
        st.session_state.file_record = df
        st.session_state.file_processing = False

    llm_model = st.radio("大语言模型", ["gpt-4-turbo", "gpt-3.5-turbo"])
    st.session_state.llm_model = llm_model

