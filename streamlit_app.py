import streamlit as st

st.set_page_config(page_title="HW Manager", page_icon="📚", layout="centered")

def home():
    st.title("Ryann's IST488 Homework!")
    st.write("Welcome! Use sidebar to navigate homework assignments")
# Pages
home_page = st.Page(home, title="Home", default=True)
hw1_page  = st.Page("HW/hw1.py", title="Homework 1")
hw2_page  = st.Page("HW/hw2.py", title="Homework 2")
hw3_page  = st.Page("HW/hw3.py", title="Homework 3")

# Navigation
pg = st.navigation([home_page, hw1_page, hw2_page])
pg.run()