# 全栈开发指南

## 项目架构

本项目采用前后端分离架构。

> 前端使用 React，后端使用 Node.js。

## 技术栈

### 技术选型

| 层级 | 技术 | 说明
| 前端 | React + TypeScript | 用户界面
| 后端 | Express | API 服务
| 数据库 | PostgreSQL | 数据存储
| 部署 | Docker | 容器化

## Docker 配置

Docker Compose 配置文件：

```yaml
version: 3.8
services:
web:
build: .
ports:
8080:80
environment:
NODE_ENV: production
db:
image: postgres:15
environment:
POSTGRES_DB: myapp
POSTGRES_PASSWORD: secret
volumes:
dbdata:/var/lib/postgresql/data
volumes:
dbdata:
```

## API 示例代码

```tsx
import express from 'express';
import { Pool } from 'pg';
const app = express();
const pool = new Pool({
connectionString: process.env.DATABASE_URL,
});
app.get('/api/users', async (req, res) => {
try {
const result = await pool.query('SELECT * FROM users');
res.json(result.rows);
} catch (err) {
res.status(500).json({ error: 'Database error' });
}
});
app.listen(3000, () => {
console.log('Server running on port 3000');
});
```

## 开发步骤

1.

初始化项目结构

2.

配置开发环境

3.

编写后端 API

4.

开发前端界面

5.

部署到生产环境

## JSON 配置

{
"appName": "fullstack-app",
"port": 3000,
"database": {
"host": "localhost",
"port": 5432,
"name": "myapp"
}
}

## 注意事项

> 开发时注意数据库连接池的管理。
> 生产环境务必使用环境变量管理敏感信息。
