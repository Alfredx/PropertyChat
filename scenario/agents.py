from dataclasses import dataclass
from typing import Dict

import streamlit as st
from autogen import Agent, AssistantAgent, GroupChatManager, UserProxyAgent


@dataclass
class ChatMessage(object):
    role: str = ""
    content: str = ""


llm_config = {
    "config_list": [
        # {
        #     "model": "gpt-3.5-turbo",
        #     "api_key": st.secrets["OPENAI_API_KEY"],
        #     "api_type": "openai",
        #     "base_url": "https://api.openai.com/v1"
        # },
        {
            "model": "gpt-4-0125-preview",
            "api_key": st.secrets["OPENAI_API_KEY"],
            "api_type": "openai",
            "base_url": "https://api.openai.com/v1"
        }
    ],
    "timeout": 120,
}

llm_config_gpt3 = {
    "config_list": [
        {
            "model": "gpt-3.5-turbo",
            "api_key": st.secrets["OPENAI_API_KEY"],
            "api_type": "openai",
            "base_url": "https://api.openai.com/v1"
        }
    ],
    "timeout": 120,
}


class TrackableAssistantAgent(AssistantAgent):
    def _process_received_message(self, message: Dict | str, sender: Agent, silent: bool):
        if isinstance(message, dict):
            return super()._process_received_message(message, sender, silent)
        with st.chat_message("user"):
            content = f"{message}"
            st.markdown(content)
            st.session_state.messages.append(ChatMessage(
                role="user", content=content))
        return super()._process_received_message(message, sender, silent)


class TrackableUserProxyAgent(UserProxyAgent):
    def _process_received_message(self, message: Dict | str, sender: Agent, silent: bool):
        if isinstance(message, dict):
            return super()._process_received_message(message, sender, silent)
        with st.chat_message("assistant"):
            content = f"{message}"
            st.markdown(content)
            st.session_state.messages.append(ChatMessage(
                role="assistant", content=content))
        return super()._process_received_message(message, sender, silent)



class TrackableGroupChatManager(GroupChatManager):
    def _process_received_message(self, message: Dict | str, sender: Agent, silent: bool):
        if isinstance(message, dict):
            if message.get("role", "") != 'user':
                return super()._process_received_message(message, sender, silent)
        
        self.chat_message_dialouge(message, sender)
        return super()._process_received_message(message, sender, silent)
    
    def chat_message_tool(self, message: Dict | str, sender: Agent):
        pass

    def chat_message_dialouge(self, message: Dict | str, sender: Agent):
        bot_role = "assistant"
        if sender.name == self._groupchat.admin_name:
            bot_role = "user"
        with st.chat_message(bot_role):
            st.markdown(f"{message}")
            st.session_state.messages.append(
                ChatMessage(role=bot_role, content=message))