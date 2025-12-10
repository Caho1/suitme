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
"""


# ============== 默认模特生成 ==============

DEFAULT_MODEL_PROMPT = """
为图片上的人物生成一张高分辨率的影棚数字时尚模特照片，模特正面站立，全身入镜（从头到脚），背景为浅灰色无缝背景。 
模特性别为 {gender}，身高约 {height_cm} cm，体重约 {weight_kg} kg，年龄 {age} 岁，肤色为 {skin_tone}，身材为 {body_shape_text}。 
只穿着一件纯白色短袖 T 恤和蓝色牛仔裤，不要任何额外配饰。 
采用中远景构图，清晰展示模特的全身，包括腿部和脚部。 
灯光柔和、有层次感，产生轻微阴影和空间深度，但不要强烈对比。 
人物面部五官需要保持高度一致，以便多次生成时形象统一。 
画面宽高比为 4:3。

"""

# ============== 模特编辑 ==============

EDIT_MODEL_PROMPT = """
根据以下编辑指令对已有的数字模特形象进行精细修改：

编辑指令：
{edit_instructions}

编辑原则（务必严格遵守）：
- 仅修改指令中**明确提到**需要变更的特征（例如：身高、体重、年龄、肤色、身材、服装款式与颜色、配饰、背景等）。
- 对于未在指令中提到的特征，必须与原始模特形象保持高度一致，包括但不限于：
  性别、面部特征与五官、整体气质、发型、姿势与肢体结构、机位与视角、构图、灯光风格、画面风格与清晰度，以及宽高比（如无特别说明则为 4:3）。
- 当编辑指令中明确要求修改身高 / 体重 / 年龄 / 肤色 / 身材等属性时，只在这些属性上做出合理、自然的一致性调整，同时保持人物面部特征与身份仍可被识别为同一人。
- 不要新增指令中未提到的物体、配饰或场景元素；不要随意改变整体画风或场景氛围。
- 不要降低画质或改变分辨率，除非编辑指令中明确要求。

"""


# ============== 穿搭生成 ==============

OUTFIT_PROMPT = """
根据提供的数字模特参考图和服装参考图，将服装单品自然地穿到模特身上，生成 {angle} 视角的完整穿搭效果图。

生成要求：
- 以参考图中的数字模特为基础，保持模特的面部特征、身材比例和整体身份一致，不要更换人物。
- 自动识别服装参考图中的服装类型、版型、长度、材质和主要细节，并真实还原到模特身上。
- 服装应与身体自然贴合，呈现合理的褶皱、垂坠感和受力效果，避免变形、穿模或明显的不合身。
- 在不改变机位和大致构图风格的前提下，可以轻微调整模特姿势，以更好展示服装细节。
- 除了需要展示的服装单品外，不要额外添加未提供的服装或配饰。
- 背景和光影风格应尽量与原始模特参考图保持一致，使画面自然统一、观感真实清晰。
"""


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


def build_outfit_prompt(angle: str) -> str:
    """
    构建穿搭生成的 Prompt
    
    Args:
        angle: 视角 (front/side/back)
    
    Returns:
        str: 格式化后的 Prompt
    """
    angle_text = ANGLE_TEXT_MAP.get(angle, "正面")
    
    return OUTFIT_PROMPT.format(angle=angle_text)
