# 创建默认模特生成任务

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /models/default:
    post:
      summary: 创建默认模特生成任务
      deprecated: false
      description: |-
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
      tags: []
      parameters: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                user_id:
                  description: 用户 ID
                  type: string
                picture_url:
                  description: 用户正面照片 (支持 Data URI 或 URL)
                  type: string
                body_profile:
                  type: object
                  properties:
                    gender:
                      type: string
                    height:
                      description: '身高 (cm)，范围: 0-300'
                      type: integer
                    weight:
                      description: '体重 (kg)，范围: 0-500'
                      type: integer
                    age:
                      description: '年龄，范围: 0-150'
                      type: integer
                    skin_color:
                      description: 肤色
                      type: string
                    body_type:
                      description: 身材类型 (可选)
                      type: string
                  x-apifox-orders:
                    - gender
                    - height
                    - weight
                    - age
                    - skin_color
                    - body_type
                size:
                  type: string
              required:
                - user_id
                - picture_url
              x-apifox-orders:
                - user_id
                - picture_url
                - body_profile
                - size
            example: "{\r\n    \"user_id\": \"user-123\", // 用户 ID\r\n    \"picture_url\": \"data:image/jpeg;base64,/9j/4AAQSkZJRg...\", // 用户正面照片 (支持 Data URI 或 URL)\r\n    \"body_profile\": {\r\n        \"gender\": \"女\", // 性别: \"男\" 或 \"女\"\r\n        \"height\": 165.0, // 身高 (cm)，范围: 0-300\r\n        \"weight\": 55.0, // 体重 (kg)，范围: 0-500\r\n        \"age\": 25, // 年龄，范围: 0-150\r\n        \"skin_color\": \"浅小麦\", // 肤色\r\n        \"body_type\": \"标准\" // 身材类型 (可选)\r\n    },\r\n    \"size\": \"4:3\" // 图片比例 (可选，默认 \"4:3\")\r\n}"
      responses:
        '202':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties:
                  code:
                    type: integer
                  msg:
                    type: string
                  data:
                    type: object
                    properties:
                      task_id:
                        type: integer
                      status:
                        type: string
                      angle:
                        type: string
                    required:
                      - task_id
                      - status
                      - angle
                    x-apifox-orders:
                      - task_id
                      - status
                      - angle
                required:
                  - code
                  - msg
                  - data
                x-apifox-orders:
                  - code
                  - msg
                  - data
          headers: {}
          x-apifox-name: 成功
        '400':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties:
                  code:
                    type: integer
                  msg:
                    type: string
                  data:
                    type: 'null'
                required:
                  - code
                  - msg
                  - data
                x-apifox-orders:
                  - code
                  - msg
                  - data
          headers: {}
          x-apifox-name: 参数错误
      security:
        - bearer: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/7521011/apis/api-387350888-run
components:
  schemas: {}
  securitySchemes:
    bearer:
      type: http
      scheme: bearer
servers:
  - url: http://dev-cn.your-api-server.com
    description: 开发环境
  - url: http://test-cn.your-api-server.com
    description: 测试环境
  - url: http://prod-cn.your-api-server.com
    description: 正式环境
security: []

```

