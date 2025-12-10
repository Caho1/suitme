# Suitme API 文档

## 基础信息

- **Base URL**: `http://localhost:8000`
- **Content-Type**: `application/json`
- **认证方式**: Bearer Token

## 认证

所有 API 请求都需要在 Header 中携带 Bearer Token：

```
Authorization: Bearer <your-token>
```

Token 在 `.env` 文件中配置：
```
API_AUTH_TOKEN=your-secret-token-here
```

如果 Token 无效，返回 401 错误：
```json
{
  "code": 1005,
  "msg": "无效的认证 Token",
  "data": null
}
```

## 启动服务

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 启动服务
uv run uvicorn main:app --reload
```

服务启动后可访问自动生成的 Swagger 文档：`http://localhost:8000/docs`

---

## API 列表

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /models/default | 创建默认模特 |
| POST | /models/edit | 编辑模特 |
| POST | /models/outfit | 穿搭生成 |
| GET | /tasks/{task_id} | 查询任务状态 |

---

## 通用参数

### 图片尺寸比例 (size)

所有生成接口都支持 `size` 参数，用于指定生成图片的比例：

| 值 | 描述 |
|------|------|
| `1:1` | 正方形 |
| `2:3` | 竖版 |
| `3:2` | 横版 |
| `3:4` | 竖版 |
| `4:3` | 横版 (默认) |
| `4:5` | 竖版 |
| `5:4` | 横版 |
| `9:16` | 手机竖屏 |
| `16:9` | 宽屏 |
| `21:9` | 超宽屏 |

---

## 1. 创建默认模特

**POST** `/models/default`

根据用户照片和身体参数生成默认数字模特。

### 请求体

```jsonc
{
  "request_id": "req-001",           // 请求唯一标识
  "user_id": "user-123",             // 用户 ID
  "user_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",  // 用户正面照片 (支持 Data URI 或 URL)
  "body_profile": {
    "gender": "female",              // 性别: "male" 或 "female"
    "height_cm": 165.0,              // 身高 (cm)，范围: 0-300
    "weight_kg": 55.0,               // 体重 (kg)，范围: 0-500
    "age": 25,                       // 年龄，范围: 0-150
    "skin_tone": "fair",             // 肤色
    "body_shape": "slim"             // 身材类型 (可选)
  },
  "size": "4:3"                      // 图片比例 (可选，默认 "4:3")
}
```

### 请求参数说明

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| request_id | string | ✅ | 请求唯一标识 |
| user_id | string | ✅ | 用户 ID |
| user_image | string | ✅ | 用户正面照片，支持 Data URI 或 URL |
| body_profile | object | ✅ | 用户身体参数 |
| size | string | ❌ | 图片比例，默认 "4:3" |

**body_profile 字段：**

| 字段 | 类型 | 必填 | 约束 | 描述 |
|------|------|------|------|------|
| gender | string | ✅ | "male" 或 "female" | 性别 |
| height_cm | float | ✅ | 0 < x ≤ 300 | 身高 (cm) |
| weight_kg | float | ✅ | 0 < x ≤ 500 | 体重 (kg) |
| age | int | ✅ | 0 < x ≤ 150 | 年龄 |
| skin_tone | string | ✅ | 非空 | 肤色 |
| body_shape | string | ❌ | - | 身材类型 |

### 成功响应 (202 Accepted)

```json
{
  "code": 0,
  "msg": "accepted",
  "data": {
    "task_id": "task_abc123def",
    "status": "submitted",
    "angle": null
  }
}
```

### 错误响应

**400 Bad Request** - 参数错误
```json
{
  "code": 1001,
  "msg": "图片必须是有效的 Data URI 格式",
  "data": null
}
```

### cURL 示例

```bash
curl -X POST "http://localhost:8000/models/default" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-token-here" \
  -d '{
    "request_id": "req-001",
    "user_id": "user-123",
    "user_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "body_profile": {
      "gender": "female",
      "height_cm": 165.0,
      "weight_kg": 55.0,
      "age": 25,
      "skin_tone": "fair",
      "body_shape": "slim"
    },
    "size": "4:3"
  }'
```

