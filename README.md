# 🍎 果园病虫害风险预警与防控可视化看板

基于 **LightGBM + SHAP** 的智能预警系统，企业级 Streamlit 可视化大屏。

## 🚀 在线访问

🔗 **[点击打开看板](https://YOUR-APP.streamlit.app)** （部署后替换此链接）

## 📊 功能特性

- 🗺️ 空间风险热力图与地块级详情
- 📈 时间趋势分析与防控窗口判定
- 🔬 SHAP 特征贡献可解释性分析
- 🎯 POSI 精准防控策略推荐
- 📋 三级差异化防控响应体系
- 🔄 模拟实时数据刷新

## 🛠️ 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📁 项目结构

```
├── app.py              # Streamlit 主应用
├── config.py           # 全局配置
├── requirements.txt    # Python 依赖
├── utils/
│   ├── data_loader.py  # 数据加载与缓存
│   └── charts.py       # Plotly 图表组件
└── output/             # 模型产出数据
    ├── 1.预处理及特征工程结果/
    ├── 2.低中高/
    └── 3.分区域分时段/
```

## 📄 许可

仅供研究与学习使用。
