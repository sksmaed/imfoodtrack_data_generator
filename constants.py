OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAICLIENT = OpenAI(api_key=OPENAI_API_KEY)
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