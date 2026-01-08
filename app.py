"""
AI 概念时空演化图谱 - Streamlit (物理引擎版)

技术栈: Streamlit + streamlit-agraph
特点: 节点可拖拽、带有弹性和物理斥力
"""

import streamlit as st
import pandas as pd
import json
import networkx as nx
# 1. 引入新库
from streamlit_agraph import agraph, Node, Edge, Config

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="AI 概念时空图谱",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== 配置常量 ====================
COLOR_MAP = {
    "Natural Language Processing": "#00D084",
    "Computer Vision": "#FF6B6B",
    "Graph & Network": "#4ECDC4",
    "Machine Learning": "#A78BFA",
    "Robotics & Control": "#FF9F40",
    "AI in Healthcare": "#FF6EC7",
    "Explainable & Trustworthy AI": "#FFD93D", # 原 Explainable AI
    "Optimization & Theory": "#8D99AE"         # 新增类别，建议用灰蓝色
}
DEFAULT_COLOR = "#CCCCCC"

# ==================== 数据加载 (保持不变) ====================
@st.cache_data
def load_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df['related_list'] = df['related_concepts'].apply(
        lambda x: json.loads(x) if pd.notna(x) else []
    )
    return df

# ==================== 主应用 ====================
def main():
    try:
        df = load_data('ai_yearly_data.csv') 
    except FileNotFoundError:
        st.error("数据文件丢失！确保 ai_yearly_data.csv 在同级目录下。")
        return

    # ========== [修改开始]：计算全局最大值与设置大小范围 ==========
    # 目的：为了让不同年份的节点大小具有可比性，必须基于所有年份的数据（全局）进行归一化。
    # 这样，2015年的节点（发文少）会比2025年的节点（发文多）明显更小。
    
    global_max = df['works_count'].max() if not df.empty else 1000
    
    # 定义节点显示的像素大小范围
    # MIN_NODE_SIZE: 最小节点大小（即使数值很小也至少显示这么大）
    # MAX_NODE_SIZE: 最大节点大小（对应全局最大发文量）
    MIN_NODE_SIZE = 10 
    MAX_NODE_SIZE = 60 # 调大上限，以增强视觉冲击力
    # ========== [修改结束] =====================================

    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🌌 AI 概念网络图谱")
    with col2:
        year = st.selectbox("选择年份", options=list(range(2015, 2026)), index=10)

    # ========== [修改]：更新文案提示 ==========
    st.caption(f"当前展示 {year} 年数据。")

    # --- 数据筛选 ---
    df_year = df[df['year'] == year]
    if df_year.empty:
        st.warning(f"{year} 年无数据")
        return

    # --- 2. 转换数据为 agraph 格式 ---    
    nodes = []
    edges = []
    added_node_ids = set()

    # [移除] 原先获取当年最大值的代码： max_works = df_year['works_count'].max() ...

    # A. 添加核心节点 (Top 100)
    for _, row in df_year.iterrows():
        if "Computer Science and Engineering" in row['display_name']:
            continue # 跳过这个超级节点
        
        node_id = row['id']
        category = row['category']
        val = row['works_count']
        
        # ========== [修改开始]：使用全局线性归一化计算大小 ==========
        # 公式：最小尺寸 + (当前值 / 全局最大值) * (尺寸范围差值)
        # 效果：真实反映数量的倍数关系。
        size = MIN_NODE_SIZE + (val / global_max) * (MAX_NODE_SIZE - MIN_NODE_SIZE)
        # ========== [修改结束] =====================================
        
        nodes.append(Node(
            id=node_id,
            label=row['display_name'],
            size=size,
            shape="dot",
            color=COLOR_MAP.get(category, DEFAULT_COLOR),
            # [修改]：Tooltip 中增加全局最大值的参考信息
            title=f"Node: {row['display_name']}\nCat: {category}\nWorks: {val}"
        ))
        added_node_ids.add(node_id)

    # B. 添加边和卫星节点
    for _, row in df_year.iterrows():
        source = row['id']
        related_list = row['related_list']
        
        for sibling in related_list:

            if isinstance(sibling, dict):
                target = sibling.get('id')
                target_name = sibling.get('display_name', 'Unknown')
                target_cat = sibling.get('category', 'Other')
            else:
                target = sibling
                target_name = "Unknown" # 如果只有ID，没有名字
                target_cat = "Other"

            if not target: continue

            # 如果目标是卫星节点（不在 Top 100 中），且还没添加过
            if target not in added_node_ids:
                nodes.append(Node(
                    id=target,
                    label=target_name, # 如果数据源里只有ID，这里可能无法显示正确名字
                    size=10, # 卫星节点较小，保持固定大小 10
                    shape="dot",
                    color="#555555", # 灰色
                    title="Related Concept"
                ))
                added_node_ids.add(target)

            # 添加连线
            edges.append(Edge(
                source=source,
                target=target,
                color="#555555", # 线条颜色
                width=1
            ))

    # --- 3. 配置物理引擎 ---
    config = Config(
        width="100%",
        height=750,
        directed=False, 
        physics=True, # 开启物理引擎
        hierarchy=False,
        # 详细的物理参数调整
        physicsOptions={
            "forceAtlas2Based": {
                "gravitationalConstant": -50, # 斥力，负数越大排斥越强
                "centralGravity": 0.005,      # 向心力，把节点拉向中心
                "springLength": 100,          # 弹簧长度
                "springConstant": 0.08,       # 弹簧弹性
                "damping": 0.4                # 阻尼，越小晃动越久
            },
            "minVelocity": 0.75,
            "solver": "forceAtlas2Based"      # 求解器模型
        },
        nodeHighlightBehavior=True,
        highlightColor="#F7A072", # 选中时的高亮颜色
        collapsible=False
    )

    # --- 4. 渲染图表 ---
    # return_value 可以获取用户点击了哪个节点
    return_value = agraph(nodes=nodes, edges=edges, config=config)

if __name__ == "__main__":
    main()