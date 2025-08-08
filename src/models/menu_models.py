from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

class MenuCategory(Enum):
    APPETIZERS = "appetizers"
    MAINS = "mains"
    SALADS = "salads"
    DESSERTS = "desserts"
    BEVERAGES = "beverages"
    SIDES = "sides"

class DietaryTag(Enum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    NUT_FREE = "nut_free"
    SPICY = "spicy"

@dataclass
class MenuItem:
    id: str
    name: str
    description: str
    price: float
    category: str
    dietary: List[str] = field(default_factory=list)
    popular: bool = False
    chef_recommendation: bool = False
    customizations: List[str] = field(default_factory=list)
    allergens: List[str] = field(default_factory=list)
    prep_time: int = 15  # minutes
    spice_level: int = 0  # 0-5 scale
    
    def __str__(self) -> str:
        base = f"{self.name} - ${self.price:.2f}"
        if self.popular:
            base += " 🔥"
        if self.chef_recommendation:
            base += " ⭐"
        return base
    
    def get_formatted_description(self) -> str:
        """Get a formatted description with dietary info"""
        desc = self.description
        if self.dietary:
            dietary_tags = ", ".join(self.dietary)
            desc += f" ({dietary_tags})"
        return desc
    
    def is_vegetarian(self) -> bool:
        return "vegetarian" in self.dietary
    
    def is_vegan(self) -> bool:
        return "vegan" in self.dietary
    
    def is_gluten_free(self) -> bool:
        return "gluten" not in self.dietary

@dataclass
class MenuSection:
    category: MenuCategory
    items: List[MenuItem] = field(default_factory=list)
    description: str = ""
    
    def add_item(self, item: MenuItem) -> None:
        """Add an item to this menu section"""
        self.items.append(item)
    
    def get_popular_items(self) -> List[MenuItem]:
        """Get popular items in this section"""
        return [item for item in self.items if item.popular]
    
    def get_chef_recommendations(self) -> List[MenuItem]:
        """Get chef recommended items in this section"""
        return [item for item in self.items if item.chef_recommendation]