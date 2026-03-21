"""
文档解析模块 — 支持 .docx、.pdf 和纯文本文件的内容提取。
"""
from __future__ import annotations

import os
import re


def _extract_docx(file_path: str) -> str:
    """从 .docx 文件中提取纯文本内容。"""
    try:
        from docx import Document  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "解析 .docx 文件需要安装 python-docx 库：pip install python-docx"
        ) from exc

    doc = Document(file_path)
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _extract_pdf(file_path: str) -> str:
    """从 .pdf 文件中提取纯文本内容。"""
    try:
        from pypdf import PdfReader  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "解析 PDF 文件需要安装 pypdf 库：pip install pypdf"
        ) from exc

    reader = PdfReader(file_path)
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n".join(pages)


def _extract_txt(file_path: str) -> str:
    """从纯文本文件中提取内容。"""
    with open(file_path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def extract_text(file_path: str) -> str:
    """
    自动根据文件扩展名选择合适的解析器，返回文档的纯文本内容。

    支持格式：
        .docx — Microsoft Word（新格式）
        .doc  — 提示需转换为 .docx
        .pdf  — PDF 文档
        .txt  — 纯文本文件

    Raises:
        FileNotFoundError: 文件不存在时抛出。
        ValueError: 不支持的文件格式时抛出。
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"文件不存在：{file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".docx":
        return _extract_docx(file_path)
    if ext == ".doc":
        raise ValueError(
            "暂不支持旧版 .doc 格式，请将文件另存为 .docx 后重试。"
        )
    if ext == ".pdf":
        return _extract_pdf(file_path)
    if ext in (".txt", ".text", ""):
        return _extract_txt(file_path)

    raise ValueError(
        f"不支持的文件格式：{ext}。支持格式：.docx、.pdf、.txt"
    )


def split_clauses(text: str) -> list[dict[str, str]]:
    """
    将合同文本按条款拆分为列表，每个元素包含 ``number`` 和 ``text`` 字段。

    识别规则（按优先级）：
        1. 中文编号：第一条、第二条 … 第N条
        2. 阿拉伯数字编号：1.、2.、3. 或 1、2、3（后接中文/英文内容）

    未能识别条款号的内容归入序号为空字符串的兜底条款。
    """
    # Pattern: 第X条 or 第X.X条 (Chinese numbering)
    chinese_pattern = re.compile(
        r"(第\s*[一二三四五六七八九十百千\d]+\s*[条款章节])",
        re.UNICODE,
    )
    # Pattern: 1. / 1、 / （1） at start of a line
    arabic_pattern = re.compile(
        r"^(\d+[\s\.、。）\)]+)",
        re.MULTILINE | re.UNICODE,
    )

    clauses: list[dict[str, str]] = []

    # Try Chinese clause splitting first
    parts = chinese_pattern.split(text)
    if len(parts) > 1:
        # parts = [preamble, heading1, body1, heading2, body2, ...]
        if parts[0].strip():
            clauses.append({"number": "", "text": parts[0].strip()})
        for i in range(1, len(parts), 2):
            heading = parts[i].strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            clauses.append({"number": heading, "text": body})
        return clauses

    # Fallback: Arabic number splitting
    parts = arabic_pattern.split(text)
    if len(parts) > 1:
        if parts[0].strip():
            clauses.append({"number": "", "text": parts[0].strip()})
        for i in range(1, len(parts), 2):
            number = parts[i].strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            clauses.append({"number": number, "text": body})
        return clauses

    # No structure detected — return entire text as one clause
    return [{"number": "", "text": text.strip()}]
