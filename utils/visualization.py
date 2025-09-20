"""
知识图谱可视化工具
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from models.knowledge import KnowledgeGraph, Entity, Relation
from utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeGraphVisualizer:
    """知识图谱可视化器"""
    
    def __init__(self):
        # 定义实体类型颜色映射
        self.entity_colors = {
            'equipment': '#FF6B6B',      # 红色 - 设备
            'component': '#4ECDC4',      # 青色 - 部件
            'procedure': '#45B7D1',      # 蓝色 - 工序
            'standard': '#96CEB4',       # 绿色 - 标准
            'material': '#FFEAA7',       # 黄色 - 材料
            'condition': '#DDA0DD',      # 紫色 - 条件
            'error': '#FF7675',          # 浅红色 - 错误
            'cause': '#FD79A8',          # 粉色 - 原因
            'solution': '#00B894',       # 深绿色 - 解决方案
            'maintenance': '#74B9FF',    # 浅蓝色 - 维修
            'inspection': '#A29BFE',     # 淡紫色 - 检查
            'other': '#B2BEC3'           # 灰色 - 其他
        }
        
        # 定义关系类型颜色映射
        self.relation_colors = {
            'part_of': '#636e72',        # 深灰色
            'used_in': '#2d3436',        # 黑色
            'related_to': '#74b9ff',     # 蓝色
            'causes': '#e17055',         # 橙红色
            'is_solution_for': '#00b894', # 绿色
            'requires': '#fdcb6e',       # 黄色
            'results_in': '#e84393',     # 粉色
            'checked_by': '#a29bfe',     # 紫色
            'maintained_by': '#fd79a8',  # 浅粉色
            'follows': '#55a3ff',        # 浅蓝色
            'depends_on': '#ff7675'      # 浅红色
        }

    def create_network_graph(
        self, 
        knowledge_graph: KnowledgeGraph,
        layout: str = "spring",
        show_labels: bool = True,
        node_size_factor: float = 1.0,
        edge_width_factor: float = 1.0
    ) -> go.Figure:
        """
        创建网络图可视化
        
        Args:
            knowledge_graph: 知识图谱对象
            layout: 布局算法 ("spring", "circular", "kamada_kawai", "random")
            show_labels: 是否显示节点标签
            node_size_factor: 节点大小因子
            edge_width_factor: 边宽度因子
            
        Returns:
            Plotly图形对象
        """
        try:
            # 创建NetworkX图
            G = self._build_networkx_graph(knowledge_graph)
            
            if len(G.nodes()) == 0:
                return self._create_empty_graph("知识图谱为空")
            
            # 计算布局
            pos = self._calculate_layout(G, layout)
            
            # 创建Plotly图形
            fig = go.Figure()
            
            # 添加边
            self._add_edges_to_plot(fig, G, pos, edge_width_factor)
            
            # 添加节点
            self._add_nodes_to_plot(fig, G, pos, show_labels, node_size_factor)
            
            # 设置布局
            fig.update_layout(
                title=f"知识图谱可视化 - {len(G.nodes())} 个实体，{len(G.edges())} 个关系",
                showlegend=True,
                hovermode='closest',
                margin=dict(b=20,l=5,r=5,t=40),
                annotations=[
                    dict(
                        text="点击节点查看详情，拖拽可移动视图",
                        showarrow=False,
                        xref="paper", yref="paper",
                        x=0.005, y=-0.002,
                        xanchor='left', yanchor='bottom',
                        font=dict(size=12, color="gray")
                    )
                ],
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"创建网络图失败: {str(e)}")
            return self._create_empty_graph(f"可视化失败: {str(e)}")
    
    def create_entity_distribution_chart(self, knowledge_graph: KnowledgeGraph) -> go.Figure:
        """
        创建实体类型分布图
        
        Args:
            knowledge_graph: 知识图谱对象
            
        Returns:
            Plotly图形对象
        """
        try:
            # 统计实体类型分布
            entity_counts = {}
            for entity in knowledge_graph.entities:
                entity_type = entity.type.value
                entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
            
            if not entity_counts:
                return self._create_empty_graph("暂无实体数据")
            
            # 创建饼图
            fig = go.Figure(data=[go.Pie(
                labels=list(entity_counts.keys()),
                values=list(entity_counts.values()),
                hole=0.3,
                marker=dict(colors=[self.entity_colors.get(t, '#B2BEC3') for t in entity_counts.keys()])
            )])
            
            fig.update_layout(
                title="实体类型分布",
                annotations=[dict(text='实体<br>分布', x=0.5, y=0.5, font_size=20, showarrow=False)]
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"创建实体分布图失败: {str(e)}")
            return self._create_empty_graph(f"创建分布图失败: {str(e)}")
    
    def create_relation_distribution_chart(self, knowledge_graph: KnowledgeGraph) -> go.Figure:
        """
        创建关系类型分布图
        
        Args:
            knowledge_graph: 知识图谱对象
            
        Returns:
            Plotly图形对象
        """
        try:
            # 统计关系类型分布
            relation_counts = {}
            for relation in knowledge_graph.relations:
                relation_type = relation.type.value
                relation_counts[relation_type] = relation_counts.get(relation_type, 0) + 1
            
            if not relation_counts:
                return self._create_empty_graph("暂无关系数据")
            
            # 创建条形图
            fig = go.Figure(data=[go.Bar(
                x=list(relation_counts.keys()),
                y=list(relation_counts.values()),
                marker=dict(color=[self.relation_colors.get(t, '#B2BEC3') for t in relation_counts.keys()])
            )])
            
            fig.update_layout(
                title="关系类型分布",
                xaxis_title="关系类型",
                yaxis_title="数量",
                xaxis_tickangle=-45
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"创建关系分布图失败: {str(e)}")
            return self._create_empty_graph(f"创建分布图失败: {str(e)}")
    
    def _build_networkx_graph(self, knowledge_graph: KnowledgeGraph) -> nx.Graph:
        """构建NetworkX图"""
        G = nx.Graph()
        
        # 添加节点
        for entity in knowledge_graph.entities:
            G.add_node(
                entity.id,
                name=entity.name,
                type=entity.type.value,
                description=entity.description or "",
                properties=entity.properties or {}
            )
        
        # 添加边
        for relation in knowledge_graph.relations:
            if G.has_node(relation.source) and G.has_node(relation.target):
                G.add_edge(
                    relation.source,
                    relation.target,
                    type=relation.type.value,
                    description=relation.description or "",
                    properties=relation.properties or {}
                )
        
        return G
    
    def _calculate_layout(self, G: nx.Graph, layout: str) -> Dict[str, Tuple[float, float]]:
        """计算图布局"""
        if layout == "spring":
            return nx.spring_layout(G, k=1, iterations=50)
        elif layout == "circular":
            return nx.circular_layout(G)
        elif layout == "kamada_kawai":
            return nx.kamada_kawai_layout(G)
        elif layout == "random":
            return nx.random_layout(G)
        else:
            return nx.spring_layout(G, k=1, iterations=50)
    
    def _add_edges_to_plot(
        self, 
        fig: go.Figure, 
        G: nx.Graph, 
        pos: Dict[str, Tuple[float, float]], 
        width_factor: float
    ):
        """添加边到图形"""
        edge_x = []
        edge_y = []
        edge_info = []
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
            # 获取边信息
            edge_data = G.edges[edge]
            edge_info.append(f"关系: {edge_data.get('type', 'unknown')}")
        
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2*width_factor, color='#888'),
            hoverinfo='none',
            mode='lines',
            name="关系"
        ))
    
    def _add_nodes_to_plot(
        self, 
        fig: go.Figure, 
        G: nx.Graph, 
        pos: Dict[str, Tuple[float, float]], 
        show_labels: bool, 
        size_factor: float
    ):
        """添加节点到图形"""
        # 按类型分组节点
        node_groups = {}
        for node in G.nodes():
            node_data = G.nodes[node]
            node_type = node_data.get('type', 'other')
            
            if node_type not in node_groups:
                node_groups[node_type] = {
                    'x': [], 'y': [], 'text': [], 'hovertext': [], 'ids': []
                }
            
            x, y = pos[node]
            node_groups[node_type]['x'].append(x)
            node_groups[node_type]['y'].append(y)
            node_groups[node_type]['text'].append(node_data.get('name', node))
            node_groups[node_type]['ids'].append(node)
            
            # 构建悬停信息
            hover_text = f"<b>{node_data.get('name', node)}</b><br>"
            hover_text += f"类型: {node_type}<br>"
            if node_data.get('description'):
                hover_text += f"描述: {node_data['description']}<br>"
            node_groups[node_type]['hovertext'].append(hover_text)
        
        # 为每种类型添加散点图
        for node_type, data in node_groups.items():
            fig.add_trace(go.Scatter(
                x=data['x'], y=data['y'],
                mode='markers+text' if show_labels else 'markers',
                text=data['text'] if show_labels else None,
                textposition="middle center",
                hovertext=data['hovertext'],
                hoverinfo='text',
                marker=dict(
                    size=20*size_factor,
                    color=self.entity_colors.get(node_type, '#B2BEC3'),
                    line=dict(width=2, color='white')
                ),
                name=f"{node_type} ({len(data['x'])})"
            ))
    
    def _create_empty_graph(self, message: str) -> go.Figure:
        """创建空图形"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(
            title="知识图谱可视化",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
        return fig


