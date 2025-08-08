from langchain_google_genai import ChatGoogleGenerativeAI
from agents.router_agent import RouterAgent, RouteDecision
from agents.menu_agent import MenuAgent
from agents.order_agent import OrderAgent
from agents.upselling_agent import UpsellingAgent
from models.shared_memory import SharedMemory
from tools.validation_tools import sanitize_input
from config import Config
import os
import uuid
from typing import Tuple, Dict, Any

class NewCoordinatorAgent:
    """
    New Coordinator Agent that implements Router-first architecture
    All user inputs go through Router Agent first for intelligent routing
    """
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=Config.MODEL_NAME,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=Config.MODEL_TEMPERATURE
        )
        
        # Initialize shared memory for all agents
        self.shared_memory = SharedMemory()
        
        # Initialize Router Agent (the central decision maker)
        self.router_agent = RouterAgent(llm=self.llm)
        
        # Initialize specialized agents
        self.menu_agent = MenuAgent(llm=self.llm)
        self.order_agent = OrderAgent(llm=self.llm, shared_memory=self.shared_memory)
        self.upselling_agent = UpsellingAgent(llm=self.llm)
        
        # Conversation session ID
        self.session_id = str(uuid.uuid4())
        
        if os.getenv("DEBUG_MODE", "false").lower() == "true":
            print("🤖 New Router-based Restaurant AI Agent initialized!")

    def process_user_input(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """
        Main conversation processing method - all inputs go through Router first
        """
        try:
            # Step 1: Router Agent analyzes and routes the input
            conversation_context = self.shared_memory.get_context_summary()
            route_decision = self.router_agent.route_conversation(user_input, conversation_context)
            
            # Step 2: Check if human intervention is needed
            if route_decision.agent == "human" or self.shared_memory.needs_human_intervention:
                return self._handle_human_intervention(user_input, route_decision), self.shared_memory.to_dict()
            
            # Step 3: Route to appropriate agent based on Router's decision
            response = self._execute_agent_action(user_input, route_decision)
            
            # Step 4: Add to conversation history
            self.shared_memory.add_to_history(user_input, response, route_decision.agent)
            
            # Step 5: Post-processing and flow management
            response = self._post_process_response(response, route_decision)
            
            return response, self.shared_memory.to_dict()
            
        except Exception as e:
            error_message = f"I encountered an error: {str(e)}. Let me try to help you differently."
            self.shared_memory.increment_error(str(e))
            return error_message, self.shared_memory.to_dict()

    def _execute_agent_action(self, user_input: str, route_decision: RouteDecision) -> str:
        """Execute the action based on Router's decision"""
        
        # Handle clarification needs first
        if route_decision.needs_clarification:
            self.shared_memory.pending_clarifications.append(route_decision.clarification_question)
            return route_decision.clarification_question or "Could you please clarify what you're looking for?"
        
        # Route to appropriate agent
        if route_decision.agent == "menu":
            return self._handle_menu_request(user_input, route_decision)
            
        elif route_decision.agent == "order":
            return self._handle_order_request(user_input, route_decision)
            
        elif route_decision.agent == "upselling":
            return self._handle_upselling_request(user_input, route_decision)
            
        elif route_decision.agent == "finalization":
            return self._handle_finalization_request(user_input, route_decision)
            
        elif route_decision.agent == "delivery":
            return self._handle_delivery_request(user_input, route_decision)
            
        else:
            # Default to menu for unclear requests
            return self._handle_menu_request(user_input, route_decision)

    def _handle_menu_request(self, user_input: str, route_decision: RouteDecision) -> str:
        """Handle menu-related requests"""
        self.shared_memory.set_customer_intent("BROWSING", "User browsing menu")
        
        if "menu" in user_input.lower() or "show" in user_input.lower():
            self.shared_memory.menu_displayed = True
            return self.menu_agent.display_menu()
        elif "recommend" in user_input.lower():
            return self.menu_agent.get_recommendations()
        else:
            return self.menu_agent.handle_menu_query(user_input)

    def _handle_order_request(self, user_input: str, route_decision: RouteDecision) -> str:
        """Handle order-related requests using extracted items from Router"""
        self.shared_memory.set_customer_intent("ORDERING", "User placing or modifying order")

        # If router classified it as a modification, apply modifications deterministically
        if route_decision.user_intent == "MODIFY_ORDER":
            modification_result = self.order_agent.handle_order_modification(user_input)
            # If we were waiting for delivery, keep the flow there
            if self.shared_memory.conversation_stage == "awaiting_delivery":
                return f"{modification_result}\n\nShall we proceed with delivery or pickup?"
            return modification_result
        
        # Use Router's extracted items for intelligent processing when placing/adding items
        if route_decision.extracted_items:
            result = self.order_agent.process_order_with_extracted_items(
                user_input, route_decision.extracted_items
            )
            
            # Handle the result
            if result.success:
                response_parts = [result.message]
                
                # Show order summary if items were added
                if result.added_items:
                    order_summary = self.order_agent.get_order_summary()
                    response_parts.append(f"\n📋 Current order total: ${order_summary['totals']['total']:.2f}")
                
                # Handle failed items
                if result.failed_items:
                    failed_names = [item.get("requested_name", "") for item in result.failed_items]
                    response_parts.append(f"\n⚠️ Couldn't find: {', '.join(failed_names)}")
                    response_parts.append("Would you like to see our menu for available items?")
                
                return "\n".join(response_parts)
            else:
                return result.message
        else:
            # No items extracted, ask for clarification
            return "I'd be happy to take your order! What would you like to order from our menu?"

    def _handle_upselling_request(self, user_input: str, route_decision: RouteDecision) -> str:
        """Handle upselling based on current order"""
        if not self.shared_memory.current_order:
            return "Would you like to add something to your order?"
        
        # Check if we've already tried upselling too much
        if self.shared_memory.upsell_attempts >= self.shared_memory.max_upsell_attempts:
            return "Would you like anything else, or shall we proceed with your order?"
        
        # Get upselling suggestion
        # Convert shared memory order to the format expected by upselling agent
        order_items = []
        for item in self.shared_memory.current_order:
            # Create a mock OrderItem-like object
            mock_item = type('MockItem', (), {
                'name': item.get('name', ''),
                'price': item.get('price', 0),
                'quantity': item.get('quantity', 1)
            })()
            order_items.append(mock_item)
        
        mock_order = type('MockOrder', (), {'items': order_items})()
        
        try:
            upsell_response = self.upselling_agent.suggest_upsell(mock_order)
            self.shared_memory.upsell_attempts += 1
            return upsell_response
        except:
            return "Would you like to add any drinks or sides to complete your order?"

    def _handle_finalization_request(self, user_input: str, route_decision: RouteDecision) -> str:
        """Handle order finalization and completion"""
        
        # Check if user wants to cancel during finalization
        if route_decision.wants_order_change and route_decision.user_intent == "CANCEL_ORDER":
            self.shared_memory.clear_order()
            self.shared_memory.set_customer_intent("GREETING", "Order cancelled by user")
            self.shared_memory.conversation_stage = "greeting"
            return "Your order has been cancelled. Would you like to start a new order?"
        
        self.shared_memory.set_customer_intent("FINALIZING", "User finalizing order")
        
        # Validate order is ready
        validation = self.order_agent.validate_order_completion()
        
        if not validation["ready"]:
            return validation["message"]
        
        # Show final order summary and proceed to delivery details
        order_summary = self.order_agent.get_order_summary()
        
        response_parts = [
            "🎯 **FINAL ORDER CONFIRMATION**",
            "",
            "Here's your complete order:",
            ""
        ]
        
        for item in order_summary['items']:
            if item['quantity'] == 1:
                response_parts.append(f"• {item['name']} - ${item['unit_price']:.2f}")
            else:
                response_parts.append(f"• {item['quantity']}x {item['name']} - ${item['unit_price']:.2f} each")
            
            if item['customizations']:
                response_parts.append(f"  └ Customizations: {', '.join(item['customizations'])}")
        
        response_parts.extend([
            "",
            f"💰 **Total: ${order_summary['totals']['total']:.2f}** (includes tax)",
            "",
            "🚚 Would you like this delivered or would you prefer pickup?"
        ])
        
        # Set stage to await delivery method
        self.shared_memory.conversation_stage = "awaiting_delivery"
        self.shared_memory.set_customer_intent("DELIVERY_METHOD", "Waiting for delivery method choice")
        
        return "\n".join(response_parts)

    def _handle_delivery_request(self, user_input: str, route_decision: RouteDecision) -> str:
        """Handle delivery method selection and processing"""
        
        # Check if user wants to change order instead of answering delivery question
        if route_decision.wants_order_change:
            if route_decision.user_intent == "MODIFY_ORDER":
                # Apply modifications (remove/change quantities, etc.)
                modification_result = self.order_agent.handle_order_modification(user_input)
                # Stay in delivery stage after modification
                self.shared_memory.conversation_stage = "awaiting_delivery"
                self.shared_memory.set_customer_intent("DELIVERY_METHOD", "Waiting for delivery method choice")
                return f"{modification_result}\n\nShall we proceed with delivery or pickup?"
                
            elif route_decision.user_intent == "CANCEL_ORDER":
                # User wants to cancel
                self.shared_memory.clear_order()
                self.shared_memory.set_customer_intent("GREETING", "Order cancelled by user")
                self.shared_memory.conversation_stage = "greeting"
                return "Your order has been cancelled. Would you like to start a new order?"
        
        # Handle delivery method selection
        if route_decision.delivery_method:
            self.shared_memory.delivery_method = route_decision.delivery_method
            self.shared_memory.conversation_stage = "completed"
            self.shared_memory.set_customer_intent("COMPLETED", f"Order completed with {route_decision.delivery_method}")
            
            if route_decision.delivery_method == "delivery":
                response_parts = [
                    "🚚 Perfect! Your order will be delivered.",
                    "",
                    "📋 **ORDER SUMMARY**",
                    f"• Order Total: ${self.shared_memory.order_total:.2f}",
                    f"• Delivery Method: Delivery",
                    f"• Estimated Delivery Time: 30-45 minutes",
                    "",
                    "Thank you for your order! We'll start preparing it right away.",
                    "You'll receive updates on your order status."
                ]
            else:  # pickup
                response_parts = [
                    "🥡 Great! Your order will be ready for pickup.",
                    "",
                    "📋 **ORDER SUMMARY**",
                    f"• Order Total: ${self.shared_memory.order_total:.2f}",
                    f"• Pickup Method: Pickup",
                    f"• Estimated Pickup Time: 15-20 minutes",
                    "",
                    "Thank you for your order! We'll start preparing it right away.",
                    "We'll notify you when it's ready for pickup."
                ]
            
            return "\n".join(response_parts)
        
        # If no clear delivery method detected, ask for clarification
        return (
            "I didn't quite catch that. Please let me know:\n"
            "• Type 'delivery' if you'd like it delivered\n"
            "• Type 'pickup' if you'd prefer to pick it up\n"
            "• Or feel free to add more items to your order first!"
        )

    def _handle_human_intervention(self, user_input: str, route_decision: RouteDecision) -> str:
        """Handle cases requiring human intervention"""
        intervention_messages = [
            "I understand this might be a complex request. Let me connect you with our human assistant.",
            f"Request: {user_input}",
            f"Reason: {self.shared_memory.intervention_reason or 'Complex query requiring human assistance'}",
            "",
            "In the meantime, I can still help with basic menu questions or simple orders."
        ]
        
        return "\n".join(intervention_messages)

    def _post_process_response(self, response: str, route_decision: RouteDecision) -> str:
        """Post-process response and determine next steps"""
        
        # If order was just placed, consider upselling
        if (route_decision.agent == "order" and 
            self.shared_memory.current_order and 
            self.shared_memory.upsell_attempts < self.shared_memory.max_upsell_attempts):
            
            # Add subtle upselling suggestion
            upsell_suggestions = [
                "\n\n💡 Would you like to add any drinks or sides?",
                "\n\n🍟 How about some appetizers to start?",
                "\n\n🥤 Any beverages to go with that?"
            ]
            
            import random
            response += random.choice(upsell_suggestions)
            self.shared_memory.upsell_attempts += 1
        
        return response

    def reset_conversation(self):
        """Reset conversation state for new session"""
        self.shared_memory = SharedMemory()
        self.session_id = str(uuid.uuid4())
        if os.getenv("DEBUG_MODE", "false").lower() == "true":
            print("🔄 Conversation reset. Starting fresh!")

    def get_conversation_state(self) -> Dict[str, Any]:
        """Get current conversation state for monitoring"""
        return {
            "session_id": self.session_id,
            "customer_intent": self.shared_memory.customer_intent,
            "conversation_stage": self.shared_memory.conversation_stage,
            "order_items": len(self.shared_memory.current_order),
            "order_total": self.shared_memory.order_total,
            "last_agent": self.shared_memory.last_agent,
            "needs_intervention": self.shared_memory.needs_human_intervention,
            "upsell_attempts": self.shared_memory.upsell_attempts,
            "error_count": self.shared_memory.error_count
        }

    def handle_intelligent_suggestions(self, partial_input: str) -> str:
        """Get intelligent suggestions for partial input"""
        suggestions = self.router_agent.get_intelligent_suggestions(partial_input)
        
        if suggestions:
            response_parts = [
                "🤔 I think you might be looking for:",
                ""
            ]
            
            for i, suggestion in enumerate(suggestions, 1):
                response_parts.append(f"{i}. {suggestion}")
            
            response_parts.append("\nWhich one interests you?")
            return "\n".join(response_parts)
        else:
            return "I'm not sure what you're looking for. Would you like to see our menu?"