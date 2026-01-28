# 创建模特编辑任务

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /models/edit:
    post:
      summary: 创建模特编辑任务
      deprecated: false
      description: 在已有默认模特基础上进行编辑（如调整发型、身材等）
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
                base_model_task_id:
                  description: 基础模特任务 ID (创建默认模特返回的 task_id)
                  type: string
                edit_instructions:
                  description: 编辑指令
                  type: string
                size:
                  type: string
              required:
                - user_id
                - base_model_task_id
                - edit_instructions
                - size
              x-apifox-orders:
                - user_id
                - base_model_task_id
                - edit_instructions
                - size
            example: "{\r\n  \"user_id\": \"user-123\",                      // 用户 ID\r\n  \"base_model_task_id\": \"task_abc123def\",     // 基础模特任务 ID (创建默认模特返回的 task_id)\r\n  \"edit_instructions\": \"将发型改为短发，肤色调亮一些\",  // 编辑指令\r\n  \"size\": \"4:3\"                               // 图片比例 (可选，默认 \"4:3\")\r\n}"
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
        '404':
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
          x-apifox-name: 未找到
      security:
        - bearer: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/7521011/apis/api-387352679-run
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

