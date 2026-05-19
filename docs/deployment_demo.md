# CampRank 公开 Demo 部署

这份文档用于把 CampRank 部署成公开可访问的 Demo：前端放到 Vercel，后端放到 Render，数据只使用公开样例数据。

## 1. 部署后端到 Render

在 Render 新建 Web Service，连接 GitHub 仓库：

```text
https://github.com/dileonardoliebel813-jpg/camp-rank
```

Render 配置：

```text
Name: camp-rank-api
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: python scripts/init_db.py && python scripts/seed_sample_data.py && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

部署成功后，先打开后端健康检查地址：

```text
https://你的-render-后端地址/health
```

正常结果应包含：

```json
{"status":"ok","project":"CampRank"}
```

## 2. 部署前端到 Vercel

在 Vercel 新建 Project，连接同一个 GitHub 仓库。

Vercel 配置：

```text
Framework Preset: Vite
Root Directory: frontend
Build Command: npm run build
Output Directory: dist
```

添加环境变量：

```text
VITE_API_BASE_URL=https://你的-render-后端地址
```

保存后重新 Deploy。

## 3. 验证 Demo

打开 Vercel 生成的网站地址，检查：

- 首页可以选择预算、场景和侧重点。
- 点击“帮我选 3 款”后能进入推荐页。
- 推荐页能展示 3 个以内购买方案。
- 切换“价格优先”“售后保障”“防水/防风”“步行携带”等组合后，推荐说明会变化。
- 浏览器控制台没有 API 地址错误或 CORS 错误。

也可以直接访问后端接口确认：

```text
https://你的-render-后端地址/api/recommendations
```

## 4. 数据安全检查

推送前确认不要提交这些文件：

```text
backend/data/real_samples/
backend/data/import_reports/
backend/camp_rank.db
*.db
*.sqlite
*.sqlite3
*.log
frontend/dist/
node_modules/
```

当前 `.gitignore` 已经排除了这些路径。提交前仍建议运行：

```bash
git status --short
git ls-files | rg "(real_samples|import_reports|camp_rank\.db|\.db$|\.sqlite|\.log$|dist/|node_modules/)"
```

第二条命令如果没有输出，就表示这些本地数据没有被 Git 跟踪。

## 5. Demo 与正式产品的区别

Demo 阶段：

- 使用 SQLite。
- Render 重启或重新部署后，样例数据可以重新初始化。
- 后端 CORS 暂时允许所有来源，方便 Vercel Demo 调用。

正式产品阶段建议：

- 换成 PostgreSQL。
- 把 CORS 限制为正式前端域名。
- 增加后台数据导入权限控制。
- 只发布经过脱敏和授权的数据。
