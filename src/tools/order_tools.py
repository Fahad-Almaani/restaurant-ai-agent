import json
import re
from typing import Dict, List, Optional, Tuple
from models.order_models import Order, OrderItem

def parse_order_input(customer_input: str) -> List[Dict]:
    """
    Enhanced order parsing to handle multiple items and natural language
    Returns a list of parsed order items
    """
    customer_input = customer_input.strip()
    parsed_items = []
    
    # Patterns for different order formats
    patterns = [
        # "give me one coca cola", "I want 2 burgers"
        r'(?:give me|i want|i\'ll take|get me|i\'d like)\s+(?:(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+)?(.+?)(?:and|,|$)',
        # "one coca cola and two burgers"
        r'(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+([^,]+?)(?:and|,|$)',
        # "coca cola and burger"
        r'([^,]+?)(?:and|,|$)',
        # Simple quantity + item: "2 pizzas"
        r'(\d+)\s+(.+)',
    ]
    
    # Number word to digit mapping
    number_words = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
    }
    
    # Clean input for better parsing
    cleaned_input = re.sub(r'\b(?:please|and)\b', ' ', customer_input.lower())
    cleaned_input = re.sub(r'\s+', ' ', cleaned_input).strip()
    
    # Try to split by common separators first
    items_list = re.split(r'\s+and\s+|,\s*', cleaned_input)
    
    for item_text in items_list:
        item_text = item_text.strip()
        if not item_text:
            continue
            
        # Try different patterns
        parsed_item = None
        
        # Pattern 1: "give me one coca cola" style
        match = re.search(r'(?:give me|i want|i\'ll take|get me|i\'d like)\s+(?:(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+)?(.+)', item_text)
        if match:
            quantity_str = match.group(1) or "1"
            item_name = match.group(2).strip()
            quantity = number_words.get(quantity_str, quantity_str)
            try:
                quantity = int(quantity)
                parsed_item = {'name': item_name, 'quantity': quantity, 'price': 0.0}
            except (ValueError, TypeError):
                quantity = 1
                parsed_item = {'name': item_name, 'quantity': quantity, 'price': 0.0}
        
        # Pattern 2: "two burgers" style
        if not parsed_item:
            match = re.search(r'(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(.+)', item_text)
            if match:
                quantity_str = match.group(1)
                item_name = match.group(2).strip()
                quantity = number_words.get(quantity_str, quantity_str)
                try:
                    quantity = int(quantity)
                    parsed_item = {'name': item_name, 'quantity': quantity, 'price': 0.0}
                except (ValueError, TypeError):
                    quantity = 1
                    parsed_item = {'name': item_name, 'quantity': quantity, 'price': 0.0}
        
        # Pattern 3: Just item name
        if not parsed_item and item_text:
            # Remove common order prefixes
            item_name = re.sub(r'^(?:give me|i want|i\'ll take|get me|i\'d like)\s+', '', item_text)
            parsed_item = {'name': item_name.strip(), 'quantity': 1, 'price': 0.0}
        
        if parsed_item:
            parsed_items.append(parsed_item)
    
    return parsed_items if parsed_items else [{'name': customer_input, 'quantity': 1, 'price': 0.0}]

def validate_order(customer_input: str) -> Optional[Dict]:
    """
    Validate and parse customer order input (legacy function, kept for compatibility)
    """
    parsed_items = parse_order_input(customer_input)
    return parsed_items[0] if parsed_items else None

def format_order_confirmation(added_items: List[Dict], menu_items: List[Dict]) -> str:
    """
    Format a structured order confirmation message
    """
    if not added_items:
        return "I couldn't understand your order. Could you please try again?"
    
    confirmation_parts = []
    total_added = 0.0
    
    confirmation_parts.append("✅ **ORDER CONFIRMED** ✅")
    confirmation_parts.append("")
    confirmation_parts.append("I've added the following to your order:")
    confirmation_parts.append("")
    
    for item_data in added_items:
        quantity = item_data['quantity']
        name = item_data['name']
        price = item_data['price']
        item_total = price * quantity
        total_added += item_total
        
        if quantity == 1:
            confirmation_parts.append(f"• {name} - ${price:.2f}")
        else:
            confirmation_parts.append(f"• {quantity}x {name} - ${price:.2f} each (${item_total:.2f} total)")
    
    confirmation_parts.append("")
    confirmation_parts.append(f"💰 Items added total: ${total_added:.2f}")
    
    return "\n".join(confirmation_parts)

def format_order_details(order: Order) -> str:
    """
    Format order details for display with enhanced structure
    """
    if not order.items:
        return "📋 Your order is currently empty."
    
    details = []
    details.append("📋 **YOUR CURRENT ORDER**")
    details.append("─" * 30)
    
    for item in order.items:
        item_total = item.get_total_price()
        if item.quantity == 1:
            details.append(f"• {item.name} - ${item.price:.2f}")
        else:
            details.append(f"• {item.quantity}x {item.name} - ${item.price:.2f} each (${item_total:.2f})")
        
        if item.customizations:
            details.append(f"  └ Customizations: {', '.join(item.customizations)}")
        if item.special_instructions:
            details.append(f"  └ Note: {item.special_instructions}")
    
    details.append("─" * 30)
    details.append(f"Subtotal: ${order.get_subtotal():.2f}")
    details.append(f"Tax ({order.tax_rate*100:.0f}%): ${order.get_tax_amount():.2f}")
    details.append(f"**Total: ${order.get_total():.2f}**")
    
    return "\n".join(details)

def find_menu_matches(item_name: str, menu: List[Dict]) -> List[Dict]:
    """
    Find menu items that match the requested item name with fuzzy matching
    """
    item_name_lower = item_name.lower()
    exact_matches = []
    partial_matches = []
    
    for menu_item in menu:
        menu_name_lower = menu_item['name'].lower()
        
        # Exact match
        if menu_name_lower == item_name_lower:
            exact_matches.append(menu_item)
        # Partial match - check if item name is in menu name or vice versa
        elif (item_name_lower in menu_name_lower or 
              menu_name_lower in item_name_lower or
              any(word in menu_name_lower for word in item_name_lower.split() if len(word) > 2)):
            partial_matches.append(menu_item)
    
    return exact_matches or partial_matches

def create_order_summary_dict(order: Order) -> Dict:
    """
    Create a structured dictionary representation of the order
    """
    return {
        "order_id": order.order_id,
        "customer_name": order.customer_name,
        "status": order.status,
        "items": [
            {
                "name": item.name,
                "quantity": item.quantity,
                "unit_price": item.price,
                "total_price": item.get_total_price(),
                "customizations": item.customizations,
                "special_instructions": item.special_instructions
            }
            for item in order.items
        ],
        "subtotal": order.get_subtotal(),
        "tax_rate": order.tax_rate,
        "tax_amount": order.get_tax_amount(),
        "total": order.get_total(),
        "timestamp": order.timestamp.isoformat() if order.timestamp else None
    }