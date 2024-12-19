import os
from dotenv import load_dotenv
from openai import OpenAI
import json

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
# MODELID="gpt-4-turbo-preview"
MODELID="gpt-3.5-turbo"
def analyze_recipe(recipe_text: str) -> dict:
    """
    Analyze recipe for ingredients, serving size, and scaling information.
    """
    response = client.chat.completions.create(
        model=MODELID,
        messages=[
            {
                "role": "user",
                "content": f"""Analyze this recipe and provide the following information in JSON format:
                1. List of ingredients with:
                   - name
                   - amount
                   - unit
                   - notes (e.g., "organic", "fresh", "canned")
                2. Number of servings this recipe makes
                3. Type of meal (breakfast, lunch, dinner)
                4. Portion size per serving
                5. Estimated calories per serving
                
                Format your response as a JSON object with these keys:
                - ingredients: array of ingredient objects
                - servings: number
                - meal_type: string
                - portion_size: string
                - calories_per_serving: number
                
                Recipe text:
                {recipe_text}"""
            }
        ],
        response_format={ "type": "json_object" }
    )
    
    return json.loads(response.choices[0].message.content)

def scale_recipe(recipe_data: dict, target_meals: int) -> dict:
    """
    Scale recipe ingredients for desired number of meals.
    """
    response = client.chat.completions.create(
        model=MODELID,
        messages=[
            {
                "role": "user",
                "content": f"""Scale this recipe to make {target_meals} meals.
                
                Current recipe data:
                {json.dumps(recipe_data, indent=2)}
                
                Calculate the new quantities needed and provide:
                1. Scaled ingredients list with adjusted amounts
                2. Shopping list optimized for bulk buying
                3. Storage recommendations for bulk ingredients
                4. Estimated total cost
                
                Format as JSON with these keys:
                - scaled_ingredients: array of adjusted ingredients
                - shopping_list: array of optimized items to buy and each item has the following fields: name, amount, units, notes
                - storage_tips: object with storage advice
                - estimated_cost: number
                
                Consider:
                - Rounding to practical purchase amounts
                - Bulk packaging sizes
                - Common store quantities
                - Ingredient shelf life"""
            }
        ],
        response_format={ "type": "json_object" }
    )
    
    return json.loads(response.choices[0].message.content)

def process_recipe(recipe_text: str, meals_per_week: int = 7):
    """
    Main function to analyze and scale recipe.
    """
    print("Analyzing recipe...")
    recipe_data = analyze_recipe(recipe_text)
    
    print("\nOriginal Recipe Analysis:")
    print(f"Serves: {recipe_data['servings']} people")
    print(f"Meal Type: {recipe_data['meal_type']}")
    print(f"Calories per serving: {recipe_data['calories_per_serving']}")
    
    # Calculate total meals needed
    servings_needed = meals_per_week
    print(f"\nScaling recipe for {servings_needed} meals...")
    
    scaled_data = scale_recipe(recipe_data, servings_needed)
    
    print("\nScaled Recipe Information:")
    print("\nShopping List:")
    for item in scaled_data['shopping_list']:
        print(f"- {item}")
    
    print("\nStorage Tips:")
    for ingredient, tip in scaled_data['storage_tips'].items():
        print(f"- {ingredient}: {tip}")
    
    print(f"\nEstimated Total Cost: ${scaled_data['estimated_cost']:.2f}")
    
    return json.dumps({
        'original_recipe': recipe_data,
        'scaled_recipe': scaled_data
    }, indent=2)

# Example usage
if __name__ == "__main__":
    example_recipe = """
    Classic Chicken Stir-Fry
    
    Ingredients:
    2 chicken breasts, sliced
    3 cups mixed vegetables
    2 tablespoons soy sauce
    1 tablespoon oil
    2 cloves garlic, minced
    1 cup rice
    
    Instructions:
    Cook rice according to package directions. Heat oil in a large pan...

    """
    
    result = process_recipe(
        recipe_text=example_recipe,
        meals_per_week=7  # Scale for a week's worth of meals
    )
    print(result)


