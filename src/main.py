import os
import sys
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from agents.new_coordinator_agent import NewCoordinatorAgent
from langchain_google_genai import ChatGoogleGenerativeAI
import uuid

class RestaurantAIAgent:
    def __init__(self):
        """Initialize the Router-based Restaurant AI Agent system"""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        # Initialize the new Router-based coordinator
        self.coordinator = NewCoordinatorAgent()
        
        # Session management
        self.session_id = str(uuid.uuid4())
        
        print("🤖 Router-based Restaurant AI Agent initialized successfully!")
        print("🎯 All inputs now go through intelligent Router Agent first!")

    def start_conversation(self):
        """Start an interactive conversation with the customer"""
        print("\n" + "="*60)
        print("🍽️ WELCOME TO AI BISTRO - ROUTER-POWERED ASSISTANT 🍽️")
        print("="*60)
        print("🎯 Enhanced with intelligent routing!")
        print("I can understand:")
        print("• 'coc' or 'coca' → Coca Cola")
        print("• 'burger' → Classic Burger")
        print("• '2 burgers and 3 cokes' → Multiple items at once")
        print("• Complex orders with customizations")
        print("• Ambiguous requests that I'll clarify")
        print("\nType 'quit' or 'exit' to end the conversation")
        print("-"*60)
        
        # Initial greeting
        response, conversation_state = self.coordinator.process_user_input("hello")
        print(f"\n🤖 AI Bistro: {response}")
        
        # Main conversation loop
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                # Check for quit commands
                if user_input.lower() in ['quit', 'exit']:
                    print("\n🤖 AI Bistro: Thank you for visiting AI Bistro! Have a wonderful day! 🍽️")
                    break
                
                if not user_input:
                    print("🤖 AI Bistro: I didn't catch that. Could you please say something?")
                    continue
                
                # Process through the new Router-based system
                response, conversation_state = self.coordinator.process_user_input(user_input)
                
                print(f"\n🤖 AI Bistro: {response}")
                
                # Show debug info if in development mode
                if os.getenv("DEBUG_MODE", "false").lower() == "true":
                    self._show_debug_info(conversation_state)
                
                # Check if order is completed
                if conversation_state.get("customer_intent") == "COMPLETED":
                    print("\n" + "="*60)
                    print("🎉 ORDER PROCESS COMPLETED! 🎉")
                    print("="*60)
                    
                    # Ask if they want to place another order
                    new_order = input("\nWould you like to place another order? (yes/no): ").strip().lower()
                    if new_order in ['yes', 'y', 'sure', 'okay']:
                        self.coordinator.reset_conversation()
                        print("\n🔄 Starting a new order...")
                        response, _ = self.coordinator.process_user_input("hello")
                        print(f"\n🤖 AI Bistro: {response}")
                    else:
                        print("\n🤖 AI Bistro: Thank you for choosing AI Bistro! Have a wonderful day! 🍽️")
                        break
                
                # Handle human intervention requests
                if conversation_state.get("needs_intervention"):
                    print("\n🆘 Human operator has been notified and will assist shortly.")
                
            except KeyboardInterrupt:
                print("\n\n🤖 AI Bistro: Thank you for visiting! Have a great day! 🍽️")
                break
            except Exception as e:
                print(f"\n❌ Sorry, I encountered an error: {str(e)}")
                print("Please try again or contact our support team.")

    def _show_debug_info(self, conversation_state):
        """Show debug information for development"""
        print("\n" + "─"*40)
        print("🔍 DEBUG INFO:")
        print(f"Intent: {conversation_state.get('customer_intent', 'Unknown')}")
        print(f"Stage: {conversation_state.get('conversation_stage', 'Unknown')}")
        print(f"Order Items: {len(conversation_state.get('current_order', []))}")
        print(f"Total: ${conversation_state.get('order_total', 0):.2f}")
        print(f"Last Agent: {conversation_state.get('last_agent', 'None')}")
        print("─"*40)

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
        print(f"🆘 Human intervention triggered: {reason}")

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
        print(f"❌ Configuration Error: {e}")
        print("Please make sure you have set up your environment variables correctly.")
        print("Create a .env file with: GOOGLE_API_KEY=your_api_key_here")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        print("Please check your setup and try again.")

if __name__ == "__main__":
    main()