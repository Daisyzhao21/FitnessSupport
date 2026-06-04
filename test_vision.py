from image_recognition import FoodImageRecognizer
import os

# 初始化识别器
api_key = os.environ.get("QWEN_API_KEY")
if not api_key:
    print("❌ 请先设置 QWEN_API_KEY 环境变量")
    print("export QWEN_API_KEY='your_key_here'")
    exit(1)

recognizer = FoodImageRecognizer(api_type="qwen", api_key=api_key)
print("✅ 识别器初始化成功")

# 测试一个简单的图片识别（如果没有图片，会提示）
print("\n📸 准备测试图片识别...")
print("请确保有一张食物图片用于测试")