"""
Analyzing recipe...

Original Recipe Analysis:
Serves: 4 people
Meal Type: dinner
Calories per serving: 500

Scaling recipe for 7 meals...

Scaled Recipe Information:

Shopping List:
- {'name': 'chicken breasts', 'amount': 4, 'unit': '', 'notes': 'packs typically come in multiples of 2'}
- {'name': 'mixed vegetables', 'amount': 6, 'unit': 'cups', 'notes': 'buy in 2 lb bags, approximately 6 cups'}
- {'name': 'soy sauce', 'amount': 1, 'unit': 'bottle', 'notes': 'buy a 10 oz bottle'}
- {'name': 'oil', 'amount': 1, 'unit': 'bottle', 'notes': 'buy a 16 oz bottle'}
- {'name': 'garlic', 'amount': 1, 'unit': 'bulb', 'notes': 'bulbs typically contain 10-12 cloves'}
- {'name': 'rice', 'amount': 2, 'unit': 'lbs', 'notes': 'buy in bags, 1 cup of rice is approximately 1/2 pound'}

Storage Tips:
- chicken breasts: Store in the freezer if not used within 2 days. Thaw overnight in the refrigerator before use.
- mixed vegetables: Keep frozen if bought frozen, or in the refrigerator if fresh. Use within 1 week.
- soy sauce: Store in a cool, dark place. Refrigerate after opening.
- oil: Keep in a cool, dark place away from direct heat or light.
- garlic: Store in a cool, dry place with good air circulation.
- rice: Store in a cool, dry place in an airtight container.

Estimated Total Cost: $45.00
{
  "original_recipe": {
    "ingredients": [
      {
        "name": "chicken breasts",
        "amount": 2,
        "unit": "",
        "notes": "sliced"
      },
      {
        "name": "mixed vegetables",
        "amount": 3,
        "unit": "cups",
        "notes": ""
      },
      {
        "name": "soy sauce",
        "amount": 2,
        "unit": "tablespoons",
        "notes": ""
      },
      {
        "name": "oil",
        "amount": 1,
        "unit": "tablespoon",
        "notes": ""
      },
      {
        "name": "garlic",
        "amount": 2,
        "unit": "cloves",
        "notes": "minced"
      },
      {
        "name": "rice",
        "amount": 1,
        "unit": "cup",
        "notes": ""
      }
    ],
    "servings": 4,
    "meal_type": "dinner",
    "portion_size": "1/4 of total dish",
    "calories_per_serving": 500
  },
  "scaled_recipe": {
    "scaled_ingredients": [
      {
        "name": "chicken breasts",
        "amount": 3.5,
        "unit": "",
        "notes": "sliced"
      },
      {
        "name": "mixed vegetables",
        "amount": 5.25,
        "unit": "cups",
        "notes": ""
      },
      {
        "name": "soy sauce",
        "amount": 3.5,
        "unit": "tablespoons",
        "notes": ""
      },
      {
        "name": "oil",
        "amount": 1.75,
        "unit": "tablespoon",
        "notes": ""
      },
      {
        "name": "garlic",
        "amount": 3.5,
        "unit": "cloves",
        "notes": "minced"
      },
      {
        "name": "rice",
        "amount": 1.75,
        "unit": "cups",
        "notes": ""
      }
    ],
    "shopping_list": [
      {
        "name": "chicken breasts",
        "amount": 4,
        "unit": "",
        "notes": "packs typically come in multiples of 2"
      },
      {
        "name": "mixed vegetables",
        "amount": 6,
        "unit": "cups",
        "notes": "buy in 2 lb bags, approximately 6 cups"
      },
      {
        "name": "soy sauce",
        "amount": 1,
        "unit": "bottle",
        "notes": "buy a 10 oz bottle"
      },
      {
        "name": "oil",
        "amount": 1,
        "unit": "bottle",
        "notes": "buy a 16 oz bottle"
      },
      {
        "name": "garlic",
        "amount": 1,
        "unit": "bulb",
        "notes": "bulbs typically contain 10-12 cloves"
      },
      {
        "name": "rice",
        "amount": 2,
        "unit": "lbs",
        "notes": "buy in bags, 1 cup of rice is approximately 1/2 pound"
      }
    ],
    "storage_tips": {
      "chicken breasts": "Store in the freezer if not used within 2 days. Thaw overnight in the refrigerator before use.",
      "mixed vegetables": "Keep frozen if bought frozen, or in the refrigerator if fresh. Use within 1 week.",
      "soy sauce": "Store in a cool, dark place. Refrigerate after opening.",
      "oil": "Keep in a cool, dark place away from direct heat or light.",
      "garlic": "Store in a cool, dry place with good air circulation.",
      "rice": "Store in a cool, dry place in an airtight container."
    },
    "estimated_cost": 45
  }
}
"""