from PIL import Image
from dotenv import load_dotenv
import numpy as np
from openai import OpenAI
from glob import glob
import json
import os
import base64
from io import BytesIO
import google.generativeai as genai
import re
import pandas as pd

OPENAI_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "Calories(kcal)": {
            "type": "number",
            "description": "The number of calories in the food item."
        },
        "Carbohydrates(g)": {
            "type": "number",
            "description": "The amount of carbohydrates in grams."
        },
        "Protein(g)": {
            "type": "number",
            "description": "The amount of protein in grams."
        },
        "Fat(g)": {
            "type": "number",
            "description": "The amount of fat in grams."
        },
    },
    "required": ["Calories(kcal)", "Carbohydrates(g)", "Protein(g)", "Fat(g)"],
    "additionalProperties": False
}
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY_1")
OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
GEMINI_CLIENT = genai.GenerativeModel("gemini-1.5-flash")
OPENROUTER_CLIENT = OpenAI(api_key=OPENROUTER_API_KEY,base_url="https://openrouter.ai/api/v1")

def import_image(image_path):

    with Image.open(image_path) as img:
        img = img.convert('RGB')
        img_array = np.array(img)
    
    return img_array

def encode_image(image_array):
    img = Image.fromarray(image_array)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def openai_api_query(image_array, example_image_1, example_image_2):
    response = OPENAI_CLIENT.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "user",
                "content": [
                    # 第一組示範
                    { "type": "text", "text": "以下是一張範例圖片與對應的營養分析結果：" },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64," + encode_image(example_image_1)
                        }
                    },
                    {
                        "type": "text",
                        "text": json.dumps({
                            "Calories(kcal)": 718,
                            "Carbohydrates(g)": 74.27,
                            "Protein(g)": 36.27,
                            "Fat(g)": 30.54
                        }, indent=4)
                    },

                    { "type": "text", "text": "另一個範例：" },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64," + encode_image(example_image_2)
                        }
                    },
                    {
                        "type": "text",
                        "text": json.dumps({
                            "Calories(kcal)": 546.5,
                            "Carbohydrates(g)": 64.9,
                            "Protein(g)": 53.5,
                            "Fat(g)": 6.9
                        }, indent=4)
                    },
                    {
                        "type": "text",
                        "text": "你是營養專家，你的任務是從一張圖片中提取食物的營養成分。請根據以下流程完成營養成分提取:\n\n"
                                "1. 請先分析圖片中的食物，並確定其類型和數量。對於你不確定的資訊請就最有可能、最常見的狀況進行估計\n"
                                "2. 根據食物的類型和數量，計算出每種營養成分的含量。\n"
                                "3. 最後將結果以**純 JSON 格式返回**，格式如下：\n"
                                "{\n"
                                "    \"Calories(kcal)\": 0,\n"
                                "    \"Carbohydrates(g)\": 0,\n" 
                                "     \"Fat(g)\": 0,\n"
                                "    \"Protein(g)\": 0\n"
                                "}\n"
                                "請注意，這些數據是基於你對食物的分析和估算得出的，並請四捨五入到小數點後第一位，並且你不能因為資訊不足就不估計或是返回錯誤格式。",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64," + encode_image(image_array)
                        }
                    }
                ]
            }
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "extract_nutrition",
                    "description": "Extract nutritional facts from food image.",
                    "parameters": OPENAI_JSON_SCHEMA
                }
            }
        ],
        tool_choice={"type": "function", "function": {"name": "extract_nutrition"}},
    )

    if response.choices[0].message.tool_calls:
        tool_args = response.choices[0].message.tool_calls[0].function.arguments
        return json.loads(tool_args)
    else:
        raise ValueError("API response did not include tool_calls.")

def gemini_api_query(image_array):

    image = Image.fromarray(image_array)

    response = GEMINI_CLIENT.generate_content(
        [
            image,
            "你是營養專家，你的任務是從一張圖片中提取食物的營養成分。請根據以下流程完成營養成分提取:\n\n"
            "1. 請先分析圖片中的食物，並確定其類型和數量。對於你不確定的資訊請就最有可能、最常見的狀況進行估計\n"
            "2. 根據食物的類型和數量，計算出每種營養成分的含量。\n"
            "3. 最後將結果以**純 JSON 格式返回**，格式如下：\n"
            "{\n"
            "    \"Calories(kcal)\": 0,\n"
            "    \"Carbohydrates(g)\": 0,\n" 
            "     \"Fat(g)\": 0,\n"
            "    \"Protein(g)\": 0\n"
            "}\n"
            "請注意，這些數據是基於你對食物的分析和估算得出的，並請四捨五入到小數點後第一位，並且你不能因為資訊不足就不估計或是返回錯誤格式。"
        ]
    )

    text = response.text

    try:
        json_str = re.search(r'\{.*\}', text, re.DOTALL).group()
        return json.loads(json_str)
    except Exception as e:
        print(f"JSON parse failed: {e}")
        return {"error": "Failed to parse response", "raw": text}

