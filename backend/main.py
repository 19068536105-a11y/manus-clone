import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

from tools import TOOLS, execute_tool
from prompts import get_planner_prompt, get_executor_prompt, get_verify_prompt

# 加载环境变量
load_dotenv()

app = FastAPI(title="Manus Chat API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化DeepSeek客户端
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


class ChatMessage(BaseModel):
    message: str


def call_planner(user_message: str) -> dict:
    """调用Planner智能体进行任务规划"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": get_planner_prompt()},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"}
        )
        
        plan = json.loads(response.choices[0].message.content)
        return plan
        
    except Exception as e:
        print(f"[Planner] 错误: {e}")
        return {
            "user_intent": user_message,
            "sub_tasks": [{"id": 1, "task": "直接回答用户问题", "depends_on": []}]
        }


def call_executor(task_description: str) -> dict:
    """调用Executor智能体分析如何执行子任务"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": get_executor_prompt()},
                {"role": "user", "content": f"子任务：{task_description}"}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        print(f"[Executor] 错误: {e}")
        return {"need_tool": False, "tool_name": None, "tool_params": None, "reason": str(e)}


def call_reasoner(message: str, log_input: bool = False) -> str:
    """调用DeepSeek Reasoner生成回答"""
    # 如果需要打印输入（用于最终汇总时）
    if log_input:
        print(f"\n{'='*60}")
        print(f"[Reasoner] 汇总答案输入:")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")
    
    try:
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[{"role": "user", "content": message}]
        )
        
        reply = response.choices[0].message.content
        return reply
        
    except Exception as e:
        print(f"[Reasoner] 错误: {e}")
        raise


def call_verify(user_question: str, draft_answer: str) -> str:
    """调用Verify智能体校验和优化答案"""
    try:
        prompt = f"""用户问题：{user_question}

AI生成的回答：
{draft_answer}

请校验并优化以上回答。"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": get_verify_prompt()},
                {"role": "user", "content": prompt}
            ]
        )
        
        verified_answer = response.choices[0].message.content
        
        # 打印Verify输出
        print(f"\n{'='*60}")
        print(f"[Verify] 校验后的最终答案:")
        print(f"{'='*60}")
        print(verified_answer)
        print(f"{'='*60}\n")
        
        return verified_answer
        
    except Exception as e:
        print(f"[Verify] 错误: {e}")
        # 如果校验失败，返回原答案
        return draft_answer


async def process_chat_stream(user_message: str):
    """流式处理聊天请求"""
    
    # 1. 发送"规划中"状态
    yield f"data: {json.dumps({'type': 'status', 'status': 'planning', 'message': '正在规划任务...'}, ensure_ascii=False)}\n\n"
    await asyncio.sleep(0.1)
    
    # 2. 调用Planner
    plan = call_planner(user_message)
    sub_tasks = plan.get("sub_tasks", [])
    
    # 3. 发送任务清单
    todo_list = [
        {"id": task["id"], "task": task["task"], "status": "pending"}
        for task in sub_tasks
    ]
    yield f"data: {json.dumps({'type': 'todo_list', 'user_intent': plan.get('user_intent', ''), 'todos': todo_list}, ensure_ascii=False)}\n\n"
    await asyncio.sleep(0.1)
    
    # 4. 执行每个子任务
    task_results = {}
    
    for task in sub_tasks:
        task_id = task["id"]
        task_desc = task["task"]
        depends_on = task.get("depends_on", [])
        
        # 发送"正在执行"状态
        yield f"data: {json.dumps({'type': 'todo_update', 'id': task_id, 'status': 'running'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)
        
        # 收集依赖任务的结果
        context_parts = []
        for dep_id in depends_on:
            if dep_id in task_results:
                context_parts.append(f"【任务{dep_id}结果】\n{task_results[dep_id]}")
        context = "\n\n".join(context_parts)
        
        # 调用Executor分析任务
        executor_result = call_executor(task_desc)
        
        # 根据Executor结果执行
        if executor_result.get("need_tool"):
            tool_name = executor_result.get("tool_name")
            tool_params = executor_result.get("tool_params", {})
            
            # 执行工具
            result = execute_tool(tool_name, tool_params)
            
        else:
            # 不需要工具，调用Reasoner
            # 判断是否是最后一个综合任务（需要打印输入）
            is_final_task = (task_id == sub_tasks[-1]["id"]) and context
            
            if context:
                prompt = f"已收集的信息：\n{context}\n\n任务：{task_desc}\n\n请根据以上信息完成任务。"
            elif "直接回答" in task_desc:
                prompt = user_message
            else:
                prompt = f"任务：{task_desc}\n\n原始问题：{user_message}"
            
            result = call_reasoner(prompt, log_input=is_final_task)
        
        task_results[task_id] = result
        
        # 发送"已完成"状态
        yield f"data: {json.dumps({'type': 'todo_update', 'id': task_id, 'status': 'done'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)
    
    # 5. 获取初步回复
    draft_reply = task_results.get(sub_tasks[-1]["id"], "处理失败") if sub_tasks else "没有可执行的任务"
    
    # 6. 调用Verify智能体校验和优化
    final_reply = call_verify(user_message, draft_reply)
    
    # 7. 发送最终回复
    yield f"data: {json.dumps({'type': 'reply', 'content': final_reply}, ensure_ascii=False)}\n\n"
    
    # 8. 发送完成信号
    yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"


@app.post("/chat/stream")
async def chat_stream(chat_message: ChatMessage):
    """流式聊天接口"""
    return StreamingResponse(
        process_chat_stream(chat_message.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/")
async def root():
    return {"status": "ok", "message": "Manus Chat API is running"}


@app.get("/tools")
async def list_tools():
    return {"tools": TOOLS}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
