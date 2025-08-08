import json
import os
from typing import List, Dict, Optional
from models.menu_models import MenuItem, MenuCategory

def load_menu_from_file(file_path: str) -> List[Dict]:
    """
    Load menu data from JSON file and flatten categorized structure
    """
    try:
        with open(file_path, 'r') as file:
            menu_data = json.load(file)
            
        # If the menu is already a list, return it as is
        if isinstance(menu_data, list):
            return menu_data
            
        # If the menu is categorized (dict with category keys), flatten it
        if isinstance(menu_data, dict):
            flattened_menu = []
            for category, items in menu_data.items():
                if isinstance(items, list):
                    flattened_menu.extend(items)
            return flattened_menu
            
        return get_default_menu()
    except FileNotFoundError:
        return get_default_menu()
    except json.JSONDecodeError:
        if os.getenv("DEBUG_MODE", "false").lower() == "true":
            print("Error: Invalid JSON format in menu file. Using default menu.")
        return get_default_menu()

def get_default_menu() -> List[Dict]:
    """
    Return a default menu if file is not found
    """
    return [
        {
            "id": "burger_classic",
            "name": "Classic Burger",
            "description": "Juicy beef patty with lettuce, tomato, onion, and our special sauce",
            "price": 12.99,
            "category": "mains",
            "dietary": ["gluten"],
            "popular": True,
            "chef_recommendation": False
        },
        {
            "id": "pizza_margherita",
            "name": "Margherita Pizza",
            "description": "Fresh mozzarella, tomato sauce, and basil on crispy thin crust",
            "price": 14.99,
            "category": "mains",
            "dietary": ["vegetarian", "gluten"],
            "popular": True,
            "chef_recommendation": True
        },
        {
            "id": "salad_caesar",
            "name": "Caesar Salad",
            "description": "Crisp romaine lettuce with parmesan, croutons, and caesar dressing",
            "price": 9.99,
            "category": "salads",
            "dietary": ["vegetarian", "gluten"],
            "popular": False,
            "chef_recommendation": False
        },
        {
            "id": "pasta_carbonara",
            "name": "Pasta Carbonara",
            "description": "Creamy pasta with bacon, eggs, and parmesan cheese",
            "price": 16.99,
            "category": "mains",
            "dietary": ["gluten"],
            "popular": True,
            "chef_recommendation": True
        }
    ]

def search_menu_items(menu: List[Dict], query: str) -> List[Dict]:
    """
    Search menu items by name or description
    """
    query = query.lower()
    results = []
    
    for item in menu:
        if (query in item['name'].lower() or 
            query in item['description'].lower() or
            query in item['category'].lower()):
            results.append(item)
    
    return results

def get_menu_item_by_name(menu: List[Dict], item_name: str) -> Optional[Dict]:
    """
    Get a specific menu item by name
    """
    for item in menu:
        if item['name'].lower() == item_name.lower():
            return item
    return None

def filter_menu_by_category(menu: List[Dict], category: str) -> List[Dict]:
    """
    Filter menu items by category
    """
    return [item for item in menu if item['category'].lower() == category.lower()]

def filter_menu_by_dietary(menu: List[Dict], dietary_requirement: str) -> List[Dict]:
    """
    Filter menu items by dietary requirements
    """
    if dietary_requirement.lower() == "vegetarian":
        return [item for item in menu if "vegetarian" in item.get('dietary', [])]
    elif dietary_requirement.lower() == "vegan":
        return [item for item in menu if "vegan" in item.get('dietary', [])]
    elif dietary_requirement.lower() == "gluten-free":
        return [item for item in menu if "gluten" not in item.get('dietary', [])]
    
    return menu

def get_popular_items(menu: List[Dict]) -> List[Dict]:
    """
    Get popular menu items
    """
    return [item for item in menu if item.get('popular', False)]

def get_chef_recommendations(menu: List[Dict]) -> List[Dict]:
    """
    Get chef recommended items
    """
    return [item for item in menu if item.get('chef_recommendation', False)]

def format_menu_display(menu: List[Dict]) -> str:
    """
    Format menu for display to customer
    """
    if not menu:
        return "No menu items available."
    
    # Group by category
    categories = {}
    for item in menu:
        category = item['category'].title()
        if category not in categories:
            categories[category] = []
        categories[category].append(item)
    
    display = "🍽️ **AI BISTRO MENU** 🍽️\n\n"
    
    for category, items in categories.items():
        display += f"**{category.upper()}**\n"
        display += "─" * 40 + "\n"
        
        for item in items:
            display += f"• {item['name']} - ${item['price']:.2f}"
            
            if item.get('popular'):
                display += " 🔥"
            if item.get('chef_recommendation'):
                display += " ⭐"
            
            display += f"\n  {item['description']}\n\n"
    
    display += "🔥 = Popular Item  |  ⭐ = Chef's Recommendation\n"
    return display