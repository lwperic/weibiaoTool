#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gradio测试程序
用于测试文件上传和选择功能
"""

import gradio as gr
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数，创建并启动Gradio界面"""
    try:
        with gr.Blocks(title="文档上传测试") as demo:
            with gr.Row():
                file_upload = gr.File(
                    file_types=[".doc", ".docx"],
                    label="上传Word文档",
                    file_count="multiple"
                )
                submit_btn = gr.Button("提交")

            # 动态生成复选框区域
            checkbox_group = gr.CheckboxGroup(
                [],
                label="选择要处理的文件",
                interactive=True
            )

            def update_checkboxes(files):
                """更新复选框选项"""
                if files:
                    file_names = [f.name if hasattr(f, 'name') else str(f) for f in files]
                    logger.info(f"更新文件列表: {file_names}")
                    return gr.CheckboxGroup(choices=file_names, value=[], interactive=True)
                return gr.CheckboxGroup([], interactive=True)

            def process_files(files, selected):
                """处理选中的文件"""
                if not selected:
                    logger.warning("没有选择任何文件")
                    return "请先选择要处理的文件"

                logger.info(f"开始处理选中的文件: {selected}")
                # 这里添加文件处理逻辑
                return f"正在处理文件: {', '.join(selected)}"

            # 绑定事件
            file_upload.change(
                update_checkboxes,
                inputs=file_upload,
                outputs=checkbox_group
            )

            submit_btn.click(
                process_files,
                inputs=[file_upload, checkbox_group],
                outputs=gr.Textbox(label="处理状态")
            )

        # 启动应用
        logger.info("启动Gradio应用")
        demo.launch(server_name="0.0.0.0", server_port=7860)

    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")
        raise

if __name__ == "__main__":
    main()
