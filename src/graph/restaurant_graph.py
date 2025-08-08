from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
import operator

# Define the state structure for our restaurant graph
class RestaurantState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    current_order: dict
    conversation_stage: str  # greeting, browsing, ordering, upselling, finalizing, delivery, completed
    customer_info: dict
    order_total: float
    upsell_attempts: int
    menu_displayed: bool
    customer_intent: str
    last_agent: str
    needs_intervention: bool
    router_decision: dict  # Store router's decision for transparency

class RestaurantGraph:
    def __init__(self, coordinator_agent):
        """Initialize with the new NewCoordinatorAgent"""
        self.coordinator = coordinator_agent
        self.graph = self.build_graph()
    
    def build_graph(self):
        """Build the conversation flow graph showing Router Agent as central hub"""
        workflow = StateGraph(RestaurantState)
        
        # Add ROUTER as the central decision-making node
        workflow.add_node("router_agent", self._router_agent_node)
        
        # Add specialized agent nodes
        workflow.add_node("menu_agent", self._menu_agent_node)
        workflow.add_node("order_agent", self._order_agent_node)
        workflow.add_node("upselling_agent", self._upselling_agent_node)
        workflow.add_node("finalization_agent", self._finalization_agent_node)
        workflow.add_node("delivery_agent", self._delivery_agent_node)
        workflow.add_node("human_intervention", self._human_intervention_node)
        
        # Add conversation flow nodes (these represent the conversation stages)
        workflow.add_node("greeting", self._greeting_node)
        workflow.add_node("menu_browsing", self._menu_browsing_node)
        workflow.add_node("ordering", self._ordering_node)
        workflow.add_node("upselling", self._upselling_node)
        workflow.add_node("finalizing", self._finalizing_node)
        workflow.add_node("delivery_method", self._delivery_method_node)
        workflow.add_node("completion", self._completion_node)
        
        # Define the Router-centric flow
        workflow.add_edge(START, "router_agent")
        
        # Router routes to appropriate agents based on analysis
        workflow.add_conditional_edges(
            "router_agent",
            self._route_from_router,
            {
                "menu_agent": "menu_agent",
                "order_agent": "order_agent", 
                "upselling_agent": "upselling_agent",
                "finalization_agent": "finalization_agent",
                "delivery_agent": "delivery_agent",
                "human_intervention": "human_intervention",
                "greeting": "greeting"
            }
        )
        
        # Agent nodes route to conversation flow nodes
        workflow.add_edge("menu_agent", "menu_browsing")
        workflow.add_edge("order_agent", "ordering")
        workflow.add_edge("upselling_agent", "upselling")
        workflow.add_edge("finalization_agent", "finalizing")
        workflow.add_edge("delivery_agent", "delivery_method")
        
        # Conversation flow nodes route back to router for next decision
        workflow.add_conditional_edges(
            "greeting",
            self._route_back_to_router,
            {
                "router_agent": "router_agent",
                "completion": "completion",
                "human_intervention": "human_intervention"
            }
        )
        
        workflow.add_conditional_edges(
            "menu_browsing",
            self._route_back_to_router,
            {
                "router_agent": "router_agent",
                "completion": "completion",
                "human_intervention": "human_intervention"
            }
        )
        
        workflow.add_conditional_edges(
            "ordering",
            self._route_back_to_router,
            {
                "router_agent": "router_agent",
                "completion": "completion",
                "human_intervention": "human_intervention"
            }
        )
        
        workflow.add_conditional_edges(
            "upselling",
            self._route_back_to_router,
            {
                "router_agent": "router_agent",
                "completion": "completion",
                "human_intervention": "human_intervention"
            }
        )
        
        workflow.add_conditional_edges(
            "finalizing",
            self._route_back_to_router,
            {
                "router_agent": "router_agent",
                "completion": "completion",
                "human_intervention": "human_intervention"
            }
        )
        
        workflow.add_conditional_edges(
            "delivery_method",
            self._route_back_to_router,
            {
                "router_agent": "router_agent",
                "completion": "completion",
                "human_intervention": "human_intervention"
            }
        )
        
        workflow.add_edge("completion", END)
        workflow.add_edge("human_intervention", END)
        
        return workflow.compile()
    
    def _router_agent_node(self, state: RestaurantState) -> RestaurantState:
        """Central Router Agent node - makes all routing decisions"""
        # Get the last user message if available
        last_message = ""
        if state.get("messages"):
            last_message = state["messages"][-1].content if hasattr(state["messages"][-1], 'content') else str(state["messages"][-1])
        
        # Use the coordinator's router to make decisions
        if hasattr(self.coordinator, 'router_agent'):
            conversation_context = {
                "current_order": state.get("current_order", {}),
                "conversation_stage": state.get("conversation_stage", "greeting"),
                "order_total": state.get("order_total", 0.0),
                "upsell_attempts": state.get("upsell_attempts", 0),
                "menu_displayed": state.get("menu_displayed", False)
            }
            
            # Get router decision
            route_decision = self.coordinator.router_agent.route_conversation(
                last_message, conversation_context
            )
            
            # Store router decision for transparency
            state["router_decision"] = {
                "target_agent": route_decision.agent,
                "confidence": route_decision.confidence,
                "user_intent": route_decision.user_intent,
                "extracted_items": route_decision.extracted_items,
                "needs_clarification": route_decision.needs_clarification
            }
            
            # Update state based on router analysis
            state["customer_intent"] = route_decision.user_intent
            state["last_agent"] = "router"
            
            # If items were extracted, update current order context
            if route_decision.extracted_items:
                state["current_order"] = {
                    "pending_items": route_decision.extracted_items,
                    "total": sum(item.get("price", 0) * item.get("quantity", 1) for item in route_decision.extracted_items)
                }
        
        return state
    
    def _menu_agent_node(self, state: RestaurantState) -> RestaurantState:
        """Menu Agent node - handles menu queries and recommendations"""
        state["last_agent"] = "menu"
        state["conversation_stage"] = "browsing"
        state["menu_displayed"] = True
        return state
    
    def _order_agent_node(self, state: RestaurantState) -> RestaurantState:
        """Order Agent node - processes orders and item extraction"""
        state["last_agent"] = "order"
        state["conversation_stage"] = "ordering"
        
        # Update order information from router's extracted items
        if state.get("router_decision", {}).get("extracted_items"):
            extracted_items = state["router_decision"]["extracted_items"]
            total = sum(item.get("price", 0) * item.get("quantity", 1) for item in extracted_items)
            state["order_total"] = state.get("order_total", 0) + total
            
            # Update current order
            current_items = state.get("current_order", {}).get("items", [])
            current_items.extend(extracted_items)
            state["current_order"] = {
                "items": current_items,
                "total": state["order_total"]
            }
        
        return state
    
    def _upselling_agent_node(self, state: RestaurantState) -> RestaurantState:
        """Upselling Agent node - suggests complementary items"""
        state["last_agent"] = "upselling"
        state["conversation_stage"] = "upselling"
        state["upsell_attempts"] = state.get("upsell_attempts", 0) + 1
        return state
    
    def _finalization_agent_node(self, state: RestaurantState) -> RestaurantState:
        """Finalization Agent node - handles order completion"""
        state["last_agent"] = "finalization"
        state["conversation_stage"] = "finalizing"
        return state
    
    def _delivery_agent_node(self, state: RestaurantState) -> RestaurantState:
        """Delivery Agent node - handles delivery method selection"""
        state["last_agent"] = "delivery"
        state["conversation_stage"] = "awaiting_delivery"
        
        # Check if router detected delivery method
        router_decision = state.get("router_decision", {})
        if router_decision.get("delivery_method"):
            state["delivery_method"] = router_decision["delivery_method"]
        
        return state

    # Conversation flow nodes
    def _greeting_node(self, state: RestaurantState) -> RestaurantState:
        """Handle initial greeting stage"""
        state["conversation_stage"] = "greeting"
        return state
    
    def _menu_browsing_node(self, state: RestaurantState) -> RestaurantState:
        """Handle menu browsing stage"""
        state["conversation_stage"] = "browsing"
        state["menu_displayed"] = True
        return state
    
    def _ordering_node(self, state: RestaurantState) -> RestaurantState:
        """Handle ordering stage"""
        state["conversation_stage"] = "ordering"
        return state
    
    def _upselling_node(self, state: RestaurantState) -> RestaurantState:
        """Handle upselling stage"""
        state["conversation_stage"] = "upselling"
        return state
    
    def _finalizing_node(self, state: RestaurantState) -> RestaurantState:
        """Handle order finalization stage"""
        state["conversation_stage"] = "finalizing"
        return state
    
    def _delivery_method_node(self, state: RestaurantState) -> RestaurantState:
        """Handle delivery method selection stage"""
        state["conversation_stage"] = "awaiting_delivery"
        return state
    
    def _completion_node(self, state: RestaurantState) -> RestaurantState:
        """Handle order completion"""
        state["conversation_stage"] = "completed"
        state["customer_intent"] = "COMPLETED"
        state["last_agent"] = "completion"
        return state
    
    def _human_intervention_node(self, state: RestaurantState) -> RestaurantState:
        """Handle human intervention cases"""
        state["conversation_stage"] = "human_intervention"
        state["customer_intent"] = "HUMAN_NEEDED"
        state["last_agent"] = "human"
        state["needs_intervention"] = True
        return state
    
    def _route_from_router(self, state: RestaurantState) -> str:
        """Route from Router Agent based on its decision"""
        router_decision = state.get("router_decision", {})
        target_agent = router_decision.get("target_agent", "menu")
        
        # Map router agent decisions to graph nodes
        agent_mapping = {
            "menu": "menu_agent",
            "order": "order_agent",
            "upselling": "upselling_agent",
            "finalization": "finalization_agent",
            "delivery": "delivery_agent",
            "human": "human_intervention"
        }
        
        # Special case for initial greeting
        if state.get("conversation_stage") == "start" or not state.get("conversation_stage"):
            return "greeting"
        
        return agent_mapping.get(target_agent, "menu_agent")
    
    def _route_back_to_router(self, state: RestaurantState) -> str:
        """Route back to router unless conversation is complete"""
        # Check for completion conditions
        if (state.get("conversation_stage") == "completed" or
            state.get("customer_intent") == "COMPLETED" or
            state.get("order_total", 0) > 0 and state.get("delivery_method")):
            return "completion"
        
        # Check for human intervention
        if (state.get("needs_intervention") or
            state.get("customer_intent") == "HUMAN_NEEDED"):
            return "human_intervention"
        
        # Continue conversation through router
        return "router_agent"
    
    def _needs_human_intervention(self, state: RestaurantState) -> bool:
        """Check if human intervention is needed"""
        if hasattr(self.coordinator, 'shared_memory'):
            return self.coordinator.shared_memory.needs_human_intervention
        return state.get("needs_intervention", False)
    
    def process_conversation(self, user_input: str, current_state: RestaurantState = None) -> tuple[str, RestaurantState]:
        """Process a conversation turn through the updated Router-centric graph"""
        if current_state is None:
            current_state = {
                "messages": [],
                "current_order": {},
                "conversation_stage": "start",
                "customer_info": {},
                "order_total": 0.0,
                "upsell_attempts": 0,
                "menu_displayed": False,
                "customer_intent": "GREETING",
                "last_agent": "router",
                "needs_intervention": False,
                "router_decision": {}
            }
        
        # Process through the new coordinator
        response, coordinator_state = self.coordinator.process_user_input(user_input)
        
        # Update state with coordinator's shared memory
        if hasattr(self.coordinator, 'shared_memory'):
            shared_memory = self.coordinator.shared_memory
            current_state.update({
                "conversation_stage": shared_memory.conversation_stage,
                "customer_intent": shared_memory.customer_intent,
                "order_total": shared_memory.order_total,
                "upsell_attempts": shared_memory.upsell_attempts,
                "menu_displayed": shared_memory.menu_displayed,
                "last_agent": shared_memory.last_agent,
                "needs_intervention": shared_memory.needs_human_intervention
            })
            
            # Update current order
            if shared_memory.current_order:
                current_state["current_order"] = {
                    "items": [
                        {
                            "name": item.get("name", ""),
                            "price": item.get("price", 0),
                            "quantity": item.get("quantity", 1),
                            "customizations": item.get("customizations", [])
                        }
                        for item in shared_memory.current_order
                    ],
                    "total": shared_memory.order_total
                }
        
        return response, current_state