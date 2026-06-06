import streamlit as st

st.title("邮件功能测试")

if 'show_email' not in st.session_state:
    st.session_state.show_email = False

st.write(f"当前 show_email 状态: {st.session_state.show_email}")

if st.button("📧 测试发送报告"):
    st.session_state.show_email = True
    st.success("按钮被点击了！show_email 已设置为 True")
    st.rerun()

if st.session_state.show_email:
    st.markdown("---")
    st.markdown("## 邮件发送界面")
    email = st.text_input("邮箱地址")
    if st.button("发送"):
        st.success(f"演示: 发送报告到 {email}")
        st.session_state.show_email = False
        st.rerun()
    if st.button("关闭"):
        st.session_state.show_email = False
        st.rerun()

st.info("点击上面的按钮测试")
