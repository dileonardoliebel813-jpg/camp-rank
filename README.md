# CampRank

CampRank 是一个户外帐篷购买风险辅助决策工具。它根据预算、使用场景、用户侧重点、商品参数、价格、售后文本和评论风险，帮助用户从候选商品中快速看到 3 个购买方案。

> 当前推荐只作为购买风险参考，不等同于专业户外性能测评。

## 功能

- 按预算、场景和偏好筛选帐篷候选商品
- 输出“首选方案 / 低价备选 / 谨慎选择”三类建议
- 标注“完全满足 / 部分满足 / 补位参考”
- 展示价格、评论风险、售后和商品参数依据
- 不编造缺失的重量、防水、防风、收纳等参数

## 技术栈

- 后端：FastAPI + SQLAlchemy + SQLite
- 前端：React + Vite
- 测试：pytest + Vite build

## 本地启动

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python scripts/init_db.py
python scripts/seed_sample_data.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开：

```text
http://127.0.0.1:5173/
```

## 常用命令

运行全量检查：

```bash
python scripts/check_all.py
```

单独运行后端测试：

```bash
cd backend
python -m pytest
```

单独构建前端：

```bash
cd frontend
npm run build
```

## 数据边界

- 本仓库不提交本地数据库、评论样本、导入报告、日志、构建产物和依赖目录
- 商品参数仅来自已接入的真实页面参数或用户提供的整理文件
- 缺失字段会在页面中提示“待确认”，不会为了展示效果补造
- 当前推荐依据以京东商品价格、售后文本、评论风险和页面标称参数为主

## 目录结构

```text
backend/   FastAPI 后端、数据模型、评分和推荐逻辑
frontend/  React 前端页面和组件
scripts/   项目级检查和数据处理脚本
docs/      数据流程、字段约定和项目文档
```
