import os
import sys
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from agents.new_coordinator_agent import NewCoordinatorAgent
import uuid
from utils.console import ConsoleUI

class RestaurantAIAgent:
    def __init__(self):
        """Initialize the Router-based Restaurant AI Agent system"""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        # Console UI
        self.ui = ConsoleUI()
        
        # Initialize the new Router-based coordinator
        self.coordinator = NewCoordinatorAgent()
        
        # Session management
        self.session_id = str(uuid.uuid4())
        
        # Runtime debug toggle
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        
        # Concise startup
        self.ui.header("AI Bistro", "Router-powered assistant")
        self.ui.info("Commands: /help, /menu, /reset, /debug, /state, quit")

    def start_conversation(self):
        """Start an interactive conversation with the customer"""
        
        # Initial greeting
        response, conversation_state = self.coordinator.process_user_input("hello")
        self.ui.ai_response(response)
        
        # Main conversation loop
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                # Check for quit commands
                if user_input.lower() in ['quit', 'exit']:
                    self.ui.ai_response("Thanks for visiting AI Bistro. Have a great day!")
                    break
                
                if not user_input:
                    self.ui.warn("I didn't catch that. Please say something.")
                    continue
                
                # Slash commands
                if user_input.startswith("/"):
                    handled = self._handle_command(user_input)
                    if handled:
                        continue
                
                # Process through the new Router-based system
                response, conversation_state = self.coordinator.process_user_input(user_input)
                
                self.ui.ai_response(response)
                
                # Show debug info if enabled
                if self.debug_mode:
                    self._show_debug_info(conversation_state)
                
                # Check if order is completed
                if conversation_state.get("customer_intent") == "COMPLETED":
                    # Show order summary in a table
                    details = self.get_order_details()
                    items = details.get("items", [])
                    totals = details.get("totals", {})
                    if items:
                        self.ui.rule("Order Summary")
                        self.ui.order_table(items, totals)
                    
                    # Ask if they want to place another order
                    new_order = input("\nStart a new order? (y/n): ").strip().lower()
                    if new_order in ['yes', 'y']:
                        self.coordinator.reset_conversation()
                        self.ui.info("Starting a new order...")
                        response, _ = self.coordinator.process_user_input("hello")
                        self.ui.ai_response(response)
                    else:
                        self.ui.ai_response("Thank you for choosing AI Bistro!")
                        break
                
                # Handle human intervention requests
                if conversation_state.get("needs_intervention"):
                    self.ui.warn("A human operator will assist shortly.")
                
            except KeyboardInterrupt:
                self.ui.ai_response("Thanks for visiting AI Bistro. Goodbye!")
                break
            except Exception as e:
                self.ui.error(f"Error: {str(e)}")
                self.ui.info("Please try again or contact support.")

    def _handle_command(self, cmd: str) -> bool:
        """Handle slash commands. Returns True if handled."""
        name = cmd.lower().strip()
        if name in ("/help", "/h"):
            self.ui.ai_response("""
            Available commands:\n
            - /menu   Show the menu\n
            - /state  Show current state\n
            - /reset  Reset the conversation\n
            - /debug  Toggle debug info\n
            - quit    Exit the assistant
            """.strip(), title="Help")
            return True
        if name == "/menu":
            self.ui.ai_response(self.coordinator.menu_agent.display_menu(), title="Menu")
            return True
        if name == "/reset":
            self.reset_conversation()
            self.ui.success("Conversation reset.")
            response, _ = self.coordinator.process_user_input("hello")
            self.ui.ai_response(response)
            return True
        if name == "/debug":
            self.debug_mode = not self.debug_mode
            self.ui.info(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
            return True
        if name == "/state":
            state = self.coordinator.shared_memory.to_dict()
            self._show_debug_info(state)
            return True
        
        self.ui.warn("Unknown command. Type /help for options.")
        return True

    def _show_debug_info(self, conversation_state):
        """Show debug information for development"""
        data = {
            "Intent": conversation_state.get('customer_intent', 'Unknown'),
            "Stage": conversation_state.get('conversation_stage', 'Unknown'),
            "Order Items": len(conversation_state.get('current_order', [])),
            "Total": f"${conversation_state.get('order_total', 0):.2f}",
            "Last Agent": conversation_state.get('last_agent', 'None'),
        }
        self.ui.debug_table(data, title="Debug Info")

    def process_single_request(self, user_input: str) -> str:
        """Process a single request (useful for API integration)"""
        try:
            response, _ = self.coordinator.process_user_input(user_input)
            return response
        except Exception as e:
            return f"I'm sorry, I encountered an error: {str(e)}. Please try again."

    def get_order_details(self) -> dict:
        """Get current order details for external systems"""
        conversation_state = self.coordinator.get_conversation_state()
        
        return {
            "session_id": self.session_id,
            "order_id": conversation_state.get("session_id"),
            "items": self.coordinator.shared_memory.current_order,
            "totals": {
                "subtotal": sum(item.get("price", 0) * item.get("quantity", 1) 
                              for item in self.coordinator.shared_memory.current_order),
                "tax": sum(item.get("price", 0) * item.get("quantity", 1) 
                          for item in self.coordinator.shared_memory.current_order) * 0.08,
                "total": self.coordinator.shared_memory.order_total
            },
            "status": conversation_state.get("customer_intent", "UNKNOWN"),
            "needs_intervention": conversation_state.get("needs_intervention", False),
            "routing_info": {
                "last_agent": conversation_state.get("last_agent"),
                "upsell_attempts": conversation_state.get("upsell_attempts", 0),
                "error_count": conversation_state.get("error_count", 0)
            }
        }

    def get_intelligent_suggestions(self, partial_input: str) -> str:
        """Get intelligent suggestions for partial/unclear input"""
        return self.coordinator.handle_intelligent_suggestions(partial_input)

    def simulate_human_intervention(self, reason: str = "Testing intervention"):
        """Simulate human intervention for testing purposes"""
        self.coordinator.shared_memory.trigger_human_intervention(reason)
        self.ui.warn(f"Human intervention triggered: {reason}")

    def reset_conversation(self):
        """Reset the conversation state"""
        self.coordinator.reset_conversation()
        self.session_id = str(uuid.uuid4())

    def get_conversation_analytics(self) -> dict:
        """Get analytics about the conversation for monitoring"""
        state = self.coordinator.get_conversation_state()
        memory = self.coordinator.shared_memory
        
        return {
            "session_info": {
                "session_id": self.session_id,
                "duration_seconds": (memory.last_activity - memory.session_start).total_seconds(),
                "total_interactions": len(memory.conversation_history)
            },
            "order_analytics": {
                "items_count": len(memory.current_order),
                "order_value": memory.order_total,
                "avg_item_price": memory.order_total / max(len(memory.current_order), 1)
            },
            "agent_usage": {
                "last_agent": state.get("last_agent"),
                "upsell_attempts": state.get("upsell_attempts", 0),
                "human_interventions": 1 if state.get("needs_intervention") else 0
            },
            "conversation_flow": {
                "current_intent": state.get("customer_intent"),
                "current_stage": state.get("conversation_stage"),
                "errors_encountered": state.get("error_count", 0)
            }
        }

def main():
    """Main function to run the restaurant AI agent"""
    try:
        # Initialize the agent
        agent = RestaurantAIAgent()
        
        # Start the interactive conversation
        agent.start_conversation()
        
    except ValueError as e:
        ConsoleUI().error(f"Configuration Error: {e}")
        ConsoleUI().info("Create a .env file with: GOOGLE_API_KEY=your_api_key_here")
    except Exception as e:
        ConsoleUI().error(f"Unexpected Error: {e}")
        ConsoleUI().info("Please check your setup and try again.")

if __name__ == "__main__":
    main()