from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from agents.menu_agent import MenuAgent
from agents.order_agent import OrderAgent
from agents.upselling_agent import UpsellingAgent
from models.order_models import Order, OrderItem
from tools.validation_tools import sanitize_input, validate_email, validate_phone_number
from config import Config
import os
import re

class CoordinatorAgent:
    def __init__(self, menu_agent=None, order_agent=None, upselling_agent=None):
        self.llm = ChatGoogleGenerativeAI(
            model=Config.MODEL_NAME,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=Config.MODEL_TEMPERATURE
        )
        
        # Initialize sub-agents
        self.menu_agent = menu_agent or MenuAgent(self.llm)
        self.order_agent = order_agent or OrderAgent(self.llm)
        self.upselling_agent = upselling_agent or UpsellingAgent(self.llm)
        
        # Enhanced conversation state tracking
        self.conversation_state = "greeting"  # greeting, menu_browsing, ordering, upselling, ask_anything_else, final_confirmation, delivery_details, completed
        self.customer_order = Order()
        self.customer_name = ""
        self.delivery_info = {}
        self.upsell_attempts = 0
        self.max_upsell_attempts = 2
        
        # Enhanced AI-powered intent detection prompt
        self.intent_detection_prompt = PromptTemplate(
            input_variables=["user_input", "conversation_state", "current_order", "has_items"],
            template="""
You are an expert conversation analyst for a restaurant AI assistant. Your job is to understand customer intent from their natural language input.

Current conversation state: {conversation_state}
Customer has items in order: {has_items}
Current order: {current_order}
Customer input: "{user_input}"

Analyze the customer's input and determine their intent. Pay special attention to signals that indicate they want to:
- Finish ordering and proceed to checkout
- Add more items to their order
- Get help or ask questions
- Respond to upselling suggestions

Common phrases that indicate "finished ordering" include:
- "That's it", "That's all", "I'm done", "That's everything"
- "Nothing else", "No more", "I'm good", "That should do it"
- "Let's proceed", "Ready to order", "Finish the order"
- "I think that's enough", "That completes my order"
- Declining upsell offers with finality

Intent options:
- show_menu: Customer wants to see the menu
- place_order: Customer wants to order specific items
- modify_order: Customer wants to change their existing order
- ask_question: Customer has questions about menu items or restaurant
- upsell_response_yes: Customer accepts upsell suggestions
- upsell_response_no: Customer declines upsell suggestions
- order_complete: Customer indicates they are done ordering and ready to proceed
- delivery_pickup_preference: Customer is specifying delivery vs pickup preference
- delivery_details: Customer is providing delivery information
- greeting: General greeting or conversation starter
- final_confirm: Customer confirms final order for processing

IMPORTANT: If the customer has items in their order and uses phrases like "that's it", "that's all", "nothing else", "I'm done", etc., classify as "order_complete".

Return only the intent name, nothing else.
"""
        )
        
        # Order completion detection prompt
        self.completion_detection_prompt = PromptTemplate(
            input_variables=["user_input", "order_summary"],
            template="""
You are analyzing if a customer wants to complete their restaurant order.

Customer's order: {order_summary}
Customer said: "{user_input}"

The customer has items in their order. Determine if they are indicating they want to:
1. COMPLETE their order (finish ordering and proceed to checkout)
2. CONTINUE ordering (add more items)

Look for completion signals like:
- "That's it", "That's all", "I'm done", "That's everything"
- "Nothing else", "No more", "I'm good", "That should do it"
- "Let's proceed", "Ready to checkout", "Finish the order"
- "I think that's enough", "That completes my order"
- Declining further additions with finality

Return only one word: "COMPLETE" or "CONTINUE"
"""
        )
        
        # Delivery preference prompt
        self.delivery_preference_prompt = PromptTemplate(
            input_variables=["user_input"],
            template="""
Analyze if the customer is expressing a preference for delivery or pickup.

Customer said: "{user_input}"

Look for keywords indicating:
- DELIVERY: "deliver", "delivery", "bring it", "send it", "to my address"
- PICKUP: "pickup", "pick up", "collect", "I'll come get it", "takeaway"

Return only: "DELIVERY", "PICKUP", or "UNCLEAR"
"""
        )
        
        self.intent_chain = LLMChain(llm=self.llm, prompt=self.intent_detection_prompt)
        self.completion_chain = LLMChain(llm=self.llm, prompt=self.completion_detection_prompt)
        self.delivery_preference_chain = LLMChain(llm=self.llm, prompt=self.delivery_preference_prompt)

    def determine_intent_ai(self, user_input: str) -> str:
        """AI-powered intent detection that understands natural language completion signals"""
        sanitized_input = sanitize_input(user_input)
        has_items = "yes" if not self.customer_order.is_empty() else "no"
        
        try:
            # Use AI to determine intent
            intent_response = self.intent_chain.invoke({
                "user_input": sanitized_input,
                "conversation_state": self.conversation_state,
                "current_order": str(self.customer_order),
                "has_items": has_items
            })
            
            detected_intent = intent_response['text'].strip().lower()
            
            # Map AI response to our internal intent system
            if "order_complete" in detected_intent:
                return "order_complete"
            elif "place_order" in detected_intent:
                return "place_order"
            elif "show_menu" in detected_intent:
                return "show_menu"
            elif "upsell_response_yes" in detected_intent:
                return "upsell_response_yes"
            elif "upsell_response_no" in detected_intent:
                return "upsell_response_no"
            elif "delivery_pickup_preference" in detected_intent:
                return "delivery_pickup_preference"
            elif "delivery_details" in detected_intent:
                return "delivery_details"
            elif "modify_order" in detected_intent:
                return "modify_order"
            elif "final_confirm" in detected_intent:
                return "final_confirm"
            elif "greeting" in detected_intent:
                return "greeting"
            else:
                return "ask_question"
                
        except Exception as e:
            if os.getenv("DEBUG_MODE", "false").lower() == "true":
                print(f"AI intent detection failed: {e}")
            # Fallback to simple keyword detection
            return self._fallback_intent_detection(sanitized_input)

    def _fallback_intent_detection(self, user_input: str) -> str:
        """Fallback intent detection using keywords"""
        input_lower = user_input.lower()
        
        # Check for order completion signals
        completion_phrases = [
            "that's it", "that's all", "i'm done", "that's everything",
            "nothing else", "no more", "i'm good", "that should do it",
            "let's proceed", "ready to order", "finish the order",
            "that completes", "that's enough"
        ]
        
        if any(phrase in input_lower for phrase in completion_phrases):
            return "order_complete"
        
        # Standard detection
        if any(word in input_lower for word in ['menu', 'see', 'show']):
            return "show_menu"
        elif any(word in input_lower for word in ['order', 'want', 'get', 'have', 'i\'ll take']):
            return "place_order"
        elif any(word in input_lower for word in ['yes', 'sure', 'add that']):
            return "upsell_response_yes"
        elif any(word in input_lower for word in ['no', 'skip', 'not interested']):
            return "upsell_response_no"
        else:
            return "ask_question"

    def route_request(self, user_input: str) -> str:
        """Enhanced routing with AI-powered intent detection"""
        intent = self.determine_intent_ai(user_input)
        sanitized_input = sanitize_input(user_input)
        
        if intent == "greeting":
            self.conversation_state = "menu_browsing"
            return self._handle_greeting()
            
        elif intent == "show_menu":
            self.conversation_state = "menu_browsing"
            return self.menu_agent.display_menu()
            
        elif intent == "place_order":
            self.conversation_state = "ordering"
            response = self.order_agent.take_order(sanitized_input)
            
            # Update coordinator's order tracking
            if self.order_agent.order.items:
                self.customer_order = self.order_agent.order
            
            return response
            
        elif intent == "modify_order":
            return self._handle_order_modification(sanitized_input)
            
        elif intent == "ask_question":
            return self.menu_agent.handle_menu_query(sanitized_input)
            
        elif intent == "upsell_response_yes":
            response = self.upselling_agent.process_upsell_response(sanitized_input, [], self.customer_order)
            response += "\n\nGreat! What would you like to add?"
            self.conversation_state = "ordering"
            return response
            
        elif intent == "upsell_response_no":
            response = self.upselling_agent.process_upsell_response(sanitized_input, [], self.customer_order)
            return self._ask_completion_or_continue()
            
        elif intent == "order_complete":
            return self._handle_order_completion()
            
        elif intent == "delivery_pickup_preference":
            return self._handle_delivery_preference(sanitized_input)
            
        elif intent == "final_confirm":
            self.conversation_state = "delivery_details"
            return self._ask_delivery_details()
            
        elif intent == "delivery_details":
            return self._handle_delivery_details(sanitized_input)
            
        else:
            return "I'm not sure how to help with that. Could you please rephrase your request?"

    def _ask_completion_or_continue(self) -> str:
        """Ask if customer wants to complete order or continue"""
        if self.customer_order.is_empty():
            return "You don't have any items in your order yet. Would you like to see our menu?"
        
        return "Would you like to add anything else to your order, or are you ready to proceed with what you have?"

    def _handle_order_completion(self) -> str:
        """Handle when AI detects the customer wants to complete their order"""
        if self.customer_order.is_empty():
            return "You don't have any items in your order yet. Would you like to see our menu?"
        
        # Show order summary and ask for delivery preference
        self.conversation_state = "final_confirmation"
        return self._show_order_and_ask_delivery_preference()

    def _show_order_and_ask_delivery_preference(self) -> str:
        """Show order summary and ask for delivery vs pickup preference"""
        order_summary = self.order_agent.get_order_summary()
        
        summary_parts = [
            "🎯 **ORDER SUMMARY**",
            "",
            "Here's what you've ordered:",
            ""
        ]
        
        for item_data in order_summary['items']:
            name = item_data['name']
            quantity = item_data['quantity']
            unit_price = item_data['unit_price']
            total_price = item_data['total_price']
            
            if quantity == 1:
                summary_parts.append(f"• {name} - ${unit_price:.2f}")
            else:
                summary_parts.append(f"• {quantity}x {name} - ${unit_price:.2f} each (${total_price:.2f})")
            
            if item_data['customizations']:
                summary_parts.append(f"  └ Customizations: {', '.join(item_data['customizations'])}")
        
        summary_parts.extend([
            "",
            "─" * 40,
            f"Subtotal: ${order_summary['totals']['subtotal']:.2f}",
            f"Tax (8%): ${order_summary['totals']['tax']:.2f}",
            f"💰 **Total: ${order_summary['totals']['total']:.2f}**",
            "─" * 40,
            "",
            "🚚 Would you like this delivered to your address, or would you prefer to pick it up?"
        ])
        
        return "\n".join(summary_parts)

    def _handle_delivery_preference(self, user_input: str) -> str:
        """Handle delivery vs pickup preference"""
        try:
            preference_response = self.delivery_preference_chain.invoke({
                "user_input": user_input
            })
            preference = preference_response['text'].strip().upper()
            
            if "DELIVERY" in preference:
                self.delivery_info['method'] = 'delivery'
                self.conversation_state = "delivery_details"
                return self._ask_delivery_details()
            elif "PICKUP" in preference:
                self.delivery_info['method'] = 'pickup'
                self.conversation_state = "delivery_details"
                return self._ask_pickup_details()
            else:
                return "I didn't catch that. Would you like delivery to your address or pickup from our restaurant?"
                
        except Exception as e:
            # Fallback to keyword detection
            input_lower = user_input.lower()
            if any(word in input_lower for word in ['deliver', 'delivery', 'bring', 'send']):
                self.delivery_info['method'] = 'delivery'
                self.conversation_state = "delivery_details"
                return self._ask_delivery_details()
            elif any(word in input_lower for word in ['pickup', 'pick up', 'collect', 'get it']):
                self.delivery_info['method'] = 'pickup'
                self.conversation_state = "delivery_details"
                return self._ask_pickup_details()
            else:
                return "I didn't catch that. Would you like delivery to your address or pickup from our restaurant?"

    def _ask_pickup_details(self) -> str:
        """Ask for pickup details"""
        return """
🏪 **PICKUP INFORMATION**

Great choice! You can pick up your order from our restaurant.

To complete your order, I just need:
1. **Name**: What name should we put this order under?
2. **Phone**: Your contact number for pickup notifications

Our address: 123 Main Street, Downtown
Estimated pickup time: 20-25 minutes

Please provide your name and phone number.
        """.strip()

    def manage_conversation_flow(self, user_input: str) -> str:
        """Enhanced conversation management with AI-driven flow"""
        response = self.route_request(user_input)
        
        # Enhanced flow management with AI detection
        if (self.conversation_state == "ordering" and 
            not self.customer_order.is_empty() and
            ("ORDER CONFIRMED" in response or "added to your order" in response.lower())):
            
            # Use AI to check if customer seems done or wants to continue
            try:
                completion_response = self.completion_chain.invoke({
                    "user_input": user_input,
                    "order_summary": str(self.customer_order)
                })
                
                completion_signal = completion_response['text'].strip().upper()
                
                if "COMPLETE" in completion_signal:
                    # Customer seems done, proceed to completion
                    response += "\n\n" + self._show_order_and_ask_delivery_preference()
                    self.conversation_state = "final_confirmation"
                elif self.upsell_attempts < self.max_upsell_attempts:
                    # Try upselling
                    upsell_suggestion = self.upselling_agent.suggest_upsell(self.customer_order)
                    response += f"\n\n{upsell_suggestion}"
                    self.conversation_state = "upselling"
                    self.upsell_attempts += 1
                else:
                    # Ask if they want anything else
                    response += "\n\n" + self._ask_completion_or_continue()
                    self.conversation_state = "ask_anything_else"
                    
            except Exception as e:
                # Fallback to original logic
                if self.upsell_attempts < self.max_upsell_attempts:
                    upsell_suggestion = self.upselling_agent.suggest_upsell(self.customer_order)
                    response += f"\n\n{upsell_suggestion}"
                    self.conversation_state = "upselling"
                    self.upsell_attempts += 1
                else:
                    response += "\n\n" + self._ask_completion_or_continue()
                    self.conversation_state = "ask_anything_else"
        
        return response

    def _handle_greeting(self) -> str:
        """Handle initial greeting"""
        return """
🍽️ Welcome to AI Bistro! I'm your personal dining assistant.

I'm here to help you with:
• Viewing our delicious menu
• Taking your order with customizations
• Suggesting perfect pairings and additions
• Answering any questions about our dishes

Would you like to see our menu to get started?
        """.strip()

    def _handle_order_modification(self, user_input: str) -> str:
        """Handle order modifications"""
        return "I'd be happy to help modify your order. What changes would you like to make?"

    def _handle_upsell_response(self, sanitized_input: str) -> str:
        """Handle upsell responses with better flow"""
        response = self.upselling_agent.process_upsell_response(
            sanitized_input, [], self.customer_order
        )
        
        # After upsell response, ask if they want anything else
        if any(word in sanitized_input.lower() for word in ['no', 'not', 'skip', 'nothing']):
            response += "\n\nNo problem! Would you like anything else, or shall we proceed with your order?"
            self.conversation_state = "ask_anything_else"
        elif any(word in sanitized_input.lower() for word in ['yes', 'add', 'sure']):
            response += "\n\nGreat! What would you like to add?"
            self.conversation_state = "ordering"
        
        return response

    def _handle_order_confirmation(self) -> str:
        """Handle order confirmation step"""
        if self.customer_order.is_empty():
            return "You don't have any items in your order yet. Would you like to see our menu?"
        
        # Move to asking if they want anything else
        self.conversation_state = "ask_anything_else"
        return "Perfect! Would you like anything else, or shall we proceed with your order?"

    def _ask_final_confirmation(self) -> str:
        """Ask for final order confirmation"""
        if self.customer_order.is_empty():
            return "You don't have any items in your order yet. Would you like to see our menu?"
        
        order_summary = self.order_agent.get_order_summary()
        
        confirmation_parts = [
            "🎯 **FINAL ORDER CONFIRMATION**",
            "",
            "Please review your complete order:",
            ""
        ]
        
        for item_data in order_summary['items']:
            name = item_data['name']
            quantity = item_data['quantity']
            unit_price = item_data['unit_price']
            total_price = item_data['total_price']
            
            if quantity == 1:
                confirmation_parts.append(f"• {name} - ${unit_price:.2f}")
            else:
                confirmation_parts.append(f"• {quantity}x {name} - ${unit_price:.2f} each (${total_price:.2f})")
            
            if item_data['customizations']:
                confirmation_parts.append(f"  └ Customizations: {', '.join(item_data['customizations'])}")
        
        confirmation_parts.extend([
            "",
            "─" * 40,
            f"Subtotal: ${order_summary['totals']['subtotal']:.2f}",
            f"Tax (8%): ${order_summary['totals']['tax']:.2f}",
            f"💰 **Total: ${order_summary['totals']['total']:.2f}**",
            "─" * 40,
            "",
            "Is this order correct? Please confirm by saying 'yes' or 'confirm' to proceed to delivery details."
        ])
        
        return "\n".join(confirmation_parts)

    def _ask_delivery_details(self) -> str:
        """Ask for delivery information"""
        return """
📍 **DELIVERY INFORMATION**

To complete your order, I'll need some delivery details:

1. **Name**: What name should we put this order under?
2. **Phone**: Your contact number for delivery updates
3. **Address**: Your delivery address
4. **Special Instructions**: Any delivery notes (optional)

Please provide these details, or you can give them to me one at a time. For example:
"My name is John Smith, phone is 555-123-4567, address is 123 Main St, and please ring the doorbell twice."
        """.strip()

    def _handle_delivery_details(self, user_input: str) -> str:
        """Handle delivery details collection with error tolerance"""
        try:
            # Extract information from input
            input_lower = user_input.lower()
            
            # Extract name
            name_patterns = [
                r'(?:name is|i\'m|my name is)\s+([a-zA-Z\s]+)(?:\s|,|$)',
                r'^([a-zA-Z\s]+?)(?:\s*,|\s+phone|\s+address|\s*$)'
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match and not self.delivery_info.get('name'):
                    potential_name = match.group(1).strip()
                    if len(potential_name.split()) <= 4 and all(word.isalpha() for word in potential_name.split()):
                        self.delivery_info['name'] = potential_name
                        break
            
            # Extract phone
            phone_pattern = r'(?:phone|number|call|contact)(?:\s+is|:)?\s*([0-9\-\(\)\s]+)'
            phone_match = re.search(phone_pattern, user_input, re.IGNORECASE)
            if phone_match:
                phone = re.sub(r'[^\d]', '', phone_match.group(1))
                if validate_phone_number(phone):
                    self.delivery_info['phone'] = phone
            
            # Extract address
            address_patterns = [
                r'(?:address is|address:)\s*([^,]+)(?:,|$)',
                r'(?:deliver to|address)\s+([0-9]+[^,]*?)(?:\s*,|\s*$)'
            ]
            
            for pattern in address_patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match and not self.delivery_info.get('address'):
                    self.delivery_info['address'] = match.group(1).strip()
                    break
            
            # Extract special instructions
            instruction_patterns = [
                r'(?:note|instruction|special|please)[:s]*\s*(.+)$',
                r'(?:and|also)\s+(.+)$'
            ]
            
            for pattern in instruction_patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match and not self.delivery_info.get('instructions'):
                    instruction = match.group(1).strip()
                    if not any(keyword in instruction.lower() for keyword in ['phone', 'address', 'name']):
                        self.delivery_info['instructions'] = instruction
                        break
            
            # Check what information we still need
            missing_info = []
            if not self.delivery_info.get('name'):
                missing_info.append("name")
            if not self.delivery_info.get('phone'):
                missing_info.append("phone number")
            if not self.delivery_info.get('address'):
                missing_info.append("delivery address")
            
            if missing_info:
                collected_info = []
                if self.delivery_info.get('name'):
                    collected_info.append(f"✅ Name: {self.delivery_info['name']}")
                if self.delivery_info.get('phone'):
                    collected_info.append(f"✅ Phone: {self.delivery_info['phone']}")
                if self.delivery_info.get('address'):
                    collected_info.append(f"✅ Address: {self.delivery_info['address']}")
                
                response_parts = []
                if collected_info:
                    response_parts.append("Great! I've got:")
                    response_parts.extend(collected_info)
                    response_parts.append("")
                
                if len(missing_info) == 1:
                    response_parts.append(f"I still need your {missing_info[0]}.")
                else:
                    response_parts.append(f"I still need your {', '.join(missing_info[:-1])} and {missing_info[-1]}.")
                
                return "\n".join(response_parts)
            
            else:
                # All information collected, proceed to completion
                self.conversation_state = "completed"
                return self._generate_final_summary()
        
        except Exception as e:
            return "I had trouble understanding those details. Could you please provide your name, phone number, and delivery address again?"

    def _generate_final_summary(self) -> str:
        """Generate final order summary with delivery details"""
        order_summary = self.order_agent.get_order_summary()
        estimated_time = 25 + (len(order_summary['items']) * 5)  # Estimate based on items
        
        summary_parts = [
            "🎉 **ORDER SUCCESSFULLY PLACED!** 🎉",
            "",
            "📋 **ORDER SUMMARY**",
            "═" * 50
        ]
        
        # Order items
        for item_data in order_summary['items']:
            name = item_data['name']
            quantity = item_data['quantity']
            unit_price = item_data['unit_price']
            total_price = item_data['total_price']
            
            if quantity == 1:
                summary_parts.append(f"• {name} - ${unit_price:.2f}")
            else:
                summary_parts.append(f"• {quantity}x {name} - ${unit_price:.2f} each (${total_price:.2f})")
            
            if item_data['customizations']:
                summary_parts.append(f"  └ Customizations: {', '.join(item_data['customizations'])}")
        
        # Totals
        summary_parts.extend([
            "",
            "─" * 40,
            f"Subtotal: ${order_summary['totals']['subtotal']:.2f}",
            f"Tax (8%): ${order_summary['totals']['tax']:.2f}",
            f"💰 **Total: ${order_summary['totals']['total']:.2f}**",
            "",
            "📍 **DELIVERY DETAILS**",
            "─" * 40,
            f"Name: {self.delivery_info.get('name', 'N/A')}",
            f"Phone: {self.delivery_info.get('phone', 'N/A')}",
            f"Address: {self.delivery_info.get('address', 'N/A')}"
        ])
        
        if self.delivery_info.get('instructions'):
            summary_parts.append(f"Special Instructions: {self.delivery_info['instructions']}")
        
        summary_parts.extend([
            "",
            "⏰ **DELIVERY INFORMATION**",
            "─" * 40,
            f"Estimated Delivery Time: {estimated_time} minutes",
            "You'll receive SMS updates on your order status",
            "",
            "🍽️ Thank you for choosing AI Bistro! Your delicious meal is being prepared with care.",
            "Enjoy your dining experience! 🌟"
        ])
        
        return "\n".join(summary_parts)

    def get_conversation_state(self) -> dict:
        """Get current conversation state for debugging/monitoring"""
        return {
            "state": self.conversation_state,
            "order_items_count": len(self.customer_order.items),
            "order_total": self.customer_order.get_total(),
            "customer_name": self.customer_name,
            "delivery_info": self.delivery_info,
            "upsell_attempts": self.upsell_attempts
        }