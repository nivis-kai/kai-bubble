# 카!이! KAI Chat App

EXO KAI 金钟仁聊天泡泡 AI 应用

## 📁 项目文件

```
kai-chat-app/
├── jongin-demo.html   # 前端页面
├── server.py          # Flask 后端（AI对话 + 数据库）
├── requirements.txt    # Python 依赖
├── avatar.jpg         # 头像图片
└── README.md          # 使用说明
```

## 🚀 运行方法

### 方法1：本地运行

```bash
# 1. 进入项目目录
cd kai-chat-app

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务器
python server.py

# 4. 打开浏览器访问
# http://localhost:8080
```

### 方法2：CloudStudio 部署

1. 在 CloudStudio 新建项目
2. 上传所有文件
3. 启动命令：`python server.py`

### 方法3：GitHub + Vercel（推荐永久部署）

1. 创建 GitHub 仓库，上传所有文件
2. 在 Vercel 导入项目
3. 设置完成后获得永久链接

## ✨ 功能

- 🤖 AI 智能对话（DeepSeek API）
- 💬 韩中双语翻译
- 💾 SQLite 数据库保存对话历史
- 📱 iPhone 风格界面
- 🎨 渐变紫色主题

## ⚙️ 配置

如需更换 AI API Key，编辑 `server.py` 中的：
```python
api_key = "your-api-key-here"
```

## 📝 数据库

对话历史保存在 `chat_history.db` 文件中。
