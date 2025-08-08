from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class OrderItem:
    name: str
    quantity: int
    price: float
    customizations: List[str] = field(default_factory=list)
    special_instructions: str = ""
    
    def get_total_price(self) -> float:
        return self.price * self.quantity
    
    def __str__(self) -> str:
        base = f"{self.quantity}x {self.name} (${self.price:.2f} each)"
        if self.customizations:
            base += f" with {', '.join(self.customizations)}"
        if self.special_instructions:
            base += f" - Note: {self.special_instructions}"
        return base

@dataclass
class Order:
    items: List[OrderItem] = field(default_factory=list)
    customer_name: str = ""
    order_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, confirmed, preparing, ready, delivered
    tax_rate: float = 0.08
    
    def add_item(self, item: OrderItem) -> None:
        """Add an item to the order"""
        # Check if item already exists, if so, update quantity
        for existing_item in self.items:
            if (existing_item.name == item.name and 
                existing_item.customizations == item.customizations):
                existing_item.quantity += item.quantity
                return
        self.items.append(item)
    
    def remove_item(self, item_name: str) -> bool:
        """Remove an item from the order"""
        for i, item in enumerate(self.items):
            if item.name.lower() == item_name.lower():
                del self.items[i]
                return True
        return False
    
    def get_subtotal(self) -> float:
        """Get subtotal before tax"""
        return sum(item.get_total_price() for item in self.items)
    
    def get_tax_amount(self) -> float:
        """Calculate tax amount"""
        return self.get_subtotal() * self.tax_rate
    
    def get_total(self) -> float:
        """Get total amount including tax"""
        return self.get_subtotal() + self.get_tax_amount()
    
    def is_empty(self) -> bool:
        """Check if order is empty"""
        return len(self.items) == 0
    
    def clear(self) -> None:
        """Clear all items from order"""
        self.items.clear()
    
    def __str__(self) -> str:
        if self.is_empty():
            return "Empty order"
        
        order_str = f"Order {self.order_id}:\n"
        for item in self.items:
            order_str += f"  - {item}\n"
        
        order_str += f"\nSubtotal: ${self.get_subtotal():.2f}\n"
        order_str += f"Tax: ${self.get_tax_amount():.2f}\n"
        order_str += f"Total: ${self.get_total():.2f}"
        
        return order_str