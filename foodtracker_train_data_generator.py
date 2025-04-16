from PIL import Image
from dotenv import load_dotenv
import numpy as np
from openai import OpenAI
from glob import glob
import json
import os
import base64
from io import BytesIO

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
OPENAICLIENT = OpenAI(api_key=OPENAI_API_KEY)

def import_image(image_path):

    with Image.open(image_path) as img:
        img = img.convert('RGB')
        img = img.resize((224, 224))
        img_array = np.array(img)
    
    return img_array

def encode_image(image_array):
    img = Image.fromarray(image_array)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def openai_api_query(image_array):
    response = OPENAICLIENT.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "你是營養專家，請回答出圖片中食物營養成分的準確數值，數字請精確至小數點後第二位。"
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
        print(f"Tool arguments: {tool_args}")
        return tool_args
    else:
        raise ValueError("API response did not include tool_calls.")

def process_folder(folder_path):
    results = []
    image_paths = glob(os.path.join(folder_path, "*.jpg")) + glob(os.path.join(folder_path, "*.png"))
    print(f"Found {len(image_paths)} images.")

    for image_path in image_paths:
        print(f"Processing: {image_path}")
        try:
            image_array = import_image(image_path)
            info = openai_api_query(image_array)

            info_dict = json.loads(info)
            info_dict['filename'] = os.path.basename(image_path)
            results.append(info_dict)

        except Exception as e:
            print(f"Error processing {image_path}: {e}")
    return results

def save_to_csv(data, filename):
    import pandas as pd
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    
def main():
    print("Please provide the path to the image folder:")
    folder_path = input().strip()
    results = process_folder(folder_path)
    save_to_csv(results, "nutritional_info.csv")

if __name__ == "__main__":
    main()