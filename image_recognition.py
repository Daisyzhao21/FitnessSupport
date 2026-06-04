"""
食物图片识别模块
支持：通义千问VL、OpenAI GPT-4V
"""

import os
import base64
import requests
import json

class FoodImageRecognizer:
    def __init__(self, api_type="qwen", api_key=None):
        self.api_type = api_type
        
        if api_type == "qwen":
            self.api_key = api_key or os.environ.get("QWEN_API_KEY")
            self.api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        elif api_type == "openai":
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
            self.api_url = "https://api.openai.com/v1/chat/completions"
        else:
            raise ValueError(f"Unsupported API type: {api_type}")
    
    def encode_image(self, image_path):
        """将图片编码为 base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def recognize_food(self, image_path):
        """识别图片中的食物并返回营养信息"""
        
        # 获取图片的 base64 编码
        base64_image = self.encode_image(image_path)
        
        # 构建提示词
        prompt = """请识别这张图片中的所有食物，并以 JSON 格式返回结果。
        对于每种食物，请提供：
        1. 食物名称（中文）
        2. 预估重量（克）
        3. 热量（千卡）
        4. 蛋白质（克）
        5. 碳水化合物（克）
        6. 脂肪（克）
        
        请按以下格式返回：
        {
            "foods": [
                {
                    "name": "食物名称",
                    "weight": 预估重量,
                    "calories": 热量,
                    "protein": 蛋白质,
                    "carbs": 碳水化合物,
                    "fat": 脂肪
                }
            ],
            "total_calories": 总热量,
            "total_protein": 总蛋白质
        }
        
        请只返回 JSON，不要有其他内容。"""
        
        # 构建请求
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
        
        payload = {
            "model": "qwen-vl-plus",
            "messages": messages,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # 解析 JSON 响应
            import re
            # 提取 JSON 部分
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                return {"error": "无法解析响应", "raw": content}
                
        except Exception as e:
            return {"error": str(e)}
    
    def recognize_food_simple(self, image_path):
        """简化版识别：只返回食物名称和预估热量"""
        
        base64_image = self.encode_image(image_path)
        
        prompt = """请识别这张图片中的主要食物，只返回食物名称和预估热量。
        格式：食物名称 - 预估热量(千卡)
        例如：鸡胸肉炒西兰花 - 350千卡"""
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
        
        payload = {
            "model": "qwen-vl-plus",
            "messages": messages,
            "max_tokens": 500
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"识别失败: {str(e)}"

# 测试函数
if __name__ == "__main__":
    print("✅ 食物图片识别模块已加载")
    print("使用方法：")
    print("  recognizer = FoodImageRecognizer(api_type='qwen', api_key='your-key')")
    print("  result = recognizer.recognize_food('food.jpg')")
