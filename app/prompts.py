"""
提示词模板配置

集中管理所有 AI 生图的 Prompt 模板，方便修改和维护。
使用 Python 字符串模板，支持变量替换。

变量说明：
- {gender}: 性别（男性/女性）
- {height_cm}: 身高 (cm)
- {weight_kg}: 体重 (kg)
- {age}: 年龄
- {skin_tone}: 肤色
- {body_shape}: 身材类型（可选）
- {edit_instructions}: 编辑指令
- {angle}: 视角（正面/侧面/背面）
- {outfit_description}: 服装描述（可选）
"""


# ============== 默认模特生成 ==============

DEFAULT_MODEL_PROMPT = """
Generate a front-facing, full-body studio photograph of a digital fashion model with the following attributes:
- Gender: {gender}
- Height: {height_cm} cm
- Weight: {weight_kg} kg
- Age: {age} years old
- Skin tone: {skin_tone}
- Body shape: {body_shape_text}
- Background: light gray seamless backdrop.
- Pose & framing: standing, full body visible from head to feet in a medium-long shot.
- Clothing: plain white short-sleeve T-shirt and blue jeans, no extra accessories.
- Lighting: soft, layered, with gentle shadows and clear depth.
- Consistency: keep the model’s facial features highly consistent.
- Aspect ratio: 4:3.
"""


# ============== 模特编辑 ==============

EDIT_MODEL_PROMPT = """根据以下指令编辑数字模特形象：{edit_instructions}。
请保持人物身份一致，仅修改指定的特征。"""


# ============== 穿搭生成 ==============

OUTFIT_PROMPT = """将服装穿到数字模特身上，生成{angle}视角的穿搭效果图。{outfit_description_text}
请保持模特身份一致，自然地展示服装穿着效果。"""


# ============== 视角映射 ==============

ANGLE_TEXT_MAP = {
    "front": "正面",
    "side": "侧面",
    "back": "背面",
}


# ============== 辅助函数 ==============

def build_default_model_prompt(
    gender: str,
    height_cm: float,
    weight_kg: float,
    age: int,
    skin_tone: str,
    body_shape: str | None = None,
) -> str:
    """
    构建默认模特生成的 Prompt
    
    Args:
        gender: 性别 (male/female)
        height_cm: 身高 (cm)
        weight_kg: 体重 (kg)
        age: 年龄
        skin_tone: 肤色
        body_shape: 身材类型（可选）
    
    Returns:
        str: 格式化后的 Prompt
    """
    gender_text = "男性" if gender == "male" else "女性"
    body_shape_text = f"，身材类型：{body_shape}" if body_shape else ""
    
    return DEFAULT_MODEL_PROMPT.format(
        gender=gender_text,
        height_cm=height_cm,
        weight_kg=weight_kg,
        age=age,
        skin_tone=skin_tone,
        body_shape_text=body_shape_text,
    )


def build_edit_model_prompt(edit_instructions: str) -> str:
    """
    构建模特编辑的 Prompt
    
    Args:
        edit_instructions: 编辑指令
    
    Returns:
        str: 格式化后的 Prompt
    """
    return EDIT_MODEL_PROMPT.format(edit_instructions=edit_instructions)


def build_outfit_prompt(
    angle: str,
    outfit_description: str | None = None,
) -> str:
    """
    构建穿搭生成的 Prompt
    
    Args:
        angle: 视角 (front/side/back)
        outfit_description: 服装描述（可选）
    
    Returns:
        str: 格式化后的 Prompt
    """
    angle_text = ANGLE_TEXT_MAP.get(angle, "正面")
    outfit_description_text = f"服装描述：{outfit_description}。" if outfit_description else ""
    
    return OUTFIT_PROMPT.format(
        angle=angle_text,
        outfit_description_text=outfit_description_text,
    )
