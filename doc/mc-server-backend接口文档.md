---
title: 默认模块
language_tabs:
  - shell: Shell
  - http: HTTP
  - javascript: JavaScript
  - ruby: Ruby
  - python: Python
  - php: PHP
  - java: Java
  - go: Go
toc_footers: []
includes: []
search: true
code_clipboard: true
highlight_theme: darkula
headingLevel: 2
generator: "@tarslib/widdershins v4.0.30"

---

# 默认模块

Base URLs:

* <a href="http://localhost:5000">开发环境: http://localhost:5000</a>

* <a href="https://qqbot.netcpu.top:5000">正式环境: https://qqbot.netcpu.top:5000</a>

# Authentication

# 服务器监控

## GET 获取服务器状态信息

GET /monitor/server-info/{server_id}

### 请求参数

|名称|位置|类型|必选|说明|
|---|---|---|---|---|
|server_id|path|integer| 是 |服务器ID|
|start_time|query|string| 是 |开始时间 (YYYY-MM-DD HH:mm:ss)|
|end_time|query|string| 是 |结束时间 (YYYY-MM- HH:mm:ss)|
|time_period|query|int| 否 |返回指标数据时间间隔，单位小时,默认1h|

> 返回示例

> 200 Response

```
{"code":0,"data":{"historyStatusList":[{"maxPlayers":0,"monitorTime":"string","onlinePlayers":0,"ping":0,"status":"string"}],"info":{"description":"string","isMonitored":true,"maxPlayers":0,"serverAddress":"string","serverId":0,"serverName":"string","serverType":"string","serverVersion":"string"}},"message":"string"}
```

> 404 Response

```json
{}
```

### 返回结果

|状态码|状态码含义|说明|数据模型|
|---|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|服务器状态信息|Inline|
|404|[Not Found](https://tools.ietf.org/html/rfc7231#section-6.5.4)|服务器未找到|Inline|

### 返回数据结构

状态码 **200**

|名称|类型|必选|约束|中文名|说明|
|---|---|---|---|---|---|
|» code|integer|true|none||none|
|» data|object|true|none||none|
|»» historyStatusList|[object]|true|none||none|
|»»» maxPlayers|integer|true|none||none|
|»»» monitorTime|string|true|none||none|
|»»» onlinePlayers|integer|true|none||none|
|»»» ping|integer|true|none||none|
|»»» status|string|true|none||none|
|»» info|object|true|none||none|
|»»» description|string|true|none||none|
|»»» isMonitored|boolean|true|none||none|
|»»» maxPlayers|integer|true|none||none|
|»»» serverAddress|string|true|none||none|
|»»» serverId|integer|true|none||none|
|»»» serverName|string|true|none||none|
|»»» serverType|string|true|none||none|
|»»» serverVersion|string|true|none||none|
|» message|string|true|none||none|

# 数据模型

