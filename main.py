import os
from typing import Dict
from urllib.parse import quote
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openai import OpenAI
import json
import time
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv

load_dotenv()

CLAUDE_2_1='claude-3-haiku-20240307'
# MODELID="gpt-3.5-turbo"
MODELID="gpt-4-turbo-preview"
# TODO: queries and item selection still arent great 
# TODO: add query term to the debugging output
# TODO: When searching can we run query, return top 3-5 items and figure out which is the most relevant
#   - we could use inference, but is expensive
#   - 
class RecipeAssistant:
    def __init__(self, num_meals: int):
        """
        Initialize the Recipe Assistant with Claude API key
        
        Args:
            claude_api_key (str): Anthropic API key
        """
        # Initialize Anthropic client with explicit API key
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.servings_needed = num_meals
        self.debug_walmart_search = True
        self.driver = uc.Chrome()
        self.driver.maximize_window()

    def wait_for_manual_login(self):
        """Wait for user to manually log in to Walmart"""
        print("\nPlease log in to Walmart in the browser window that just opened.")
        print("After logging in, type 'done' and press Enter: ")
        input()
        print("Continuing with recipe processing...")

    def extract_recipe_text(self, recipe_url: str) -> str:
        """Extract text content from recipe URL"""
        response = requests.get(recipe_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.decompose()
            
        return soup.get_text()

    def parse_recipe_with_claude(self, recipe_text: str) -> list:
        """Use Claude to parse recipe ingredients"""
        try:
            response = self.client.chat.completions.create(
                model=MODELID,
                messages=[
                    {
                        "role": "user",
                        "content": f"""Analyze this recipe and convert ingredients into Walmart-optimized shopping format.

                        For each ingredient provide:
                        - name: Format specifically for Walmart grocery search (e.g., "fresh garlic bulb" instead of "garlic cloves", "dairy sour cream" instead of just "sour cream")
                        - amount: numerical quantity
                        - unit: Use common retail units:
                        - For produce: "whole", "bunch", "head", "lb"
                        - For dairy/liquid: "oz", "fl oz", "gallon"
                        - For packaged goods: "oz", "lb", "count"
                        - category: Specify one of: "produce", "dairy", "meat", "pantry", "spices"
                        - notes: Include any specifics like "fresh", "organic", "pre-sliced"

                        Consider common Walmart packaging and product names. Format ingredient names as you would find them on Walmart.com.

                        Format response as JSON with:
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
        except Exception as e:
            print(f"Error parsing ingredients: {e}")
            return []

    def add_to_cart(self, search_query: str):
        """Search for and add item to cart"""
        try:
            self.driver.get(f"https://www.walmart.com/search?q={search_query}")
            
            # Wait for search results
            item = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-item-id]"))
            )
            
            # Wait for and click Add to Cart button
            add_button = WebDriverWait(item, 10).until(
                EC.element_to_be_clickable((By.XPATH, ".//button[contains(text(), 'Add to cart')]"))
            )
            add_button.click()
            
            time.sleep(2)  # Wait for cart update
            
        except Exception as e:
            print(f"Error adding {search_query} to cart: {e}")

    def process_recipe_url(self, recipe_url: str):
        """Main function to process recipe and add to cart"""
        # First navigate to Walmart and wait for manual login
        # self.driver.get("https://www.walmart.com")
        # self.wait_for_manual_login()
        if self.debug_walmart_search:
            scaled_data = None
            with open('shopping_list.json', 'r') as f:
                data = json.loads(f.read())
            print(data)
            scaled_data = data['scaled_recipe']
            recipe_text = data['original_recipe']
        else:
            print("Extracting recipe text...")
            recipe_text = self.extract_recipe_text(recipe_url)

            # print("\nOriginal Recipe Information:")
            # print("\nShopping List:")
            # for item in recipe_text['shopping_list']:
            #     print(f"- {item}")
            
            print("Parsing ingredients with Claude...")
            ingredients = self.parse_recipe_with_claude(recipe_text)
            print(f"Found {len(ingredients)} ingredients")
            
            # Calculate total meals needed
            print(f"\nScaling recipe for {self.servings_needed} meals...")
            scaled_data = self.scale_recipe(ingredients)
            print("\nScaled Recipe Information:")
            print("\nShopping List:")
            for item in scaled_data['shopping_list']:
                print(f"- {item}")

            print("\nStorage Tips:")
            for ingredient, tip in scaled_data['storage_tips'].items():
                print(f"- {ingredient}: {tip}")
            
            print(f"\nEstimated Total Cost: ${scaled_data['estimated_cost']:.2f}")

        print("\nSearching Walmart for ingredients...")
        shopping_results = []

        for ingredient in scaled_data['scaled_ingredients']:
            print(f"Searching for {ingredient['name']}...")
            result = self.search_walmart_product(ingredient)
            shopping_results.append(result)
            time.sleep(2)  # Prevent rate limiting

        # print("Adding items to cart...")
        # for item in ingredients:
        #     search_query = f"{item.get('amount', '')} {item.get('unit', '')} {item['name']}".strip()
        #     print(f"Adding {item['name']} to cart...")
        #     self.add_to_cart(search_query)
        #     time.sleep(2)
        return {
            'original_recipe': recipe_text,
            'scaled_recipe': scaled_data,
            'walmart_products': shopping_results
        }

    def cleanup(self):
        """Close the browser"""
        self.driver.quit()

    def scale_recipe(self, recipe_data: dict) -> dict:
        """
        Scale recipe ingredients for desired number of meals.
        """
        response = self.client.chat.completions.create(
            model=MODELID,
            messages=[
                {
                    "role": "user",
                    "content": f"""Scale this recipe to make {self.servings_needed} meals.
                    
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

    def search_walmart_product(self, ingredient: dict) -> dict:
        """Search for a single ingredient on Walmart.com and return product info."""
        try:
            # Construct more specific search queries based on category
            category = ingredient.get('category', '').lower()
            name = ingredient['name']
            unit = ingredient.get('unit', '')
            notes = ingredient.get('notes', '')

            if category == 'produce':
                search_query = f"fresh {name}"
            elif category == 'dairy':
                search_query = f"dairy {name}"
            elif category == 'meat':
                search_query = f"fresh {name}"
            elif category == 'spices':
                search_query = f"{name} spice"
            else:
                search_query = name

            # Add notes if they exist (like "organic")
            # if notes:
            #     search_query = f"{notes} {search_query}"

            # Add department filter for more accurate results
            # if category == 'produce':
            #     url = f"https://www.walmart.com/browse/food/fresh-fruits-vegetables/{search_query}"
            # elif category == 'dairy':
            #     url = f"https://www.walmart.com/browse/food/dairy-eggs/{search_query}"
            # else:
            #     url = f"https://www.walmart.com/search?q={quote(search_query)}"

            # Construct search query
            # search_query = f"{ingredient['name']} {ingredient['unit']}"
            # search_query = f"{ingredient['amount']} {ingredient['unit']} {ingredient['name']}"
            encoded_query = quote(search_query)
            url = f"https://www.walmart.com/search?q={encoded_query}"
            
            self.driver.get(url)
            time.sleep(2)  # Allow page to load
            
            # Wait for product grid to load
            product = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-item-id]"))
            )
            
            try:
                # Try multiple possible selectors for product name and URL
                product_name = None
                product_url = None
                price = None
                
                # Get product name
                name_selectors = [
                    "span[data-automation-id='product-title']",
                    "span.normal",
                    "span.f6"
                ]
                for selector in name_selectors:
                    try:
                        product_name = product.find_element(By.CSS_SELECTOR, selector).text
                        if self.is_valid_product(product_name, ingredient):
                            break
                    except:
                        continue
                
                # Get product URL
                try:
                    # First try to get the main product link
                    link_element = product.find_element(By.CSS_SELECTOR, "a[href*='/ip/']")
                    product_url = link_element.get_attribute('href')
                except:
                    try:
                        # Backup: try to get any link that contains '/ip/'
                        links = product.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            href = link.get_attribute('href')
                            if href and '/ip/' in href:
                                product_url = href
                                break
                    except:
                        pass
                
                # Get price
                price_selectors = [
                    "[data-automation-id='product-price']",
                    "div.price-main",
                    "span.price"
                ]
                for selector in price_selectors:
                    try:
                        price = product.find_element(By.CSS_SELECTOR, selector).text
                        if price:
                            break
                    except:
                        continue
                
                # Print debug information
                print(f"\nDebug info for {ingredient['name']}:")
                print(f"Name found: {product_name}")
                print(f"URL found: {product_url}")
                print(f"Price found: {price}")
                
                return {
                    "ingredient": ingredient,
                    "product": {
                        "name": product_name or "Name not found",
                        "url": product_url or "URL not found",
                        "price": price or "Price not found",
                        "quantity_needed": f"{ingredient['amount']} {ingredient['unit'] or ''}"
                    }
                }
                
            except Exception as e:
                print(f"Error extracting product details for {ingredient['name']}: {e}")
                return {
                    "ingredient": ingredient,
                    "product": {
                        "name": "Product details not found",
                        "url": "URL not found",
                        "price": "Price not found",
                        "quantity_needed": f"{ingredient['amount']} {ingredient['unit']}"
                    }
                }
                
        except Exception as e:
            print(f"Error searching for {ingredient['name']}: {e}")
            return {
                "ingredient": ingredient,
                "product": {
                    "name": "Search failed",
                    "url": "URL not found",
                    "price": "Price not found",
                    "quantity_needed": f"{ingredient['amount']} {ingredient['unit'] or None}"
                }
            }

    def save_results(self, results: Dict, filename: str = "shopping_list.json"):
        """Save results to a JSON file."""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {filename}")

    def is_valid_product(self, product_name: str, ingredient: dict) -> bool:
        """Validate if the found product matches what we're looking for"""
        category = ingredient.get('category', '').lower()
        name = ingredient['name'].lower()
        
        # Reject if product name contains certain keywords
        invalid_keywords = {
            'produce': ['seeds', 'plant', 'garden', 'growing'],
            'dairy': ['chips', 'snacks', 'artificial'],
            'meat': ['pet', 'dog', 'cat', 'toy']
        }
        
        # Check category-specific invalid keywords
        if category in invalid_keywords:
            if any(kw in product_name.lower() for kw in invalid_keywords[category]):
                return False
        
        # Verify product name contains main ingredient name
        if name not in product_name.lower():
            return False
            
        return True
# Example usage
if __name__ == "__main__":
    assistant = RecipeAssistant(num_meals=7)
    
    recipe_url = "https://www.bonappetit.com/recipe/loaded-scalloped-potatoes"
    
    try:
        results = assistant.process_recipe_url(recipe_url)
        # Save results
        assistant.save_results(results)
        
        # Print shopping list
        print("\nShopping List:")
        for item in results['walmart_products']:
            prod = item['product']
            print(f"\nItem: {item['ingredient']['name']}")
            print(f"Quantity Needed: {prod['quantity_needed']}")
            print(f"Walmart Product: {prod['name']}")
            print(f"Price: {prod['price']}")
            print(f"URL: {prod['url']}")
    except KeyboardInterrupt:
        print("\nStopping the script...")
    finally:
        assistant.cleanup()