---

## 2. 编辑模特

**POST** `/models/edit`

在已有默认模特基础上进行编辑（如调整发型、身材等）。

### 请求体

```jsonc
{
  "request_id": "req-002",                    // 请求唯一标识
  "user_id": "user-123",                      // 用户 ID
  "base_model_task_id": "task_abc123def",     // 基础模特任务 ID (创建默认模特返回的 task_id)
  "edit_instructions": "将发型改为短发，肤色调亮一些",  // 编辑指令
  "size": "4:3"                               // 图片比例 (可选，默认 "4:3")
}
```

### 请求参数说明

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| request_id | string | ✅ | 请求唯一标识 |
| user_id | string | ✅ | 用户 ID |
| base_model_task_id | string | ✅ | 基础模特任务 ID (格式: task_xxxxxxx) |
| edit_instructions | string | ✅ | 编辑指令 |
| size | string | ❌ | 图片比例，默认 "4:3" |

### 成功响应 (202 Accepted)

```json
{
  "code": 0,
  "msg": "accepted",
  "data": {
    "task_id": "task_xyz789abc",
    "status": "submitted",
    "angle": null
  }
}
```

### 错误响应

**404 Not Found** - 基础模特不存在
```json
{
  "code": 1003,
  "msg": "基础模特任务不存在: task_invalid",
  "data": null
}
```

### cURL 示例

```bash
curl -X POST "http://localhost:8000/models/edit" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-token-here" \
  -d '{
    "request_id": "req-002",
    "user_id": "user-123",
    "base_model_task_id": "task_abc123def",
    "edit_instructions": "将发型改为短发",
    "size": "4:3"
  }'
```

---

## 3. 穿搭生成

**POST** `/models/outfit`

将服装单品"穿"到数字模特上，生成穿搭效果图。支持传入 1-5 张服装单品图片。

### 请求体

```jsonc
{
  "request_id": "req-003",                    // 请求唯一标识
  "user_id": "user-123",                      // 用户 ID
  "base_model_task_id": "task_abc123def",     // 基础模特任务 ID (创建默认模特返回的 task_id)
  "angle": "front",                           // 视角: "front" / "side" / "back"
  "outfit_images": [                          // 服装单品图片列表 (1-5 张，支持 Data URI 或 URL)
    "https://example.com/top.jpg",            // 上衣图片 URL
    "https://example.com/pants.jpg",          // 裤子图片 URL
    "data:image/jpeg;base64,/9j/4AAQ..."      // 或 Base64 Data URI
  ],
  "size": "4:3"                               // 图片比例 (可选，默认 "4:3")
}
```

### 请求参数说明

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| request_id | string | ✅ | 请求唯一标识 |
| user_id | string | ✅ | 用户 ID |
| base_model_task_id | string | ✅ | 基础模特任务 ID (格式: task_xxxxxxx) |
| angle | string | ✅ | 视角: "front" / "side" / "back" |
| outfit_images | array | ✅ | 服装单品图片列表 (1-5 张，支持 Data URI 或 URL) |
| size | string | ❌ | 图片比例，默认 "4:3" |

### 成功响应 (202 Accepted)

```json
{
  "code": 0,
  "msg": "accepted",
  "data": {
    "task_id": "task_outfit123",
    "status": "submitted",
    "angle": "front"
  }
}
```

### 错误响应

**400 Bad Request** - angle 参数无效
```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["body", "angle"],
      "msg": "Input should be 'front', 'side' or 'back'",
      "input": "invalid"
    }
  ]
}
```

**400 Bad Request** - 图片数量超出限制
```json
{
  "detail": [
    {
      "type": "too_long",
      "loc": ["body", "outfit_images"],
      "msg": "List should have at most 5 items after validation, not 6"
    }
  ]
}
```

**404 Not Found** - 基础模特不存在
```json
{
  "code": 1003,
  "msg": "基础模特任务不存在: task_invalid",
  "data": null
}
```

### cURL 示例

