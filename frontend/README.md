# 前端使用说明

## 🚀 快速开始

### 前提条件
确保后端服务正在运行：
```bash
# 在 ranking_sys 根目录下
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 运行前端

有多种方式可以运行前端：

#### 方法 1: VS Code Live Server（推荐）
1. 在 VS Code 中安装 "Live Server" 插件
2. 右键点击 `index.html`
3. 选择 "Open with Live Server"
4. 浏览器会自动打开页面

#### 方法 2: Python HTTP Server
```bash
# 在 frontend 目录下
cd frontend
python -m http.server 5500
```
然后访问：http://localhost:5500

#### 方法 3: 直接打开文件
双击 `index.html` 文件在浏览器中打开（某些浏览器可能因 CORS 限制无法使用）

## 📁 文件说明

- `index.html` - 主页面结构
- `style.css` - 样式表（紫色渐变主题）
- `app.js` - 交互逻辑和 API 通信

## 🔧 配置

如果后端不在 `localhost:8000`，需要修改 `app.js` 中的 API 地址：

```javascript
// 找到这一行（约在第 145 行）
const response = await fetch('http://localhost:8000/api/v1/rank', {
```

## ✨ 功能

- ✅ 任务描述输入
- ✅ 动态添加/删除候选项
- ✅ 表单验证
- ✅ 实时结果展示
- ✅ 处理时间显示