def openrouter_api_query(image_array, model):
    response = OPENROUTER_CLIENT.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "你是營養專家，你的任務是從一張圖片中提取食物的營養成分。請根據以下流程完成營養成分提取:\n\n"
                                "1. 請先分析圖片中的食物，並確定其類型和數量。對於你不確定的資訊請就最有可能、最常見的狀況進行估計\n"
                                "2. 根據食物的類型和數量，計算出每種營養成分的含量。\n"
                                "3. 最後將結果以**純 JSON 格式返回**，格式如下：\n"
                                "{\n"
                                "    \"Calories(kcal)\": 0,\n"
                                "    \"Carbohydrates(g)\": 0,\n" 
                                "     \"Fat(g)\": 0,\n"
                                "    \"Protein(g)\": 0\n"
                                "}\n"
                                "請注意，這些數據是基於你對食物的分析和估算得出的，並請四捨五入到小數點後第一位，並且你不能因為資訊不足就不估計或是返回錯誤格式。",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64," + encode_image(image_array)
                        }
                    }
                ]
            }
        ],
    )
    if response.choices[0].message:
        content = response.choices[0].message.content
        json_str = re.search(r'\{.*\}', content, re.DOTALL).group()
        return json.loads(json_str)
    else:
        raise ValueError("API response did not include tool_calls.")    

def process_folder(folder_path, filename, example_image_1, example_image_2):
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} does not exist.")
        return

    if os.path.exists(filename):
        existing_df = pd.read_csv(filename)
        existing_files = set(existing_df['filename'].tolist())
        print(f"Found {len(existing_files)} images already processed.")
    else:
        existing_files = set()
        print("No existing file found, will process all images.")

    image_paths = glob(os.path.join(folder_path, "*.jpg")) + glob(os.path.join(folder_path, "*.png"))
    print(f"Found {len(image_paths)} images in folder.")

    example_image_1_array = import_image(example_image_1)
    example_image_2_array = import_image(example_image_2)

    for image_path in image_paths:
        basename = os.path.basename(image_path)
        if basename in existing_files:
            print(f"Skipping {basename} (already processed)")
            continue

        print(f"Processing: {basename}")
        try:
            image_array = import_image(image_path)

            print("OpenAI API Querying...")
            info_openai = openai_api_query(image_array, example_image_1_array, example_image_2_array)
            """print("Gemini API Querying...")
            info_gemini = gemini_api_query(image_array)
            print("Llama Maverick (Openrouter API) Querying...")
            info_llama = openrouter_api_query(image_array, "meta-llama/llama-4-maverick:free")
            print("Google Gemma (Openrouter API) Querying...")
            info_gemma = openrouter_api_query(image_array, "google/gemma-3-12b-it:free")"""
            print("OpenAI 回傳：", info_openai)
            # print("Gemini 回傳：", info_gemini)
            # print("Llama 回傳：", info_llama)
            # print("Gemma 回傳：", info_gemma)

            models = [info_openai]
            keys = ["Calories(kcal)", "Carbohydrates(g)", "Protein(g)", "Fat(g)"]

            info_dict = {
                "filename": basename,
                **{
                    key: round(np.mean([model[key] for model in models]), 2)
                    for key in keys
                }
            }

            save_to_csv(info_dict, filename)
            if info_dict["Calories(kcal)"] < 500:
                save_to_csv(info_dict, "low_calorie_lunch_box.csv")
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            raise e

def save_to_csv(data, filename):
    new_df = pd.DataFrame([data])
    
    if os.path.exists(filename):
        existing_df = pd.read_csv(filename)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    combined_df.to_csv(filename, index=False)
    print(f"✅ Data saved to {filename} (rows: {len(combined_df)})")
    
def main():
    print("Please provide the path to the image folder:")
    folder_path = input().strip()
    file_name = "lunch_box_few_shot.csv"
    example_image_1 = import_image("example_image_1.png")
    example_image_2 = import_image("example_image_2.png")
    process_folder(folder_path, file_name, example_image_1, example_image_2)
    print(f"Nutritional information saved to {file_name}")

if __name__ == "__main__":
    main()