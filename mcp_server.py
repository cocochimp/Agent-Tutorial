"""真实MCP stdio服务，身份固定于服务端启动参数。"""
import argparse
import json
from mcp.server.fastmcp import FastMCP
from estate_agent.auth import identity
from estate_agent.data import initialize
from estate_agent.intent import understand
from estate_agent.retrieval import search_knowledge
from estate_agent.sql_tools import retrieve_schema, query_metrics, calculate_metrics


def create_server(username='chaoyang', backend='bm25'):
    user = identity(username)
    server = FastMCP('estate-analysis-readonly')

    @server.tool()
    def metric_schema(metric: str = 'viewing_to_deal') -> dict:
        """获取指标表字段、连接键和计算口径。"""
        return retrieve_schema(metric)

    @server.tool()
    def query_business(question: str) -> dict:
        """查询授权区域经营指标；不执行写入、工单或通知。"""
        task = understand(question, user=user)
        if task['action'] != 'none':
            raise ValueError('MCP仅开放只读能力，业务动作请到网页审批。')
        return calculate_metrics(query_metrics(task, user))

    @server.tool()
    def knowledge_search(query: str, region: str = '朝阳') -> dict:
        """检索权限、版本、有效期过滤后的制度。"""
        return search_knowledge(query, region, user, backend=backend)

    @server.resource('estate://schema')
    def schema_resource() -> str:
        return json.dumps(retrieve_schema('viewing_to_deal'), ensure_ascii=False)

    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--user', default='chaoyang', choices=['chaoyang','haidian','director','viewer'])
    parser.add_argument('--backend', default='bm25', choices=['bm25','hybrid'])
    args = parser.parse_args()
    initialize()
    create_server(args.user, args.backend).run(transport='stdio')
