from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
import operator

# Define the state structure for our restaurant graph
class RestaurantState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    current_order: dict
    conversation_stage: str  # greeting, menu_browsing, ordering, upselling, confirming
    customer_info: dict
    order_total: float
    upsell_attempts: int
    menu_displayed: bool

class RestaurantGraph:
    def __init__(self, coordinator_agent):
        self.coordinator = coordinator_agent
        self.graph = self.build_graph()
    
    def build_graph(self):
        """Build the conversation flow graph"""
        workflow = StateGraph(RestaurantState)
        
        # Add nodes for different conversation stages
        workflow.add_node("greeting", self._greeting_node)
        workflow.add_node("menu_display", self._menu_display_node)
        workflow.add_node("order_processing", self._order_processing_node)
        workflow.add_node("customization", self._customization_node)
        workflow.add_node("upselling", self._upselling_node)
        workflow.add_node("order_confirmation", self._order_confirmation_node)
        workflow.add_node("completion", self._completion_node)
        
        # Define the conversation flow
        workflow.add_edge(START, "greeting")
        workflow.add_conditional_edges(
            "greeting",
            self._route_after_greeting,
            {
                "show_menu": "menu_display",
                "place_order": "order_processing",
                "ask_question": "menu_display"
            }
        )
        
        workflow.add_conditional_edges(
            "menu_display",
            self._route_after_menu,
            {
                "place_order": "order_processing",
                "ask_question": "menu_display",
                "continue_browsing": "menu_display"
            }
        )
        
        workflow.add_conditional_edges(
            "order_processing",
            self._route_after_order,
            {
                "customize": "customization",
                "upsell": "upselling",
                "confirm": "order_confirmation",
                "continue_ordering": "order_processing"
            }
        )
        
        workflow.add_conditional_edges(
            "customization",
            self._route_after_customization,
            {
                "upsell": "upselling",
                "confirm": "order_confirmation",
                "continue_ordering": "order_processing"
            }
        )
        
        workflow.add_conditional_edges(
            "upselling",
            self._route_after_upselling,
            {
                "confirm": "order_confirmation",
                "continue_ordering": "order_processing",
                "complete": "completion"
            }
        )
        
        workflow.add_conditional_edges(
            "order_confirmation",
            self._route_after_confirmation,
            {
                "complete": "completion",
                "modify": "order_processing"
            }
        )
        
        workflow.add_edge("completion", END)
        
        return workflow.compile()
    
    def _greeting_node(self, state: RestaurantState) -> RestaurantState:
        """Handle initial greeting"""
        if state["conversation_stage"] != "greeting":
            return state
            
        response = self.coordinator._handle_greeting()
        state["conversation_stage"] = "menu_browsing"
        return state
    
    def _menu_display_node(self, state: RestaurantState) -> RestaurantState:
        """Handle menu display and queries"""
        state["menu_displayed"] = True
        state["conversation_stage"] = "menu_browsing"
        return state
    
    def _order_processing_node(self, state: RestaurantState) -> RestaurantState:
        """Handle order processing"""
        state["conversation_stage"] = "ordering"
        # Update order total if items were added
        if self.coordinator.customer_order.items:
            state["order_total"] = self.coordinator.customer_order.get_total()
            state["current_order"] = {
                "items": [str(item) for item in self.coordinator.customer_order.items],
                "total": state["order_total"]
            }
        return state
    
    def _customization_node(self, state: RestaurantState) -> RestaurantState:
        """Handle order customizations"""
        state["conversation_stage"] = "customizing"
        return state
    
    def _upselling_node(self, state: RestaurantState) -> RestaurantState:
        """Handle upselling attempts"""
        state["conversation_stage"] = "upselling"
        state["upsell_attempts"] = state.get("upsell_attempts", 0) + 1
        return state
    
    def _order_confirmation_node(self, state: RestaurantState) -> RestaurantState:
        """Handle order confirmation"""
        state["conversation_stage"] = "confirming"
        return state
    
    def _completion_node(self, state: RestaurantState) -> RestaurantState:
        """Handle order completion"""
        state["conversation_stage"] = "completed"
        return state
    
    # Routing functions
    def _route_after_greeting(self, state: RestaurantState) -> str:
        """Route after greeting based on user intent"""
        return "show_menu"  # Default flow
    
    def _route_after_menu(self, state: RestaurantState) -> str:
        """Route after menu display"""
        return "place_order"  # Simplified routing
    
    def _route_after_order(self, state: RestaurantState) -> str:
        """Route after order processing"""
        if state.get("order_total", 0) > 0:
            return "upsell"
        return "continue_ordering"
    
    def _route_after_customization(self, state: RestaurantState) -> str:
        """Route after customization"""
        return "upsell"
    
    def _route_after_upselling(self, state: RestaurantState) -> str:
        """Route after upselling"""
        upsell_attempts = state.get("upsell_attempts", 0)
        if upsell_attempts >= 2 or state.get("order_total", 0) > 30:
            return "confirm"
        return "confirm"
    
    def _route_after_confirmation(self, state: RestaurantState) -> str:
        """Route after confirmation"""
        return "complete"
    
    def process_conversation(self, user_input: str, current_state: RestaurantState = None) -> tuple[str, RestaurantState]:
        """Process a conversation turn through the graph"""
        if current_state is None:
            current_state = {
                "messages": [],
                "current_order": {},
                "conversation_stage": "greeting",
                "customer_info": {},
                "order_total": 0.0,
                "upsell_attempts": 0,
                "menu_displayed": False
            }
        
        # Process through coordinator
        response = self.coordinator.manage_conversation_flow(user_input)
        
        # Update state based on coordinator's current state
        coordinator_state = self.coordinator.get_conversation_state()
        current_state["conversation_stage"] = coordinator_state["state"]
        current_state["order_total"] = coordinator_state["order_total"]
        
        if self.coordinator.customer_order.items:
            current_state["current_order"] = {
                "items": [str(item) for item in self.coordinator.customer_order.items],
                "total": current_state["order_total"]
            }
        
        return response, current_state