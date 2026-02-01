# Manus Clone

一个模仿 Manus 的 AI Agent 系统，基于 DeepSeek API 构建，具备任务规划、工具调用和答案校验能力。

## 功能特点

- **多智能体架构**：Planner → Executor → Reasoner → Verify 协同工作
- **任务规划**：自动将复杂问题拆分为可执行的子任务
- **工具调用**：支持网络搜索等外部工具
- **实时反馈**：前端实时显示任务执行进度
- **答案校验**：Verify 智能体对最终答案进行质量把关

## 系统架构

```
用户输入
    ↓
[Planner] 分析意图，拆分子任务
    ↓
[Executor] 分析每个子任务，决定调用什么工具
    ↓
[Tool/Reasoner] 执行工具或直接生成回答
    ↓
[Verify] 校验和优化最终答案
    ↓
返回给用户
```

## 智能体说明

| 智能体 | 模型 | 职责 |
|--------|------|------|
| Planner | deepseek-chat | 理解用户意图，将请求拆分为子任务 |
| Executor | deepseek-chat | 分析子任务，决定使用什么工具和参数 |
| Reasoner | deepseek-reasoner | 深度思考，生成高质量回答 |
| Verify | deepseek-chat | 校验答案质量，优化表达 |

## 可用工具

| 工具名 | 功能 |
|--------|------|
| web_search | 使用 DuckDuckGo 搜索互联网信息 |

## 项目结构

```
manus-clone/
├── frontend/                # 前端代码
│   ├── index.html          # 页面结构
│   ├── styles.css          # 样式文件
│   └── script.js           # 交互逻辑
├── backend/                 # 后端代码
│   ├── main.py             # FastAPI 主程序
│   ├── prompts.py          # 智能体提示词
│   ├── tools.py            # 工具定义与实现
│   ├── requirements.txt    # Python 依赖
│   └── .env                # 环境变量配置（需自行创建）
└── README.md
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/19068536105-a11y/manus-clone.git
cd manus-clone
```

### 2. 配置后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 创建环境变量文件
cp .env.example .env  # 或手动创建
```

编辑 `.env` 文件，填入你的配置：

```
DEEPSEEK_API_KEY=你的DeepSeek_API_Key

# 如果需要代理访问 DuckDuckGo（国内用户）
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

### 3. 启动后端服务

```bash
python main.py
```

服务将在 http://localhost:8000 运行

### 4. 打开前端页面

直接在浏览器中打开 `frontend/index.html`，或使用：

```bash
open frontend/index.html
```

## 使用示例

在聊天框中输入问题，例如：

- "分析 Vue 和 React 的区别"
- "帮我调研一下特斯拉这家公司"
- "搜索 Python 最新版本"

系统会自动：
1. 显示"正在规划任务..."
2. 展示任务清单（Todo List）
3. 逐个执行任务并打勾
4. 显示最终回答

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/chat/stream` | POST | 流式聊天接口（SSE） |
| `/tools` | GET | 获取可用工具列表 |
| `/` | GET | 健康检查 |

## 技术栈

**前端**
- HTML5 / CSS3 / JavaScript
- Server-Sent Events (SSE)

**后端**
- Python 3.9+
- FastAPI
- DeepSeek API
- DuckDuckGo Search (ddgs)

## 注意事项

1. **API Key 安全**：不要将 `.env` 文件上传到 GitHub
2. **网络代理**：国内用户使用搜索功能需要配置代理
3. **API 额度**：注意 DeepSeek API 的调用额度

## License

MIT
