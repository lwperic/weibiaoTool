# !/user/bin/env python3
# -*- coding: utf-8 -*-
import gradio as gr

with gr.Blocks() as demo:
    with gr.Row():
        file_upload = gr.File(file_types=[".doc", ".docx"], label="上传Word文档", file_count="multiple")
        submit_btn = gr.Button("提交")

    # 动态生成复选框区域
    checkbox_group = gr.CheckboxGroup([], label="选择要处理的文件", interactive=True)


    def update_checkboxes(files):
        if files:
            return gr.CheckboxGroup(choices=[f.name for f in files], value=[], interactive=True)
        return gr.CheckboxGroup([], interactive=True)


    file_upload.change(update_checkboxes, inputs=file_upload, outputs=checkbox_group)

    submit_btn.click(
        lambda files, selected: print(f"选中的文件: {selected}"),
        inputs=[file_upload, checkbox_group],
        outputs=None
    )