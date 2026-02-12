import streamlit as st
from langchain_ollama import OllamaLLM
import time

# Streamlit title
st.title("Hackathon Ready!")

# Add a button to trigger the query
if st.button("Ask the model"):
    try:
        with st.spinner("Connecting to Ollama..."):
            # Initialize the Ollama model
            llm = OllamaLLM(model="deepseek-coder-v2:lite")
            
            # Ask the model a question
            question = "Are you ready for a hackathon?"
            st.write(f"Question: {question}")
            
            with st.spinner("Getting response..."):
                response = llm.invoke(question)
                st.write(f"Response: {response}")
                
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.write("Make sure Ollama is running and the model 'deepseek-coder-v2:lite' is available.")
else:
    st.write("Click the button to ask the model a question.")