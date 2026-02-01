"""
工具定义与实现文件
维护所有可供模型调用的工具列表及其执行逻辑
"""

import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# 获取代理配置
PROXY = os.getenv("HTTP_PROXY", "") or os.getenv("HTTPS_PROXY", "")
if PROXY:
    print(f"[Tools] 代理已配置: {PROXY}")

# 导入DuckDuckGo搜索库（新版本是ddgs）
DDGS = None
try:
    from ddgs import DDGS
    print("[Tools] 使用 ddgs 库")
except ImportError:
    try:
        from duckduckgo_search import DDGS
        print("[Tools] 使用 duckduckgo_search 库")
    except ImportError:
        print("[Tools] 错误: 请安装搜索库: pip install ddgs")


# 工具定义列表
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索互联网获取实时信息。当用户询问最新新闻、实时数据、不确定的事实、或需要网络查询才能回答的问题时使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询关键词，应该简洁明确，包含核心关键词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "期望返回的搜索结果数量，默认为5",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    使用DuckDuckGo执行网络搜索
    """
    if DDGS is None:
        return {"success": False, "error": "搜索库未安装，请运行: pip install ddgs", "results": []}
    
    try:
        print(f"[Tool] 开始DuckDuckGo搜索: {query}")
        print(f"[Tool] 使用代理: {PROXY if PROXY else '无'}")
        
        # 创建DDGS实例，传入代理配置
        if PROXY:
            ddgs = DDGS(timeout=20, proxy=PROXY)
        else:
            ddgs = DDGS(timeout=20)
        
        # 执行搜索
        results = list(ddgs.text(query, max_results=max_results))
        
        print(f"[Tool] 获取到 {len(results)} 条结果")
        
        # 格式化结果
        formatted_results = []
        for item in results:
            formatted_results.append({
                "title": item.get("title", ""),
                "url": item.get("href", ""),
                "content": item.get("body", "")
            })
        
        return {"success": True, "query": query, "results": formatted_results}
        
    except Exception as e:
        import traceback
        print(f"[Tool] 搜索异常: {str(e)}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e), "results": []}


def execute_tool(tool_name: str, tool_params: Dict[str, Any]) -> str:
    """执行工具并返回结果字符串"""
    if tool_name == "web_search":
        query = tool_params.get("query", "")
        max_results = tool_params.get("max_results", 5)
        
        result = web_search(query, max_results)
        
        if not result["success"]:
            return f"搜索失败: {result.get('error', '未知错误')}"
        
        if not result["results"]:
            return f"搜索关键词: {result['query']}\n搜索结果: 未找到相关结果"
        
        # 格式化输出
        output_parts = [f"搜索关键词: {result['query']}", f"搜索结果 ({len(result['results'])}条):\n"]
        
        for i, item in enumerate(result["results"], 1):
            output_parts.append(f"[{i}] {item['title']}")
            output_parts.append(f"    链接: {item['url']}")
            content = item['content'][:200] + "..." if len(item['content']) > 200 else item['content']
            output_parts.append(f"    摘要: {content}\n")
        
        return "\n".join(output_parts)
    
    return f"未知工具: {tool_name}"


def get_tool_by_name(name: str) -> Optional[dict]:
    for tool in TOOLS:
        if tool["function"]["name"] == name:
            return tool
    return None


def get_all_tool_names() -> List[str]:
    return [tool["function"]["name"] for tool in TOOLS]


def get_tools_description() -> str:
    descriptions = []
    for tool in TOOLS:
        func = tool["function"]
        params = func["parameters"]["properties"]
        param_desc = ", ".join([f"{k}: {v.get('description', '')}" for k, v in params.items()])
        descriptions.append(f"- {func['name']}: {func['description']}\n  参数: {param_desc}")
    return "\n".join(descriptions)


if __name__ == "__main__":
    print("\n测试DuckDuckGo搜索...\n")
    print(execute_tool("web_search", {"query": "Vue框架", "max_results": 3}))
