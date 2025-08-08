from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools.menu_tools import (
    load_menu_from_file, get_default_menu, search_menu_items,
    get_menu_item_by_name, filter_menu_by_category, filter_menu_by_dietary,
    get_popular_items, get_chef_recommendations, format_menu_display
)
from prompts.menu_agent_prompts import MENU_AGENT_PROMPT, MENU_DISPLAY_PROMPT
from tools.validation_tools import sanitize_input, validate_dietary_restrictions
from config import Config
import os

class MenuAgent:
    def __init__(self, llm=None):
        self.llm = llm or ChatGoogleGenerativeAI(
            model=Config.MODEL_NAME,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=Config.MODEL_TEMPERATURE
        )
        self.menu = self.load_menu()
        self.prompt_template = PromptTemplate(
            input_variables=["menu", "customer_input"],
            template=MENU_AGENT_PROMPT
        )
        self.menu_chain = self.prompt_template | self.llm | StrOutputParser()

    def load_menu(self):
        """Load menu from file or use default"""
        menu_file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'menu.json')
        return load_menu_from_file(menu_file_path)

    def display_menu(self, category=None, dietary_filter=None):
        """Display the full menu or filtered version"""
        menu_to_display = self.menu
        
        if category:
            menu_to_display = filter_menu_by_category(menu_to_display, category)
        
        if dietary_filter:
            menu_to_display = [item for item in menu_to_display 
                             if validate_dietary_restrictions(item, [dietary_filter])]
        
        return format_menu_display(menu_to_display)

    def get_menu_item(self, item_name):
        """Get specific menu item details"""
        sanitized_name = sanitize_input(item_name)
        return get_menu_item_by_name(self.menu, sanitized_name)

    def search_menu(self, query):
        """Search menu items by query"""
        sanitized_query = sanitize_input(query)
        results = search_menu_items(self.menu, sanitized_query)
        return format_menu_display(results)

    def get_recommendations(self):
        """Get chef recommendations and popular items"""
        recommendations = get_chef_recommendations(self.menu)
        popular = get_popular_items(self.menu)
        
        response = "🌟 **CHEF'S RECOMMENDATIONS** 🌟\n"
        response += format_menu_display(recommendations)
        response += "\n🔥 **POPULAR ITEMS** 🔥\n"
        response += format_menu_display(popular)
        
        return response

    def handle_menu_query(self, customer_input):
        """Handle customer menu-related queries using AI"""
        sanitized_input = sanitize_input(customer_input)
        
        response_text = self.menu_chain.invoke({
            "menu": format_menu_display(self.menu),
            "customer_input": sanitized_input
        })
        
        return response_text