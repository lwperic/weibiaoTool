# !/user/bin/env python3
# -*- coding: utf-8 -*-
"""
文档模型
"""
"""
维标管理工具主函数
"""

# 强制设置编码
import sys
import os
import locale

# 设置环境变量
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'zh_CN.UTF-8'
os.environ['LC_ALL'] = 'zh_CN.UTF-8'

# 设置系统编码
if sys.platform.startswith('win'):
    try:
        locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'Chinese_China.UTF-8')
        except:
            pass

# 设置标准输出编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import gradio as gr
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import settings, load_settings
from services.document_service import DocumentService
from services.knowledge_service import KnowledgeService
from services.query_service import QueryService
from services.graph_service import GraphService
from api.client import MockAPIClient
from utils.api_utils import DeepSeekClient
from utils.logger import get_logger

# 初始化日志
logger = get_logger(__name__)

def create_app():
    """创建应用"""
    # 加载配置
    settings = load_settings()
    logger.info("配置加载成功")

    # 创建API客户端
    try:
        # 尝试使用真实的DeepSeek客户端
        api_client = DeepSeekClient(settings)
        logger.info("使用DeepSeek API客户端")
    except Exception as e:
        # 如果DeepSeek API不可用，回退到Mock客户端
        logger.warning(f"无法初始化DeepSeek客户端: {e}，使用Mock客户端")
        api_client = MockAPIClient(settings)

    # 创建服务
    document_service = DocumentService(settings, api_client)
    knowledge_service = KnowledgeService(settings, api_client)
    query_service = QueryService(settings, api_client)
    graph_service = GraphService(settings)

    # 定义应用布局
    with gr.Blocks(title="维标管理工具") as app:
        # 顶部标题
        gr.Markdown("# 维标管理工具")

        # 选项卡
        with gr.Tabs():
            # 文档管理选项卡
            with gr.TabItem("文档管理"):
                # 文档上传区域
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("## 文档上传")
                        file_upload = gr.File(
                            file_types=[".doc", ".docx"],
                            label="上传Word文档",
                            file_count="multiple"
                        )
                        upload_button = gr.Button("上传文档")
                        folder_upload = gr.File(
                            file_types=[".doc", ".docx"],
                            label="上传文件夹",
                            file_count="directory"
                        )
                        upload_folder_button = gr.Button("上传文件夹")

                    with gr.Column(scale=2):
                        gr.Markdown("## 文档列表")
                        # 文档列表复选框组
                        document_checkbox = gr.CheckboxGroup([], label="选择文档", interactive=True)
                        # 文档操作按钮
                        with gr.Row():
                            with gr.Column():
                                rename_button = gr.Button("重命名选中文档")
                                new_name = gr.Textbox(
                                    label="新名称",
                                    placeholder="输入新名称"
                                )
                            with gr.Column():
                                clean_button = gr.Button("清洗选中文档")
                                delete_button = gr.Button("删除选中文档")

                # 文档详情和预览区域
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("## 文档详情")
                        document_details = gr.JSON()
                        document_preview = gr.Textbox(
                            label="文档预览",
                            lines=10,
                            max_lines=20,
                            interactive=False
                        )
                    with gr.Column(scale=1):
                        gr.Markdown("## 统计信息")
                        document_stats = gr.JSON()

            # 知识抽取选项卡
            with gr.TabItem("知识抽取"):
                # 文档选择区域
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("## 选择要抽取的文档")
                        # 知识抽取用的文档选择器（与文档管理选项卡同步）
                        extraction_document_checkbox = gr.CheckboxGroup([], label="选择文档进行知识抽取", interactive=True)
                        refresh_docs_button = gr.Button("刷新文档列表")
                
                # 抽取配置区域
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("## 抽取配置")
                        model_name = gr.Dropdown(
                            choices=["deepseek-r1", "deepseek-v2"],
                            value="deepseek-r1",
                            label="模型选择"
                        )
                        concurrency = gr.Slider(
                            minimum=1,
                            maximum=5,
                            value=3,
                            step=1,
                            label="并发数量"
                        )
                        timeout = gr.Slider(
                            minimum=30,
                            maximum=300,
                            value=120,
                            step=30,
                            label="超时时间(秒)"
                        )
                        extract_button = gr.Button("开始抽取")

                    with gr.Column(scale=2):
                        gr.Markdown("## 抽取状态")
                        # 抽取状态表格
                        extraction_table = gr.DataFrame(
                            headers=["任务ID", "文档数量", "状态", "进度", "错误信息"],
                            datatype=["str", "int", "str", "str", "str"],
                            interactive=False,
                            wrap=True
                        )
                        # 抽取结果统计
                        extraction_stats = gr.JSON()

                # 抽取结果区域
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("## 抽取结果")
                        extraction_results = gr.JSON()
                    with gr.Column(scale=1):
                        gr.Markdown("## 错误信息")
                        extraction_errors = gr.JSON()
                        
                # Cypher语句显示区域
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("## 生成的Cypher语句")
                        cypher_output = gr.Textbox(
                            label="Cypher语句",
                            lines=15,
                            max_lines=30,
                            interactive=False,
                            placeholder="生成的Cypher语句将在这里显示..."
                        )
                        with gr.Row():
                            cypher_copy_button = gr.Button("复制Cypher语句")
                            write_neo4j_button = gr.Button("写入Neo4j")

            # 知识查询选项卡
            with gr.TabItem("知识查询"):
                # 查询区域
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("## 查询")
                        query_input = gr.Textbox(
                            label="输入查询",
                            placeholder="例如：查找所有设备",
                            lines=3
                        )
                        query_button = gr.Button("执行查询")
                        query_history = gr.JSON()

                    with gr.Column(scale=2):
                        gr.Markdown("## 查询结果")
                        # 查询结果可视化
                        query_visualization = gr.Plot()
                        # 查询结果表格
                        query_results = gr.DataFrame(
                            headers=["实体", "类型", "属性"],
                            datatype=["str", "str", "str"],
                            interactive=False,
                            wrap=True
                        )
                        # 查询结果导出
                        export_button = gr.Button("导出结果")

    # 定义事件处理函数

        def clean_cypher_for_execution(cypher_text):
            """
            清理Cypher语句，移除注释行，只保留可执行的Cypher语句
            
            Args:
                cypher_text: 包含注释的Cypher文本
                
            Returns:
                清理后的Cypher语句
            """
            if not cypher_text:
                return ""
            
            lines = cypher_text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # 移除注释行（以--开头的行）
                if line.strip().startswith('--'):
                    continue
                # 保留非空行
                if line.strip():
                    cleaned_lines.append(line)
            
            return '\n'.join(cleaned_lines)

        def upload_documents(files):
            """上传文档"""
            if not files:
                return [], {}, "请选择要上传的文件"

            try:
                # 转换为Path对象
                file_paths = [Path(file.name) for file in files]

                # 上传文档
                documents = document_service.upload_documents(file_paths)

                # 更新文档列表
                choices, stats = update_document_list()

                return choices, stats, f"成功上传 {len(documents)} 个文档"
            except Exception as e:
                logger.error(f"上传文档失败: {str(e)}")
                return [], {}, f"上传失败: {str(e)}"

        def upload_folder(folder):
            """上传文件夹"""
            if not folder:
                return [], {}, "请选择要上传的文件夹"

            try:
                # 转换为Path对象
                folder_path = Path(folder.name)

                # 上传文件夹中的文档
                documents = document_service.upload_folder(folder_path)

                # 更新文档列表
                choices, stats = update_document_list()

                return choices, stats, f"成功上传 {len(documents)} 个文档"
            except Exception as e:
                logger.error(f"上传文件夹失败: {str(e)}")
                return [], {}, f"上传失败: {str(e)}"

        def update_document_list():
            """更新文档列表"""
            try:
                # 获取文档列表
                documents, total = document_service.list_documents()

                # 准备复选框选项
                choices = []
                for doc in documents:
                    # 格式: 文档ID - 文档名称 (状态)
                    choice = f"{doc.id} - {doc.name} ({doc.status.value})"
                    choices.append(choice)

                # 返回复选框选项和统计信息
                return choices, document_service.get_document_statistics()
            except Exception as e:
                logger.error(f"更新文档列表失败: {str(e)}")
                return [], {}

        def show_document_details(document_id):
            """显示文档详情"""
            if not document_id:
                return {}, ""

            try:
                # 获取文档
                document = document_service.get_document(document_id)
                if not document:
                    return {}, "文档不存在"

                # 获取文档预览
                preview = document_service.get_document_preview(document_id)

                # 准备文档详情
                details = {
                    "ID": document.id,
                    "名称": document.name,
                    "原始名称": document.original_name,
                    "文件大小": f"{document.file_size / 1024:.2f} KB",
                    "文件哈希": document.file_hash,
                    "状态": document.status.value,
                    "创建时间": document.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "更新时间": document.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "错误信息": document.error_message
                }

                return details, preview or "无法预览文档"
            except Exception as e:
                logger.error(f"显示文档详情失败: {str(e)}")
                return {}, f"获取详情失败: {str(e)}"

        def rename_document(selected_choices, new_name):
            """重命名选中的文档"""
            if not selected_choices or not new_name:
                return [], {}, "请选择文档并输入新名称"

            try:
                # 从选中的选项中提取文档ID
                # 选项格式: "文档ID - 文档名称 (状态)"
                selected_doc_id = selected_choices[0].split(" - ")[0]

                # 重命名文档
                document = document_service.rename_document(selected_doc_id, new_name)

                if document:
                    # 更新文档列表
                    choices, stats = update_document_list()
                    return choices, stats, f"文档重命名成功: {new_name}"
                else:
                    choices, stats = update_document_list()
                    return choices, stats, "文档不存在"
            except Exception as e:
                logger.error(f"重命名文档失败: {str(e)}")
                choices, stats = update_document_list()
                return choices, stats, f"重命名失败: {str(e)}"

        def clean_document(selected_choices):
            """清洗选中的文档数据"""
            if not selected_choices:
                return [], {}, "请选择要清洗的文档"

            try:
                # 从选中的选项中提取文档ID
                # 选项格式: "文档ID - 文档名称 (状态)"
                selected_doc_id = selected_choices[0].split(" - ")[0]

                # 清洗文档数据
                document = document_service.clean_document(selected_doc_id)

                if document:
                    # 更新文档列表
                    choices, stats = update_document_list()
                    return choices, stats, f"文档数据清洗完成: {document.name}"
                else:
                    choices, stats = update_document_list()
                    return choices, stats, "文档不存在"
            except Exception as e:
                logger.error(f"清洗文档数据失败: {str(e)}")
                choices, stats = update_document_list()
                return choices, stats, f"清洗失败: {str(e)}"

        def delete_document(selected_choices):
            """删除选中的文档"""
            if not selected_choices:
                return [], {}, "请选择要删除的文档"

            try:
                # 从选中的选项中提取文档ID
                # 选项格式: "文档ID - 文档名称 (状态)"
                selected_doc_id = selected_choices[0].split(" - ")[0]

                # 删除文档
                success = document_service.delete_document(selected_doc_id)

                if success:
                    # 更新文档列表
                    choices, stats = update_document_list()
                    return choices, stats, "文档删除成功"
                else:
                    choices, stats = update_document_list()
                    return choices, stats, "文档不存在"
            except Exception as e:
                logger.error(f"删除文档失败: {str(e)}")
                choices, stats = update_document_list()
                return choices, stats, f"删除失败: {str(e)}"

        def sync_document_selection():
            """同步文档列表到知识抽取选项卡"""
            try:
                choices, _ = update_document_list()
                return gr.CheckboxGroup(choices=choices, value=[], interactive=True)
            except Exception as e:
                logger.error(f"同步文档列表失败: {str(e)}")
                return gr.CheckboxGroup([], interactive=True)

        def extract_knowledge(selected_choices, model_name, concurrency, timeout):
            """知识抽取处理函数"""
            if not selected_choices:
                return [], {}, "请选择要抽取知识的文档"
            
            try:
                # 从选中的选项中提取文档ID
                document_ids = []
                for choice in selected_choices:
                    doc_id = choice.split(" - ")[0]
                    document_ids.append(doc_id)
                
                logger.info(f"开始知识抽取: {document_ids}")
                
                # 批量抽取知识
                results = knowledge_service.extract_knowledge_from_documents(
                    document_ids=document_ids,
                    concurrency=concurrency,
                    timeout=timeout
                )
                
                # 生成Cypher语句
                cypher_statements = []
                entity_count = 0
                relation_count = 0
                
                for doc_id, kg in results.items():
                    if kg and kg.entities:  # 确保知识图谱不为空且有实体
                        # 优先使用LLM生成的Cypher语句
                        if kg.metadata and kg.metadata.get("cypher_statements"):
                            llm_cypher = kg.metadata["cypher_statements"]
                            cypher_statements.append(f"-- 文档: {doc_id} (LLM生成)\n" + "\n".join(llm_cypher) + "\n")
                        else:
                            # 回退到程序生成的Cypher
                            cypher = kg.to_cypher()
                            cypher_statements.append(f"-- 文档: {doc_id} (程序生成)\n{cypher}\n")
                        
                        entity_count += len(kg.entities)
                        relation_count += len(kg.relations)
                    else:
                        # 如果知识图谱为空，添加错误信息
                        cypher_statements.append(f"-- 文档: {doc_id} (抽取失败)\n-- 错误: 知识抽取失败或返回空结果\n")
                
                # 更新文档列表
                choices, stats = update_document_list()
                
                # 准备抽取结果统计
                extraction_stats = {
                    "处理文档数": len(document_ids),
                    "成功文档数": len(results),
                    "抽取实体数": entity_count,
                    "抽取关系数": relation_count,
                    "生成的Cypher语句": "\n".join(cypher_statements)
                }
                
                cypher_text = "\n".join(cypher_statements) if cypher_statements else "暂无Cypher语句生成"
                
                # 同步更新两个文档选择器
                extraction_choices = gr.CheckboxGroup(choices=choices, value=[], interactive=True)
                
                return choices, extraction_choices, extraction_stats, cypher_text, f"知识抽取完成！成功处理 {len(results)} 个文档，抽取 {entity_count} 个实体，{relation_count} 个关系"
                
            except Exception as e:
                logger.error(f"知识抽取失败: {str(e)}")
                choices, stats = update_document_list()
                extraction_choices = gr.CheckboxGroup(choices=choices, value=[], interactive=True)
                return choices, extraction_choices, {}, "", f"抽取失败: {str(e)}"

            # 绑定事件

        # 文档管理操作的事件绑定（同时更新两个文档选择器）
        def sync_upload_documents(files):
            choices, stats, message = upload_documents(files)
            extraction_choices = gr.CheckboxGroup(choices=choices, value=[], interactive=True)
            return choices, extraction_choices, stats, message
            
        def sync_upload_folder(folder):
            choices, stats, message = upload_folder(folder)
            extraction_choices = gr.CheckboxGroup(choices=choices, value=[], interactive=True)
            return choices, extraction_choices, stats, message
            
        def sync_rename_document(selected_choices, new_name):
            choices, stats, message = rename_document(selected_choices, new_name)
            extraction_choices = gr.CheckboxGroup(choices=choices, value=[], interactive=True)
            return choices, extraction_choices, stats, message
            
        def sync_clean_document(selected_choices):
            choices, stats, message = clean_document(selected_choices)
            extraction_choices = gr.CheckboxGroup(choices=choices, value=[], interactive=True)
            return choices, extraction_choices, stats, message
            
        def sync_delete_document(selected_choices):
            choices, stats, message = delete_document(selected_choices)
            extraction_choices = gr.CheckboxGroup(choices=choices, value=[], interactive=True)
            return choices, extraction_choices, stats, message

        upload_button.click(sync_upload_documents, inputs=[file_upload], outputs=[document_checkbox, extraction_document_checkbox, document_stats, gr.Textbox(label="上传状态")])
        upload_folder_button.click(sync_upload_folder, inputs=[folder_upload], outputs=[document_checkbox, extraction_document_checkbox, document_stats, gr.Textbox(label="上传状态")])
        rename_button.click(sync_rename_document, inputs=[document_checkbox, new_name], outputs=[document_checkbox, extraction_document_checkbox, document_stats, gr.Textbox(label="操作状态")])
        clean_button.click(sync_clean_document, inputs=[document_checkbox], outputs=[document_checkbox, extraction_document_checkbox, document_stats, gr.Textbox(label="操作状态")])
        delete_button.click(sync_delete_document, inputs=[document_checkbox], outputs=[document_checkbox, extraction_document_checkbox, document_stats, gr.Textbox(label="操作状态")])
        
        def write_neo4j(cypher_text):
            if not cypher_text or not cypher_text.strip():
                return "没有可写入的Cypher语句"
            try:
                # 清理Cypher语句，移除注释行
                cleaned_cypher = clean_cypher_for_execution(cypher_text)
                if not cleaned_cypher.strip():
                    return "清理后的Cypher语句为空，无法执行"
                
                graph_service.write_cypher(cleaned_cypher)
                return "已写入Neo4j"
            except Exception as e:
                return f"写入失败: {str(e)}"

        def execute_query(query_text):
            """执行知识查询"""
            if not query_text or not query_text.strip():
                return [], [], "请输入查询内容"
            
            try:
                logger.info(f"执行查询: {query_text}")
                
                # 使用QueryService执行自然语言查询
                query_result = query_service.query_by_natural_language(
                    query_text=query_text,
                    max_results=50
                )
                
                # 格式化结果为DataFrame
                results_data = []
                for result in query_result["results"]:
                    if result["type"] == "entity":
                        results_data.append([
                            result["name"],
                            result["type_value"],
                            str(result.get("properties", {}))
                        ])
                    elif result["type"] == "relation":
                        results_data.append([
                            f"{result['source']} -> {result['target']}",
                            result["type_value"],
                            str(result.get("properties", {}))
                        ])
                
                # 更新查询历史
                history = query_service.get_query_history(10)
                
                # 生成可视化数据（使用专业的可视化工具）
                from utils.visualization import create_query_result_visualization
                
                # 创建查询结果可视化
                fig = create_query_result_visualization(query_result["results"])
                
                return fig, results_data, f"查询完成！找到 {len(results_data)} 个结果。生成的Cypher: {query_result['cypher_query']}"
                
            except Exception as e:
                logger.error(f"查询执行失败: {str(e)}")
                import plotly.graph_objects as go
                fig = go.Figure()
                fig.add_annotation(
                    text=f"查询失败: {str(e)}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False, font=dict(size=14, color="red")
                )
                return fig, [], f"查询失败: {str(e)}"

        # 知识抽取与写入按钮事件绑定
        extract_button.click(
            extract_knowledge, 
            inputs=[extraction_document_checkbox, model_name, concurrency, timeout], 
            outputs=[document_checkbox, extraction_document_checkbox, extraction_stats, cypher_output, gr.Textbox(label="抽取状态")]
        )

        write_neo4j_button.click(
            write_neo4j,
            inputs=[cypher_output],
            outputs=[gr.Textbox(label="写入状态")]
        )
        
        # 刷新文档列表按钮事件绑定
        refresh_docs_button.click(
            sync_document_selection,
            inputs=[],
            outputs=[extraction_document_checkbox]
        )
        
        # 知识查询按钮事件绑定
        query_button.click(
            execute_query,
            inputs=[query_input],
            outputs=[query_visualization, query_results, gr.Textbox(label="查询状态")]
        )

    return app

def main():
    """主函数"""
    # 创建应用
    app = create_app()

    # 启动应用
    app.launch()

if __name__ == "__main__":
    main()
