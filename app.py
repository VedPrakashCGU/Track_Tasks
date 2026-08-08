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

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
db=SQLDatabase.from_uri("sqlite:///my_task.db")
db.run("""CREATE TABLE IF NOT EXISTS tasks 
       (id INTEGER PRIMARY KEY, 
       task TEXT NOT NULL, 
       status TEXT CHECK(status IN ('pending', 'completed','In progress')),
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
       """)


llm=ChatGroq(model="openai/gpt-oss-120b",groq_api_key=os.getenv("Groq_api_key"),streaming=True)
toolkit=SQLDatabaseToolkit(llm=llm,db=db)
tools=toolkit.get_tools()

system_prompt = """
You are a task management assistant that interacts with a SQL database containing a 'tasks' table. 

TASK RULES:
1. Limit SELECT queries to 10 results max with ORDER BY created_at DESC
2. After CREATE/UPDATE/DELETE, confirm with SELECT query
3. If the user requests a list of tasks, present the output in a structured table format to ensure a clean and organized display in the browser."

CRUD OPERATIONS:
    CREATE: INSERT INTO tasks(title, description, status)
    READ: SELECT * FROM tasks WHERE ... LIMIT 10
    UPDATE: UPDATE tasks SET status=? WHERE id=? OR title=?
    DELETE: DELETE FROM tasks WHERE id=? OR title=?

Table schema: id, title, description, status(pending/in_progress/completed), created_at.
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