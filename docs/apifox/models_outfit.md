# 创建穿搭生成任务

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /models/outfit:
    post:
      summary: 创建穿搭生成任务
      deprecated: false
      description: |-

        将服装单品"穿"到数字模特上，生成穿搭效果图。支持传入 1-5 张服装单品图片 URL

        ### outfit_image_urls可以传入oss路径或base64格式：
        {
          "outfit_image_urls": [
            "https://example.com/top.jpg",
            "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
          ]
        }
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
                angle:
                  type: string
                outfit_images:
                  type: array
                  items:
                    type: string
                  description: 服装单品图片列表 (1-5 张，支持 Data URI 或 URL)
                size:
                  type: string
              required:
                - user_id
                - base_model_task_id
                - angle
                - outfit_images
              x-apifox-orders:
                - user_id
                - base_model_task_id
                - angle
                - outfit_images
                - size
            example: "{\r\n  \"user_id\": \"user-123\",                      // 用户 ID\r\n  \"base_model_task_id\": \"task_abc123def\",     // 基础模特任务 ID (创建默认模特返回的 task_id)\r\n  \"angle\": \"front\",                           // 视角: \"front\" / \"side\" / \"back\"\r\n  \"outfit_images\": [                          // 服装单品图片列表 (1-5 张，支持 Data URI 或 URL)\r\n    \"https://example.com/top.jpg\",            // 上衣图片 URL\r\n    \"https://example.com/pants.jpg\",          // 裤子图片 URL\r\n    \"data:image/jpeg;base64,/9j/4AAQ...\"      // 或 Base64 Data URI\r\n  ],\r\n  \"size\": \"4:3\"                               // 图片比例 (可选，默认 \"4:3\")\r\n}"
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
      security:
        - bearer: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/7521011/apis/api-387352833-run
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