def create_query_result_visualization(query_results: List[Dict[str, Any]]) -> go.Figure:
    """
    为查询结果创建可视化
    
    Args:
        query_results: 查询结果列表
        
    Returns:
        Plotly图形对象
    """
    visualizer = KnowledgeGraphVisualizer()
    
    if not query_results:
        return visualizer._create_empty_graph("查询结果为空")
    
    try:
        # 从查询结果构建临时知识图谱
        entities = []
        relations = []
        
        for result in query_results:
            if result["type"] == "entity":
                # 创建临时实体对象用于可视化
                entity_data = {
                    "id": result["id"],
                    "name": result["name"],
                    "type": result["type_value"],
                    "description": result.get("description", ""),
                    "properties": result.get("properties", {})
                }
                entities.append(entity_data)
            elif result["type"] == "relation":
                # 创建临时关系对象用于可视化
                relation_data = {
                    "id": result.get("id", f"{result['source']}-{result['target']}"),
                    "source": result["source"],
                    "target": result["target"],
                    "type": result["type_value"],
                    "description": result.get("description", ""),
                    "properties": result.get("properties", {})
                }
                relations.append(relation_data)
        
        # 创建简化的网络图
        fig = go.Figure()
        
        if entities:
            # 简单布局：实体排列成圆形
            n_entities = len(entities)
            angles = np.linspace(0, 2*np.pi, n_entities, endpoint=False)
            
            entity_x = [np.cos(angle) for angle in angles]
            entity_y = [np.sin(angle) for angle in angles]
            entity_names = [entity["name"] for entity in entities]
            entity_types = [entity["type"] for entity in entities]
            
            # 按类型分组显示
            type_groups = {}
            for i, entity in enumerate(entities):
                entity_type = entity["type"]
                if entity_type not in type_groups:
                    type_groups[entity_type] = {
                        'x': [], 'y': [], 'text': [], 'hovertext': []
                    }
                
                type_groups[entity_type]['x'].append(entity_x[i])
                type_groups[entity_type]['y'].append(entity_y[i])
                type_groups[entity_type]['text'].append(entity["name"])
                
                hover_text = f"<b>{entity['name']}</b><br>类型: {entity_type}"
                if entity.get("description"):
                    hover_text += f"<br>描述: {entity['description']}"
                type_groups[entity_type]['hovertext'].append(hover_text)
            
            # 添加实体节点
            for entity_type, data in type_groups.items():
                fig.add_trace(go.Scatter(
                    x=data['x'], y=data['y'],
                    mode='markers+text',
                    text=data['text'],
                    textposition="middle center",
                    hovertext=data['hovertext'],
                    hoverinfo='text',
                    marker=dict(
                        size=30,
                        color=visualizer.entity_colors.get(entity_type, '#B2BEC3'),
                        line=dict(width=2, color='white')
                    ),
                    name=f"{entity_type} ({len(data['x'])})"
                ))
        
        # 添加关系边（如果有）
        if relations and entities:
            edge_x = []
            edge_y = []
            
            # 创建实体ID到位置的映射
            entity_positions = {entity["id"]: (entity_x[i], entity_y[i]) 
                              for i, entity in enumerate(entities)}
            
            for relation in relations:
                source_pos = entity_positions.get(relation["source"])
                target_pos = entity_positions.get(relation["target"])
                
                if source_pos and target_pos:
                    edge_x.extend([source_pos[0], target_pos[0], None])
                    edge_y.extend([source_pos[1], target_pos[1], None])
            
            if edge_x:
                fig.add_trace(go.Scatter(
                    x=edge_x, y=edge_y,
                    line=dict(width=2, color='#888'),
                    hoverinfo='none',
                    mode='lines',
                    name="关系",
                    showlegend=True
                ))
        
        fig.update_layout(
            title=f"查询结果可视化 - {len(entities)} 个实体，{len(relations)} 个关系",
            showlegend=True,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=500
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"创建查询结果可视化失败: {str(e)}")
        return visualizer._create_empty_graph(f"可视化失败: {str(e)}")

