"""生成HTML说明书及带行号的源码索引。"""
import ast
import html
import re
from pathlib import Path
from markdown_it import MarkdownIt

ROOT=Path(__file__).resolve().parents[1]
CSS='''body{font:16px/1.8 "Segoe UI","Microsoft YaHei",sans-serif;background:#f7f5ef;color:#283c47;max-width:1180px;margin:40px auto;padding:0 28px}h1{font-size:32px}h2{margin-top:56px;border-bottom:2px solid #bedbd5;padding-bottom:8px}h3{margin-top:32px}a{color:#087b76}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #d5ded9;padding:10px;vertical-align:top}th{background:#e3efea}pre{background:#e9eee9;padding:20px;overflow:auto;line-height:1.6}code{font-family:Consolas,monospace;font-size:.92em}.line{display:block;min-height:1.5em}.line:target{background:#fff2b4}.ln{display:inline-block;width:45px;color:#82908b;text-decoration:none;user-select:none}nav{padding:18px;border:1px solid #bbd8d0;background:#eef5ef}img,svg{max-width:100%}@media(max-width:700px){body{margin:15px auto;padding:0 12px}table{display:block;overflow:auto}h1{font-size:26px}}'''

def source_name(path): return path.replace('/','__')+'.html'

def locate(path,symbol):
    text=(ROOT/path).read_text(encoding='utf-8-sig')
    if not symbol: return 1
    tree=ast.parse(text)
    found={}
    def walk(node,prefix=''):
        for child in ast.iter_child_nodes(node):
            if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                name=prefix+child.name;found[name]=child.lineno
                walk(child,name+'.')
            else: walk(child,prefix)
    walk(tree)
    if symbol in found: return found[symbol]
    matches=[line for name,line in found.items() if name.endswith('.'+symbol)]
    if len(matches)!=1: raise ValueError(f'Missing/ambiguous symbol: {path}::{symbol}')
    return matches[0]


def main():
    docs=ROOT/'docs';sources=docs/'source';sources.mkdir(parents=True,exist_ok=True)
    raw=(docs/'manual_source.md').read_text(encoding='utf-8-sig');files=set()
    def replace(m):
        path,_,symbol=m.group(1).partition('::');files.add(path)
        line=locate(path,symbol)
        label=path+((' · '+symbol) if symbol else '')+' · L'+str(line)
        return f'[{label}](source/{source_name(path)}#L{line})'
    markdown=re.sub(r'\[\[([^\]]+)\]\]',replace,raw)
    (docs/'能力对照说明书.md').write_text(markdown,encoding='utf-8')
    rendered=MarkdownIt('commonmark').enable('table').render(markdown)
    headings=[]
    def anchor(m):
        idx='section-'+str(len(headings)+1);headings.append((idx,m.group(1)))
        return f'<h2 id="{idx}">{m.group(1)}</h2>'
    rendered=re.sub(r'<h2>(.*?)</h2>',anchor,rendered)
    toc='<nav>'+''.join(f'<a href="#{i}">{title}</a><br>' for i,title in headings)+'</nav>'
    rendered=rendered.replace('</h1>','</h1>'+toc,1)
    (docs/'能力对照说明书.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>能力对照说明书</title><style>'+CSS+'</style><body>'+rendered+'</body></html>',encoding='utf-8')
    for path in files:
        lines=(ROOT/path).read_text(encoding='utf-8-sig').splitlines()
        body=''.join(f'<span class="line" id="L{i}"><a class="ln" href="#L{i}">{i}</a>{html.escape(line)}</span>' for i,line in enumerate(lines,1))
        (sources/source_name(path)).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+html.escape(path)+'</title><style>'+CSS+'</style><body><a href="../能力对照说明书.html">← 返回能力对照说明书</a><h1>'+html.escape(path)+'</h1><pre><code>'+body+'</code></pre></body></html>',encoding='utf-8')
    (ROOT/'代码导读.md').write_text('# 代码导读\n\n[能力对照说明书](docs/能力对照说明书.html)提供模块说明、参考手册章节映射、文件与函数索引、运行示例和验证范围。\n\n重点入口：estate_agent/runtime.py 的 build_graph() 和 run()。\n',encoding='utf-8')
    print(f'Manual built: {len(files)} source files; {len(headings)} chapters.')

if __name__=='__main__': main()
