"""
工具注册中心：统一管理所有批改工具
"""
from typing import List
from langchain_core.tools import BaseTool
from src.tools.qr_tool import parse_qr_code
from src.tools.ocr_tool import ocr_handwriting
from src.tools.template_tool import remove_template_text
from src.tools.grammar_tool import grammar_check
from src.tools.scoring_tool import score_essay_4dimensions


class ToolRegistry:
    """工具注册中心"""

    _instance = None
    _tools: List[BaseTool] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._register_defaults()
        return cls._instance

    def _register_defaults(self):
        self._tools = [
            parse_qr_code,
            ocr_handwriting,
            remove_template_text,
            grammar_check,
            score_essay_4dimensions,
        ]

    def get_all_tools(self) -> List[BaseTool]:
        return self._tools

    def get_tool_by_name(self, name: str) -> BaseTool:
        for tool in self._tools:
            if tool.name == name:
                return tool
        raise ValueError(f"工具 '{name}' 未注册")

    def add_tool(self, tool: BaseTool):
        self._tools.append(tool)


tool_registry = ToolRegistry()
