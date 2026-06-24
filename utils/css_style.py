"""
全局 CSS 样式注入模块
"""
import streamlit as st


def inject_custom_css():
    """注入看板全局自定义 CSS 样式"""
    st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        text-align: center;
        color: #2c3e50;
        padding: 10px 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .status-bar {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 20px;
        padding: 8px;
        background: #f8f9fa;
        border-radius: 8px;
        margin: 5px 0 15px 0;
    }

    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #2ecc71;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.3; }
        100% { opacity: 1; }
    }

    .metric-card {
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: transform 0.3s;
    }

    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
    }

    .metric-label {
        font-size: 0.95rem;
        opacity: 0.9;
        margin-top: 5px;
    }

    .metric-delta {
        font-size: 0.8rem;
        opacity: 0.8;
        margin-top: 3px;
    }

    .custom-divider {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #bdc3c7, transparent);
        margin: 20px 0;
    }

    .advice-box-low {
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #2ecc71;
        background: #eafaf1;
        margin: 10px 0;
    }

    .advice-box-mid {
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #f39c12;
        background: #fef9e7;
        margin: 10px 0;
    }

    .advice-box-high {
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #e74c3c;
        background: #fdedec;
        margin: 10px 0;
    }

    .footer {
        text-align: center;
        padding: 20px;
        color: #bdc3c7;
        font-size: 0.8rem;
        border-top: 1px solid #ecf0f1;
        margin-top: 30px;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)
