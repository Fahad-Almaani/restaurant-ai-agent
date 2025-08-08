import re
from typing import Dict, List, Optional, Any
from models.order_models import Order, OrderItem

def validate_menu_item_exists(item_name: str, menu: List[Dict]) -> bool:
    """
    Validate if a menu item exists
    """
    for item in menu:
        if item['name'].lower() == item_name.lower():
            return True
    return False

def validate_quantity(quantity: Any) -> bool:
    """
    Validate quantity is a positive integer
    """
    try:
        qty = int(quantity)
        return qty > 0
    except (ValueError, TypeError):
        return False

def validate_customizations(customizations: List[str], allowed_customizations: List[str]) -> List[str]:
    """
    Validate and filter customizations against allowed options
    """
    if not customizations:
        return []
    
    valid_customizations = []
    for custom in customizations:
        if custom.lower() in [ac.lower() for ac in allowed_customizations]:
            valid_customizations.append(custom)
    
    return valid_customizations

def validate_order_completeness(order: Order) -> Dict[str, Any]:
    """
    Validate if an order is complete and ready for processing
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': []
    }
    
    if order.is_empty():
        validation_result['is_valid'] = False
        validation_result['errors'].append("Order is empty")
        return validation_result
    
    for item in order.items:
        # Check if item has valid price
        if item.price <= 0:
            validation_result['warnings'].append(f"Item '{item.name}' has no price set")
        
        # Check if quantity is valid
        if not validate_quantity(item.quantity):
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Invalid quantity for item '{item.name}'")
    
    return validation_result

def sanitize_input(user_input: str) -> str:
    """
    Sanitize user input to prevent issues
    """
    if not user_input:
        return ""
    
    # Remove excessive whitespace
    sanitized = re.sub(r'\s+', ' ', user_input.strip())
    
    # Remove potentially harmful characters
    sanitized = re.sub(r'[<>"\']', '', sanitized)
    
    return sanitized

def validate_dietary_restrictions(item: Dict, dietary_restrictions: List[str]) -> bool:
    """
    Check if menu item meets dietary restrictions
    """
    item_dietary = item.get('dietary', [])
    
    for restriction in dietary_restrictions:
        if restriction.lower() == 'vegetarian' and 'vegetarian' not in item_dietary:
            return False
        elif restriction.lower() == 'vegan' and 'vegan' not in item_dietary:
            return False
        elif restriction.lower() == 'gluten-free' and 'gluten' in item_dietary:
            return False
        elif restriction.lower() == 'dairy-free' and 'dairy' in item_dietary:
            return False
    
    return True

def validate_price_format(price: Any) -> bool:
    """
    Validate price format
    """
    try:
        price_float = float(price)
        return price_float >= 0
    except (ValueError, TypeError):
        return False

def validate_email(email: str) -> bool:
    """
    Validate email format for order confirmation
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid length (10 or 11 digits for US numbers)
    return len(digits_only) in [10, 11]

def validate_menu_selection(selection, menu_items):
    if selection in menu_items:
        return True
    return False

def validate_order(order, menu_items):
    for item in order:
        if item not in menu_items:
            return False
    return True

def validate_customization(customization, valid_customizations):
    for key, value in customization.items():
        if key not in valid_customizations or value not in valid_customizations[key]:
            return False
    return True

def validate_upsell_selection(selection, upsell_items):
    if selection in upsell_items:
        return True
    return False

def validate_input(input_value, expected_type):
    if isinstance(input_value, expected_type):
        return True
    return False