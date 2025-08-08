from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from prompts.upselling_prompts import (
    UPSELLING_AGENT_PROMPT, UPSELLING_SUGGESTIONS, UPSELLING_RESPONSES,
    get_upselling_prompt
)
from tools.validation_tools import sanitize_input
from models.order_models import Order, OrderItem
from config import Config
import json
import os

class UpsellingAgent:
    def __init__(self, llm=None):
        self.llm = llm or ChatGoogleGenerativeAI(
            model=Config.MODEL_NAME,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.8
        )
        self.upselling_rules = self.load_upselling_rules()
        self.prompt_template = PromptTemplate(
            input_variables=["current_order", "available_upsells", "customer_input"],
            template=UPSELLING_AGENT_PROMPT
        )
        self.upselling_chain = LLMChain(llm=self.llm, prompt=self.prompt_template)

    def load_upselling_rules(self):
        """Load upselling rules from file"""
        try:
            rules_file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'upselling_rules.json')
            with open(rules_file_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return self.get_default_upselling_rules()

    def get_default_upselling_rules(self):
        """Default upselling rules if file not found"""
        return {
            "burger": ["fries", "onion rings", "soft drink", "milkshake"],
            "pizza": ["garlic bread", "caesar salad", "wine", "dessert"],
            "pasta": ["garlic bread", "wine", "parmesan cheese", "side salad"],
            "salad": ["grilled chicken", "avocado", "bread rolls", "iced tea"],
            "mains": ["appetizer", "dessert", "beverage"],
            "any_order": ["dessert", "coffee", "extra sides"]
        }

    def suggest_upsell(self, current_order: Order):
        """Generate upsell suggestions based on current order"""
        if current_order.is_empty():
            return "Would you like to start with one of our appetizers?"

        suggestions = []
        order_items = [item.name.lower() for item in current_order.items]

        # Check for specific item-based upsells
        for item_name in order_items:
            for rule_key, rule_suggestions in self.upselling_rules.items():
                if rule_key.lower() in item_name:
                    suggestions.extend(rule_suggestions)

        # Always suggest general upsells
        suggestions.extend(self.upselling_rules.get("any_order", []))

        # Remove duplicates and limit suggestions
        unique_suggestions = list(set(suggestions))[:3]

        if unique_suggestions:
            suggestion_text = f"Based on your order, I'd recommend adding: {', '.join(unique_suggestions)}. "
            suggestion_text += "These items complement your selection perfectly!"
            return suggestion_text
        
        return "Would you like to add a beverage or dessert to complete your meal?"

    def process_upsell_response(self, customer_response: str, suggested_items: list, current_order: Order):
        """Process customer response to upsell suggestions"""
        sanitized_response = sanitize_input(customer_response).lower()
        
        # Positive responses
        if any(word in sanitized_response for word in ['yes', 'sure', 'okay', 'add', 'include']):
            # Try to identify which item they want
            for item in suggested_items:
                if item.lower() in sanitized_response:
                    return f"Great! I've noted that you'd like to add {item}. Anything else?"
            
            return "Excellent! Which of the suggested items would you like to add?"
        
        # Negative responses
        elif any(word in sanitized_response for word in ['no', 'not', "don't", 'skip']):
            return UPSELLING_RESPONSES["declined_politely"].format(
                current_order=str(current_order)
            )
        
        # Unclear response - ask for clarification
        else:
            return "I'd be happy to help! Could you let me know which items interest you, or would you prefer to skip the additional items?"

    def generate_smart_upsell(self, current_order: Order, customer_input: str):
        """Use AI to generate contextual upsell suggestions"""
        sanitized_input = sanitize_input(customer_input)
        available_upsells = []
        
        # Generate available upsells based on order
        for item in current_order.items:
            item_key = item.name.lower()
            for rule_key, suggestions in self.upselling_rules.items():
                if rule_key in item_key:
                    available_upsells.extend(suggestions)
        
        response = self.upselling_chain.run(
            current_order=str(current_order),
            available_upsells=', '.join(set(available_upsells)),
            customer_input=sanitized_input
        )
        
        return response

    def calculate_upsell_value(self, base_order_total: float, upsell_items: list):
        """Calculate potential value from upselling"""
        # This would typically use menu prices
        estimated_upsell_value = len(upsell_items) * 5.99  # Average upsell price
        return base_order_total + estimated_upsell_value