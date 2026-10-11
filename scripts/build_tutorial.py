"""生成网页教程使用的源码快照；只发布显式白名单中的源码，不读取密钥或运行记录。"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {
    'app.py', 'web/app.js', 'web/workspace.js', 'estate_agent/runtime.py', 'estate_agent/state.py',
    'estate_agent/intent.py', 'estate_agent/contracts.py', 'estate_agent/llm.py',
    'estate_agent/sql_tools.py', 'estate_agent/business.py', 'estate_agent/retrieval.py',
    'estate_agent/report.py', 'estate_agent/storage.py', 'estate_agent/graph_rag.py',
    'data/knowledge.json', 'tests/test_agent.py', 'evaluate.py', 'eval_cases.json',
    'mcp_server.py', 'extras/train_lora.py',
}


def symbols(text):
    result = {}

    def visit(node, prefix=''):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + child.name
                result[name] = (child.lineno, child.end_lineno)
                visit(child, name + '.')
            else:
                visit(child, prefix)

    visit(ast.parse(text))
    return result


def main():
    lessons = json.loads((ROOT / 'docs/tutorials.json').read_text(encoding='utf-8'))
    files = {}
    for lesson in lessons:
        for ref in lesson['refs']:
            path = ref['path']
            if path not in ALLOWED:
                raise ValueError(f'Source is not allowlisted: {path}')
            if path not in files:
                text = (ROOT / path).read_text(encoding='utf-8-sig')
                files[path] = {'text': text, 'sha256': hashlib.sha256(text.encode()).hexdigest()}
            text = files[path]['text']
            start, end = symbols(text)[ref['symbol']] if ref.get('symbol') else (1, len(text.splitlines()))
            if ref.get('start_marker'):
                matches = [i for i, line in enumerate(text.splitlines(), 1)
                           if start <= i <= end and line == ref['start_marker']]
                if len(matches) != 1:
                    raise ValueError(f'Invalid source marker: {path}')
                start = matches[0]
            # AST 的 lineno 从 def/class 开始；把紧贴定义的中文导读也包含进片段。
            lines = text.splitlines()
            while start > 1 and lines[start - 2].lstrip().startswith('#'):
                start -= 1
            ref.update(start=start, end=end)
    payload = {'version': 1, 'lessons': lessons, 'files': files}
    target = ROOT / 'web/tutorial-data.json'
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Tutorial built: {len(lessons)} topics, {len(files)} source files.')


if __name__ == '__main__':
    main()
