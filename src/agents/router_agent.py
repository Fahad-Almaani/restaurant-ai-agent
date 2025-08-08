from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from tools.validation_tools import sanitize_input
import os
import json

class RouteDecision(BaseModel):
    """Structured output for routing decisions"""
    agent: str = Field(description="The target agent: 'menu', 'order', 'upselling', 'finalization', 'delivery', 'human'")
    confidence: float = Field(description="Confidence score between 0 and 1")
    extracted_items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of items extracted from user input with quantities and specifications"
    )
    user_intent: str = Field(description="Clear description of what user wants")
    needs_clarification: bool = Field(default=False, description="Whether input needs clarification")
    clarification_question: Optional[str] = Field(default=None, description="Question to ask for clarification")
    delivery_method: Optional[str] = Field(default=None, description="Delivery method if detected: 'delivery' or 'pickup'")
    wants_order_change: bool = Field(default=False, description="Whether user wants to modify order instead of answering delivery question")

class MultipleItemsExtraction(BaseModel):
    """Structured output for multiple item extraction"""
    items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of extracted items with details"
    )
    success: bool = Field(description="Whether extraction was successful")
    message: str = Field(description="Summary message about what was extracted")

class RouterAgent:
    def __init__(self, llm=None, menu_data=None):
        self.llm = llm or ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.3  # Lower temperature for more consistent routing
        )
        
        self.menu_data = menu_data or self._load_menu()
        
        # Set up output parsers
        self.route_parser = PydanticOutputParser(pydantic_object=RouteDecision)
        self.multi_item_parser = PydanticOutputParser(pydantic_object=MultipleItemsExtraction)
        
        # Create the main routing prompt
        self.routing_prompt = PromptTemplate(
            input_variables=["user_input", "conversation_context", "menu_items"],
            partial_variables={"format_instructions": self.route_parser.get_format_instructions()},
            template="""
You are an expert Router Agent for an AI restaurant assistant. Your job is to analyze user input and make intelligent routing decisions.

Available Menu Items:
{menu_items}

Current Conversation Context:
{conversation_context}

User Input: "{user_input}"

Analyze the user input and determine:

1. **Intent Classification**: What does the user want to do?
   - BROWSE_MENU: User wants to see menu, get recommendations, or learn about items
   - PLACE_ORDER: User wants to order specific items
   - MODIFY_ORDER: User wants to change existing order
   - FINALIZE_ORDER: User is done ordering and wants to complete/pay
   - DELIVERY_METHOD: User is answering delivery/pickup question
   - ASK_QUESTION: User has general questions about food, ingredients, etc.
   - UNCLEAR: Input is ambiguous and needs clarification

2. **Agent Routing**: Route to appropriate agent:
   - menu: For browsing, recommendations, item information
   - order: For placing orders, item extraction, customizations
   - upselling: When order is placed and upselling is appropriate
   - finalization: When user indicates they're done ordering
   - delivery: For handling delivery questions and confirmations
   - human: For complex issues, complaints, or unclear requests

3. **Delivery Method Detection**: If user is responding to delivery question:
   - "delivery", "deliver", "delivered" → delivery_method: "delivery"
   - "pickup", "pick up", "takeaway", "take away" → delivery_method: "pickup"
   - If user mentions adding items instead → wants_order_change: true, agent: "order"
   - If user wants to cancel → wants_order_change: true, agent: "finalization"

4. **Intelligent Matching**: For order requests, note items mentioned but don't extract them here:
   - "coc" or "coca" likely means "Coca Cola"
   - "burger" could mean "Classic Burger"
   - "pizza" could mean "Margherita Pizza"
   - "cheesecake" could mean "New York Cheesecake"

5. **Context Awareness**: Consider conversation stage:
   - If context shows we're waiting for delivery method and user says anything about ordering → wants_order_change: true
   - If context shows we're finalizing and user gives clear delivery preference → agent: "delivery"
   - If user says "add", "more", "another", "also want" during delivery stage → wants_order_change: true

IMPORTANT: 
- Do NOT include extracted_items in your response. Set extracted_items to an empty list []. 
- Item extraction will be handled separately by the Order Agent.
- Always check if user wants to modify order when delivery method is being asked

{format_instructions}

Be intelligent about context and provide structured, actionable routing decisions.
"""
        )
        
        # Simplified item extraction prompt for multiple items
        self.item_extraction_prompt = PromptTemplate(
            input_variables=["user_input", "menu_items"],
            partial_variables={"format_instructions": self.multi_item_parser.get_format_instructions()},
            template="""
You are an expert at extracting menu items from natural language input.

Available Menu Items:
{menu_items}

User Input: "{user_input}"

Extract ALL items mentioned in the user input. Use intelligent matching:

Examples:
- "coc" or "coca" → "Coca Cola"
- "burger" → "Classic Burger"
- "cheesecake" → "New York Cheesecake"
- "vanilla ice cream" → "Vanilla Ice Cream"
- "2 wings" → "Buffalo Wings" with quantity 2
- "pizza no mushrooms" → "Margherita Pizza" with customization "no mushrooms"
- "I want 3 burgers and 2 cokes" → Extract both items with quantities

For each item found, create a dictionary with:
- item_name: Exact menu item name or closest match
- quantity: Number requested (default 1)
- customizations: List of any customizations mentioned
- confidence: Confidence score 0-1
- alternatives: List of alternative matches if confidence is low

{format_instructions}

Extract ALL items mentioned, not just one.
"""
        )
        
        self.routing_chain = LLMChain(llm=self.llm, prompt=self.routing_prompt)
        self.extraction_chain = LLMChain(llm=self.llm, prompt=self.item_extraction_prompt)

    def _load_menu(self):
        """Load menu data for intelligent matching"""
        try:
            menu_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'menu.json')
            with open(menu_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _format_menu_for_prompt(self):
        """Format menu items for prompt context"""
        items = []
        # Handle menu as a list of items (not a dict)
        if isinstance(self.menu_data, list):
            for item in self.menu_data:
                items.append(f"- {item['name']}: {item['description']} (${item['price']})")
        elif isinstance(self.menu_data, dict):
            # Handle dict format (categorized menu)
            for category, category_items in self.menu_data.items():
                if isinstance(category_items, list):
                    for item in category_items:
                        items.append(f"- {item['name']}: {item['description']} (${item['price']})")
        return "\n".join(items)

    def route_conversation(self, user_input: str, conversation_context: dict = None) -> RouteDecision:
        """
        Main routing function - analyzes input and returns structured routing decision
        """
        sanitized_input = sanitize_input(user_input)
        
        if conversation_context is None:
            conversation_context = {
                "current_order": [],
                "conversation_stage": "greeting",
                "order_total": 0.0
            }
        
        try:
            # Get routing decision from AI
            menu_context = self._format_menu_for_prompt()
            context_str = json.dumps(conversation_context, indent=2)
            
            response = self.routing_chain.invoke({
                "user_input": sanitized_input,
                "conversation_context": context_str,
                "menu_items": menu_context
            })
            
            # Parse the structured output
            route_decision = self.route_parser.parse(response["text"])
            
            # For order requests, extract items separately
            if route_decision.agent == "order":
                extracted_items = self.extract_multiple_items(sanitized_input)
                route_decision.extracted_items = extracted_items
            
            return route_decision
            
        except Exception as e:
            print(f"Router Agent error: {e}")
            # Fallback routing
            return self._fallback_routing(sanitized_input, conversation_context)

    def extract_multiple_items(self, user_input: str) -> List[Dict[str, Any]]:
        """Extract multiple items with detailed analysis using simplified approach"""
        try:
            menu_context = self._format_menu_for_prompt()
            
            response = self.extraction_chain.invoke({
                "user_input": user_input,
                "menu_items": menu_context
            })
            
            # Parse the response
            extraction_result = self.multi_item_parser.parse(response["text"])
            
            return extraction_result.items
            
        except Exception as e:
            print(f"Item extraction error: {e}")
            # Fallback: try to extract items manually
            return self._manual_item_extraction(user_input)

    def _manual_item_extraction(self, user_input: str) -> List[Dict[str, Any]]:
        """Manual fallback item extraction"""
        input_lower = user_input.lower()
        extracted_items = []
        
        # Simple intelligent matching
        intelligent_matches = {
            "cheesecake": {"name": "New York Cheesecake", "price": 6.99},
            "vanilla ice cream": {"name": "Vanilla Ice Cream", "price": 4.99},
            "ice cream": {"name": "Vanilla Ice Cream", "price": 4.99},
            "burger": {"name": "Classic Burger", "price": 12.99},
            "pizza": {"name": "Margherita Pizza", "price": 14.99},
            "coc": {"name": "Coca Cola", "price": 2.99},
            "coca": {"name": "Coca Cola", "price": 2.99},
            "cola": {"name": "Coca Cola", "price": 2.99},
            "wings": {"name": "Buffalo Wings", "price": 8.99},
            "pasta": {"name": "Pasta Carbonara", "price": 16.99},
            "salmon": {"name": "Grilled Salmon", "price": 19.99}
        }
        
        # Look for quantity patterns
        import re
        quantity_patterns = [
            r'(\d+)\s+([a-zA-Z\s]+)',  # "2 burgers"
            r'(one|two|three|four|five)\s+([a-zA-Z\s]+)',  # "one burger"
        ]
        
        # Extract quantities and items
        found_items = {}
        
        # First try quantity patterns
        for pattern in quantity_patterns:
            matches = re.findall(pattern, input_lower)
            for match in matches:
                qty_str, item_name = match
                try:
                    quantity = int(qty_str)
                except:
                    # Convert word numbers
                    word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
                    quantity = word_to_num.get(qty_str, 1)
                
                # Find matching menu item
                for key, menu_item in intelligent_matches.items():
                    if key in item_name:
                        found_items[menu_item["name"]] = {
                            "item_name": menu_item["name"],
                            "quantity": quantity,
                            "customizations": [],
                            "confidence": 0.8,
                            "alternatives": [],
                            "price": menu_item["price"]
                        }
        
        # Then look for items without explicit quantities
        for key, menu_item in intelligent_matches.items():
            if key in input_lower and menu_item["name"] not in found_items:
                found_items[menu_item["name"]] = {
                    "item_name": menu_item["name"],
                    "quantity": 1,
                    "customizations": [],
                    "confidence": 0.8,
                    "alternatives": [],
                    "price": menu_item["price"]
                }
        
        return list(found_items.values())

    def _fallback_routing(self, user_input: str, conversation_context: dict) -> RouteDecision:
        """Fallback routing when AI parsing fails"""
        input_lower = user_input.lower()
        
        # Check if we're in delivery method stage
        if conversation_context.get("conversation_stage") == "awaiting_delivery":
            # Check for delivery method keywords
            if any(word in input_lower for word in ['delivery', 'deliver', 'delivered']):
                return RouteDecision(
                    agent="delivery",
                    confidence=0.8,
                    user_intent="DELIVERY_METHOD",
                    delivery_method="delivery",
                    extracted_items=[],
                    needs_clarification=False
                )
            elif any(word in input_lower for word in ['pickup', 'pick up', 'takeaway', 'take away']):
                return RouteDecision(
                    agent="delivery",
                    confidence=0.8,
                    user_intent="DELIVERY_METHOD",
                    delivery_method="pickup",
                    extracted_items=[],
                    needs_clarification=False
                )
            elif any(word in input_lower for word in ['add', 'more', 'another', 'also', 'want', 'order']):
                return RouteDecision(
                    agent="order",
                    confidence=0.7,
                    user_intent="MODIFY_ORDER",
                    wants_order_change=True,
                    extracted_items=self._manual_item_extraction(user_input),
                    needs_clarification=False
                )
            elif any(word in input_lower for word in ['cancel', 'stop', 'nevermind', 'forget']):
                return RouteDecision(
                    agent="finalization",
                    confidence=0.8,
                    user_intent="CANCEL_ORDER",
                    wants_order_change=True,
                    extracted_items=[],
                    needs_clarification=False
                )
        
        # Simple keyword-based fallback for other stages
        if any(word in input_lower for word in ['menu', 'see', 'show', 'what', 'have']):
            agent = "menu"
            intent = "BROWSE_MENU"
        elif any(word in input_lower for word in ['order', 'want', 'get', 'buy', 'take']):
            agent = "order"
            intent = "PLACE_ORDER"
        elif any(word in input_lower for word in ['done', 'finish', 'complete', 'pay', 'checkout']):
            agent = "finalization"
            intent = "FINALIZE_ORDER"
        else:
            agent = "menu"
            intent = "ASK_QUESTION"
        
        # For order requests, try manual extraction
        extracted_items = []
        if agent == "order":
            extracted_items = self._manual_item_extraction(user_input)
        
        return RouteDecision(
            agent=agent,
            confidence=0.6,
            user_intent=intent,
            extracted_items=extracted_items,
            needs_clarification=False
        )

    def analyze_ambiguous_input(self, user_input: str) -> Dict[str, Any]:
        """Analyze ambiguous input and suggest clarifications"""
        ambiguity_prompt = PromptTemplate(
            input_variables=["user_input", "menu_items"],
            template="""
User said: "{user_input}"

Available menu items:
{menu_items}

This input seems ambiguous. Analyze what the user might mean and suggest clarifying questions.

Return a JSON with:
- possible_meanings: List of possible interpretations
- clarifying_question: A helpful question to ask the user
- suggested_items: Menu items that might match

Be helpful and specific in your suggestions.
"""
        )
        
        try:
            chain = LLMChain(llm=self.llm, prompt=ambiguity_prompt)
            response = chain.invoke({
                "user_input": user_input,
                "menu_items": self._format_menu_for_prompt()
            })
            
            return json.loads(response["text"])
        except:
            return {
                "possible_meanings": ["Could be menu browsing", "Could be placing an order"],
                "clarifying_question": "What would you like to do today?",
                "suggested_items": []
            }

    def get_intelligent_suggestions(self, partial_input: str) -> List[str]:
        """Get intelligent suggestions for partial/unclear input"""
        suggestion_prompt = PromptTemplate(
            input_variables=["partial_input", "menu_items"],
            template="""
User typed: "{partial_input}"

Menu items available:
{menu_items}

Provide intelligent suggestions for what the user might be looking for.
Consider:
- Partial matches (e.g., "burg" → "Classic Burger")
- Common abbreviations (e.g., "coc" → "Coca Cola")
- Similar sounding items
- Popular items

Return up to 5 suggestions as a simple list.
"""
        )
        
        try:
            chain = LLMChain(llm=self.llm, prompt=suggestion_prompt)
            response = chain.invoke({
                "partial_input": partial_input,
                "menu_items": self._format_menu_for_prompt()
            })
            
            # Parse suggestions from response
            suggestions = [line.strip("- ").strip() for line in response["text"].split("\n") if line.strip()]
            return suggestions[:5]
        except:
            return ["Browse our menu", "See popular items", "Get recommendations"]