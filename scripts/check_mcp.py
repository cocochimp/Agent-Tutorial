"""真实MCP握手、工具发现、调用和权限负例。"""
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params=StdioServerParameters(command=sys.executable,args=['-X','utf8',str(Path(__file__).resolve().parents[1]/'mcp_server.py')])
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            names={t.name for t in (await session.list_tools()).tools}
            assert names=={'metric_schema','query_business','knowledge_search'}
            assert not (await session.call_tool('metric_schema',{})).isError
            result=await session.call_tool('query_business',{'question':'朝阳最近7天带看转成交率'})
            assert not result.isError
            denied=await session.call_tool('query_business',{'question':'海淀最近7天带看转成交率'})
            assert denied.isError
            assert (await session.list_resources()).resources
            print('MCP: handshake, discover, call, ACL, resource PASS')

asyncio.run(main())