```bash
curl -X POST "http://localhost:8000/models/outfit" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-token-here" \
  -d '{
    "request_id": "req-003",
    "user_id": "user-123",
    "base_model_task_id": "task_abc123def",
    "angle": "front",
    "outfit_images": [
      "https://example.com/top.jpg",
      "https://example.com/pants.jpg"
    ],
    "size": "4:3"
  }'
```

---

## 4. 查询任务状态

**GET** `/tasks/{task_id}`

查询任务的当前状态和结果。

### 路径参数

| 参数 | 类型 | 描述 |
|------|------|------|
| task_id | string | 任务 ID (格式: task_xxxxxxx) |

### 成功响应 (200 OK)

**任务进行中：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "task_id": "task_abc123def",
    "status": "processing",
    "progress": 50,
    "type": "default",
    "angle": null,
    "image": null,
    "error_message": null
  }
}
```

**任务完成：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "task_id": "task_abc123def",
    "status": "completed",
    "progress": 100,
    "type": "default",
    "angle": null,
    "image": {
      "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
      "image_url": "https://oss.example.com/images/xxx.jpg"
    },
    "error_message": null
  }
}
```

**任务失败：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "task_id": "task_abc123def",
    "status": "failed",
    "progress": 0,
    "type": "default",
    "angle": null,
    "image": null,
    "error_message": "timeout"
  }
}
```

### 错误响应

**404 Not Found** - 任务不存在
```json
{
  "code": 1003,
  "msg": "任务不存在: task_invalid",
  "data": null
}
```

### cURL 示例

```bash
curl -X GET "http://localhost:8000/tasks/task_abc123def" \
  -H "Authorization: Bearer your-secret-token-here"
```

---

## 任务状态说明

| 状态 | 描述 |
|------|------|
| submitted | 任务已提交，等待处理 |
| processing | 任务处理中 |
| completed | 任务完成，可获取图片 |
| failed | 任务失败，查看 error_message |

---

## 任务类型说明

| 类型 | 描述 |
|------|------|
| default | 默认模特生成 |
| edit | 模特编辑 |
| outfit | 穿搭生成 |

---

## 错误码说明

| code | HTTP Status | 描述 |
|------|-------------|------|
| 0 | 200/202 | 成功 |
| 1001 | 400 | 参数错误 |
| 1002 | 502 | Apimart 调用失败 |
| 1003 | 404 | 任务不存在 |
| 1004 | 500 | 内部异常 |
| 1005 | 401 | 认证失败（无效 Token） |

---

## 测试用 Base64 图片

以下是一个 1x1 像素的 PNG 图片 Data URI，可用于测试：

```
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==
```

---

## 完整测试流程

1. **创建默认模特**
```bash
curl -X POST "http://localhost:8000/models/default" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-token-here" \
  -d '{
    "request_id": "test-001",
    "user_id": "user-001",
    "user_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "body_profile": {
      "gender": "female",
      "height_cm": 165,
      "weight_kg": 55,
      "age": 25,
      "skin_tone": "fair"
    },
    "size": "4:3"
  }'
```

2. **查询任务状态** (假设返回 task_id="task_abc123")
```bash
curl -X GET "http://localhost:8000/tasks/task_abc123" \
  -H "Authorization: Bearer your-secret-token-here"
```

3. **编辑模特** (需要先有完成的默认模特任务)
```bash
curl -X POST "http://localhost:8000/models/edit" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-token-here" \
  -d '{
    "request_id": "test-002",
    "user_id": "user-001",
    "base_model_task_id": "task_abc123",
    "edit_instructions": "改为短发",
    "size": "4:3"
  }'
```

4. **穿搭生成**
```bash
curl -X POST "http://localhost:8000/models/outfit" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-token-here" \
  -d '{
    "request_id": "test-003",
    "user_id": "user-001",
    "base_model_task_id": "task_abc123",
    "angle": "front",
    "outfit_images": [
      "https://example.com/top.jpg",
      "https://example.com/pants.jpg"
    ],
    "size": "4:3"
  }'
```
