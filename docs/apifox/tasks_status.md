# 查询任务状态

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /tasks/{task_id}:
    get:
      summary: 查询任务状态
      deprecated: false
      description: |-
        ## task_id
        成功创建生图任务会返回task_id

        ## status：
        | 状态 | 描述 |
        |------|------|
        | submitted | 任务已提交，等待处理 |
        | processing | 任务处理中 |
        | completed | 任务完成，可获取图片 |
        | failed | 任务失败，查看 error_message |
      tags: []
      parameters:
        - name: task_id
          in: path
          description: ''
          required: true
          schema:
            type: string
      responses:
        '200':
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
                      progress:
                        type: integer
                      type:
                        type: string
                      angle:
                        type: string
                      image:
                        type: object
                        properties:
                          image_base64:
                            type: string
                          image_url:
                            type: string
                        required:
                          - image_base64
                          - image_url
                        x-apifox-orders:
                          - image_base64
                          - image_url
                      error_message:
                        type: string
                    required:
                      - task_id
                      - status
                      - progress
                      - type
                      - angle
                      - image
                      - error_message
                    x-apifox-orders:
                      - task_id
                      - status
                      - progress
                      - type
                      - angle
                      - image
                      - error_message
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
          x-apifox-name: 任务不存在
        '422':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties:
                  detail:
                    type: array
                    items:
                      type: object
                      properties:
                        loc:
                          type: array
                          items:
                            oneOf:
                              - type: string
                              - type: integer
                        msg:
                          type: string
                        type:
                          type: string
                      x-apifox-orders:
                        - loc
                        - msg
                        - type
                required:
                  - detail
                x-apifox-orders:
                  - detail
          headers: {}
          x-apifox-name: 参数错误
        '500':
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
          x-apifox-name: 服务器错误
      security: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/7521011/apis/api-387353312-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: http://dev-cn.your-api-server.com
    description: 开发环境
  - url: http://test-cn.your-api-server.com
    description: 测试环境
  - url: http://prod-cn.your-api-server.com
    description: 正式环境
security: []

```

