#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
维标管理工具主程序入口
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 导入必要的模块
from config.settings import load_settings
from utils.logger import setup_logger
from api.client import APIClient, MockAPIClient
from services.document_service import DocumentService
from services.knowledge_service import KnowledgeService
from services.query_service import QueryService
import gradio as gr

# 初始化日志
logger = setup_logger(__name__)

def main():
    """主函数"""
    try:
        # 加载配置
        settings = load_settings()
        logger.info("配置加载成功")

        # 初始化API客户端
        # 使用MockAPIClient进行测试，实际部署时可替换为APIClient
        api_client = MockAPIClient(settings)
        logger.info("API客户端初始化成功")

        # 初始化服务
        document_service = DocumentService(settings, api_client)
        knowledge_service = KnowledgeService(settings, api_client)
        query_service = QueryService(settings, api_client)
        logger.info("服务初始化成功")

        # 创建Gradio界面
        create_interface(document_service, knowledge_service, query_service)

    except Exception as e:
        logger.error(f"程序启动失败: {str(e)}")
        raise

def create_interface(document_service, knowledge_service, query_service):
    """创建Gradio用户界面"""
    with gr.Blocks(title="维标管理工具") as app:
        gr.Markdown("# 维标管理工具")
        gr.Markdown("## 文档管理与知识图谱系统")

        with gr.Tabs():
            # 文档管理标签页
            with gr.TabItem("文档管理"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 文档上传")
                        file_upload = gr.File(
                            file_types=[".doc", ".docx"],
                            file_count="multiple",
                            label="上传文档"
                        )
                        upload_btn = gr.Button("上传文档")
                        status_display = gr.Textbox(label="上传状态", interactive=False)

                    with gr.Column():
                        gr.Markdown("### 文档列表")
                        doc_list = gr.Dataframe(
                            headers=["文档名称", "上传时间", "文件大小", "处理状态", "最后处理时间"],
                            datatype=["str", "str", "str", "str", "str"],
                            label="文档列表",
                            interactive=False
                        )
                        refresh_btn = gr.Button("刷新列表")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 文档操作")
                        doc_select = gr.Dropdown(label="选择文档", choices=[])
                        preview_btn = gr.Button("预览")
                        rename_btn = gr.Button("重命名")
                        delete_btn = gr.Button("删除")

                    with gr.Column():
                        gr.Markdown("### 处理控制")
                        process_btn = gr.Button("开始处理")
                        reset_btn = gr.Button("重置状态")
                        progress_bar = gr.Progress()

            # 知识抽取标签页
            with gr.TabItem("知识抽取"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 抽取配置")
                        model_select = gr.Dropdown(
                            label="选择模型",
                            choices=["DeepSeek-R1", "DeepSeek-V2", "自定义模型"]
                        )
                        concurrency_slider = gr.Slider(
                            label="并发数量",
                            minimum=1,
                            maximum=10,
                            value=3,
                            step=1
                        )
                        timeout_slider = gr.Slider(
                            label="超时时间(秒)",
                            minimum=30,
                            maximum=300,
                            value=120,
                            step=10
                        )
                        config_btn = gr.Button("应用配置")

                    with gr.Column():
                        gr.Markdown("### 处理状态")
                        status_display2 = gr.Textbox(label="处理状态", interactive=False)
                        progress_bar2 = gr.Progress()
                        result_display = gr.JSON(label="抽取结果")

                with gr.Row():
                    process_btn2 = gr.Button("批量处理")
                    stop_btn = gr.Button("停止处理")

            # 查询与可视化标签页
            with gr.TabItem("查询与可视化"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 自然语言查询")
                        query_input = gr.Textbox(
                            label="输入查询",
                            placeholder="例如：查找与冷却皮带相关的维修标准",
                            lines=3
                        )
                        query_btn = gr.Button("执行查询")
                        query_history = gr.Dataframe(
                            headers=["查询内容", "时间"],
                            datatype=["str", "str"],
                            label="查询历史",
                            interactive=False
                        )

                    with gr.Column():
                        gr.Markdown("### 可视化结果")
                        graph_display = gr.HTML()
                        details_display = gr.JSON(label="详细信息")

                with gr.Row():
                    export_btn = gr.Button("导出结果")
                    clear_btn = gr.Button("清除历史")

    # 启动应用
    app.launch()

if __name__ == "__main__":
    main()
