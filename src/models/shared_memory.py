from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

@dataclass
class SharedMemory:
    """Central shared memory for all agents to maintain conversation state"""
    
    # Customer Intent and State
    customer_intent: str = "GREETING"  # GREETING, BROWSING, ORDERING, FINALIZING, DELIVERY_METHOD, COMPLETED
    conversation_stage: str = "greeting"  # greeting, browsing, ordering, finalizing, awaiting_delivery, completed
    needs_human_intervention: bool = False
    intervention_reason: str = ""
    
    # Order Information
    current_order: List[Dict[str, Any]] = field(default_factory=list)
    order_status: str = "IN_PROGRESS"  # IN_PROGRESS, COMPLETE, CONFIRMED
    order_total: float = 0.0
    order_id: str = ""
    
    # Customer Information
    customer_name: str = ""
    delivery_details: Dict[str, str] = field(default_factory=dict)
    customer_preferences: Dict[str, Any] = field(default_factory=dict)
    delivery_method: str = ""  # "delivery" or "pickup"
    
    # Conversation Context
    last_agent: str = ""
    last_action: str = ""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    pending_clarifications: List[str] = field(default_factory=list)
    
    # Upselling and Recommendations
    upsell_attempts: int = 0
    max_upsell_attempts: int = 2
    suggested_items: List[str] = field(default_factory=list)
    declined_suggestions: List[str] = field(default_factory=list)
    
    # Menu Context
    menu_displayed: bool = False
    current_category: str = ""
    browsing_preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Error Handling
    error_count: int = 0
    last_error: str = ""
    fallback_mode: bool = False
    
    # Timestamps
    session_start: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def add_to_history(self, user_input: str, agent_response: str, agent_name: str):
        """Add interaction to conversation history"""
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "agent_response": agent_response,
            "agent": agent_name
        })
        self.last_activity = datetime.now()
        self.last_agent = agent_name
    
    def add_order_item(self, item: Dict[str, Any]):
        """Add item to current order"""
        # Check if item already exists
        for existing_item in self.current_order:
            if (existing_item.get("name") == item.get("name") and 
                existing_item.get("customizations") == item.get("customizations", [])):
                existing_item["quantity"] = existing_item.get("quantity", 1) + item.get("quantity", 1)
                return
        
        self.current_order.append(item)
        self._update_order_total()
    
    def remove_order_item(self, item_name: str) -> bool:
        """Remove item from order"""
        for i, item in enumerate(self.current_order):
            if item.get("name", "").lower() == item_name.lower():
                del self.current_order[i]
                self._update_order_total()
                return True
        return False
    
    def clear_order(self):
        """Clear all order items"""
        self.current_order.clear()
        self.order_total = 0.0
        self.order_status = "IN_PROGRESS"
    
    def _update_order_total(self):
        """Update total order price"""
        total = 0.0
        for item in self.current_order:
            quantity = item.get("quantity", 1)
            price = item.get("price", 0.0)
            total += quantity * price
        
        # Add tax (8%)
        self.order_total = total * 1.08
    
    def set_customer_intent(self, intent: str, reason: str = ""):
        """Update customer intent with reason"""
        self.customer_intent = intent
        self.last_action = f"Intent changed to {intent}: {reason}"
    
    def trigger_human_intervention(self, reason: str):
        """Trigger human operator intervention"""
        self.needs_human_intervention = True
        self.intervention_reason = reason
        self.last_action = f"Human intervention requested: {reason}"
    
    def resolve_human_intervention(self):
        """Clear human intervention flag"""
        self.needs_human_intervention = False
        self.intervention_reason = ""
        self.last_action = "Human intervention resolved"
    
    def increment_error(self, error_message: str):
        """Track errors for potential escalation"""
        self.error_count += 1
        self.last_error = error_message
        
        # Auto-trigger human intervention after 3 errors
        if self.error_count >= 3:
            self.trigger_human_intervention(f"Multiple errors occurred: {error_message}")
    
    def is_order_ready_for_completion(self) -> bool:
        """Check if order can be completed"""
        return (len(self.current_order) > 0 and 
                self.customer_intent in ["FINALIZING", "COMPLETED"] and
                not self.needs_human_intervention)
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context for agents"""
        return {
            "customer_intent": self.customer_intent,
            "conversation_stage": self.conversation_stage,
            "current_order": self.current_order,
            "order_total": self.order_total,
            "order_status": self.order_status,
            "customer_name": self.customer_name,
            "last_agent": self.last_agent,
            "upsell_attempts": self.upsell_attempts,
            "needs_clarification": len(self.pending_clarifications) > 0,
            "menu_displayed": self.menu_displayed,
            "error_count": self.error_count,
            "needs_human_intervention": self.needs_human_intervention
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "customer_intent": self.customer_intent,
            "conversation_stage": self.conversation_stage,
            "current_order": self.current_order,
            "order_total": self.order_total,
            "order_status": self.order_status,
            "customer_name": self.customer_name,
            "delivery_details": self.delivery_details,
            "conversation_history": self.conversation_history[-10:],  # Last 10 interactions
            "upsell_attempts": self.upsell_attempts,
            "menu_displayed": self.menu_displayed,
            "session_duration": (self.last_activity - self.session_start).total_seconds()
        }
    
    def __str__(self) -> str:
        """String representation for debugging"""
        return f"""
SharedMemory Status:
- Intent: {self.customer_intent}
- Stage: {self.conversation_stage}
- Order Items: {len(self.current_order)}
- Order Total: ${self.order_total:.2f}
- Last Agent: {self.last_agent}
- Needs Intervention: {self.needs_human_intervention}
- Error Count: {self.error_count}
"""