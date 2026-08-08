from dotenv import load_dotenv
load_dotenv()
import os
from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from langchain.agents import create_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.checkpoint.memory import InMemorySaver
import streamlit as st
import uuid

db=SQLDatabase.from_uri("sqlite:///my_task.db")
db.run("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    task TEXT NOT NULL,
    status TEXT CHECK(status IN ('pending', 'completed', 'In progress')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")


llm=ChatGroq(model="openai/gpt-oss-120b",groq_api_key=os.getenv("Groq_api_key"),streaming=True)
toolkit=SQLDatabaseToolkit(llm=llm,db=db)
tools=toolkit.get_tools()
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "thread_id" not in st.session_state:
    st.session_state.thread_id = st.session_state.user_id
system_prompt = f"""
You are a task management assistant.

The current user's ID is:

{st.session_state.user_id}

Database table:

tasks(
    id,
    user_id,
    task,
    status,
    created_at
)

IMPORTANT RULES:

1. Every task belongs to a user.
2. ALWAYS use the current user's ID when querying tasks.
3. Never show another user's tasks.
4. When inserting a task, use:
   user_id = '{st.session_state.user_id}'
5. SELECT queries must contain:
   WHERE user_id = '{st.session_state.user_id}'
6. Limit SELECT results to 10.
7. Order results by created_at DESC.
8. After INSERT, UPDATE, or DELETE, verify the operation with SELECT.
9. Never modify another user's tasks.
"""
st.subheader("🤖 Task Management Assistant")
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    st.chat_message(message["role"]).markdown(message["content"])
@st.cache_resource
def createAgent():
    memory=InMemorySaver()
    agent=create_agent(model=llm,tools=tools,system_prompt=system_prompt,checkpointer=memory)
    return agent
agent=createAgent()
prompt=st.chat_input("Track your tasks here...")
if prompt:
    st.session_state.messages.append({"role":"user","content":prompt})
    st.chat_message("user").markdown(prompt)
    with st.chat_message("ai"):
        with st.spinner(" Thoda Wait karle....."):
            res=agent.invoke(
                {"messages":[{"role":"user","content":prompt}]},
                {"configurable":{"thread_id":st.session_state.thread_id }})
            result=res["messages"][-1].content
            st.session_state.messages.append({"role":"ai","content":result})
            st.markdown(result)