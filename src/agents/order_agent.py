from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from tools.order_tools import (
    validate_order, format_order_details, parse_order_input, 
    format_order_confirmation, find_menu_matches
)
from tools.menu_tools import get_menu_item_by_name, load_menu_from_file
from models.order_models import Order, OrderItem
from models.shared_memory import SharedMemory
from prompts.order_agent_prompts import ORDER_AGENT_PROMPT
import os
import json
import re

class OrderProcessingResult(BaseModel):
    """Structured result for order processing"""
    success: bool = Field(description="Whether the order was processed successfully")
    added_items: List[Dict[str, Any]] = Field(default_factory=list, description="Items successfully added")
    failed_items: List[Dict[str, Any]] = Field(default_factory=list, description="Items that couldn't be processed")
    message: str = Field(description="Response message to user")
    requires_clarification: bool = Field(default=False, description="Whether clarification is needed")
    clarification_options: List[str] = Field(default_factory=list, description="Options for clarification")

class OrderAgent:
    def __init__(self, llm, shared_memory: SharedMemory):
        self.llm = llm
        self.shared_memory = shared_memory
        self.menu = self._load_menu()
        
        # Set up structured output parser
        self.result_parser = PydanticOutputParser(pydantic_object=OrderProcessingResult)
        
        # Enhanced prompt for intelligent order processing
        self.order_prompt = PromptTemplate(
            input_variables=["customer_input", "extracted_items", "current_order", "menu_context"],
            partial_variables={"format_instructions": self.result_parser.get_format_instructions()},
            template="""
You are an expert Order Processing Agent for a restaurant AI system.

Available Menu:
{menu_context}

Current Order in Memory:
{current_order}

Customer Input: "{customer_input}"

Pre-extracted Items from Router:
{extracted_items}

Your task is to intelligently process the order request:

1. **Validate Extracted Items**: Check if the extracted items match our menu
2. **Handle Ambiguity**: If items are unclear, provide clarification options
3. **Process Quantities**: Handle multiple quantities correctly
4. **Apply Customizations**: Process any mentioned customizations
5. **Update Order**: Add items to the order with correct pricing
6. **Generate Response**: Create a helpful, conversational response

For each item:
- Validate it exists on our menu
- Get correct pricing
- Handle quantity properly (default to 1 if not specified)
- Process customizations like "no onions", "extra cheese"
- Provide alternatives if item not found

Special Intelligence Required:
- "coc" or "coca" → "Coca Cola"
- "burger" → "Classic Burger" 
- "pizza" → "Margherita Pizza"
- "wings" → "Buffalo Wings"
- Handle plurals: "2 burgers" = 2x Classic Burger

{format_instructions}

Provide a structured response that's both informative and conversational.
"""
        )
        
        # Replace deprecated LLMChain with Runnable pipeline
        self.order_chain = self.order_prompt | self.llm | self.result_parser

    def _load_menu(self):
        """Load menu data for price lookup"""
        menu_file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'menu.json')
        return load_menu_from_file(menu_file_path)

    def _format_menu_for_context(self):
        """Format menu for AI context"""
        menu_items = []
        # Handle menu as a list of items (not a dict)
        if isinstance(self.menu, list):
            for item in self.menu:
                menu_items.append(f"- {item['name']}: ${item['price']:.2f} - {item['description']}")
        else:
            # Fallback for dict format
            for category, items in self.menu.items():
                for item in items:
                    menu_items.append(f"- {item['name']}: ${item['price']:.2f} - {item['description']}")
        return "\n".join(menu_items)

    def _normalize_order_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize an order item dict to ensure required fields are present.
        Ensures we always have: name, quantity, price, customizations.
        If price is missing, try to look it up from the menu.
        """
        # Determine name from possible keys
        name = (
            item.get("name") or
            item.get("item_name") or
            item.get("menu_name") or
            item.get("title") or
            item.get("product") or
            ""
        )
        name = str(name).strip()
        if not name:
            return None
        
        # Quantity
        quantity = item.get("quantity", 1)
        try:
            quantity = int(quantity)
        except Exception:
            quantity = 1
        if quantity <= 0:
            quantity = 1
        
        # Try to get a matching menu item for canonical name/price
        menu_item = self._find_best_menu_match(name)
        canonical_name = menu_item["name"] if menu_item else name
        
        # Price
        price = item.get("price")
        try:
            price = float(price) if price is not None else None
        except Exception:
            price = None
        if price is None or price <= 0:
            price = float(menu_item.get("price", 0.0)) if menu_item else 0.0
        
        # Customizations
        customizations = item.get("customizations") or item.get("mods") or item.get("notes") or []
        if isinstance(customizations, str):
            customizations = [customizations]
        if not isinstance(customizations, list):
            try:
                customizations = list(customizations)
            except Exception:
                customizations = []
        customizations = [str(c).strip() for c in customizations if str(c).strip()]
        
        return {
            "name": canonical_name,
            "quantity": quantity,
            "price": price,
            "customizations": customizations,
        }

    def process_order_with_extracted_items(self, customer_input: str, extracted_items: List[Dict[str, Any]]) -> OrderProcessingResult:
        """
        Main order processing function that uses pre-extracted items from Router Agent
        """
        try:
            # Prepare context
            menu_context = self._format_menu_for_context()
            current_order_str = json.dumps(self.shared_memory.current_order, indent=2)
            extracted_items_str = json.dumps(extracted_items, indent=2)
            
            # Process through AI
            result: OrderProcessingResult = self.order_chain.invoke({
                "customer_input": customer_input,
                "extracted_items": extracted_items_str,
                "current_order": current_order_str,
                "menu_context": menu_context
            })
            
            # Normalize and update shared memory with successful items
            normalized_added: List[Dict[str, Any]] = []
            for raw_item in result.added_items:
                normalized = self._normalize_order_item(raw_item)
                if normalized:
                    self.shared_memory.add_order_item(normalized)
                    normalized_added.append(normalized)
            
            # Replace added_items with normalized ones so downstream has consistent structure
            try:
                result.added_items = normalized_added
            except Exception:
                pass
            
            # Update conversation state
            if normalized_added:
                self.shared_memory.set_customer_intent("ORDERING", "Items added to order")
            
            return result
            
        except Exception as e:
            if os.getenv("DEBUG_MODE", "false").lower() == "true":
                print(f"Order processing error: {e}")
            return self._fallback_order_processing(customer_input, extracted_items)

    def _fallback_order_processing(self, customer_input: str, extracted_items: List[Dict[str, Any]]) -> OrderProcessingResult:
        """Fallback order processing when AI fails"""
        added_items = []
        failed_items = []
        
        for item_data in extracted_items:
            item_name = item_data.get("item_name", "")
            quantity = item_data.get("quantity", 1)
            confidence = item_data.get("confidence", 0.5)
            
        
            # Try to find menu match
            menu_item = self._find_best_menu_match(item_name)
            
            if menu_item and confidence > 0.6:
                order_item = {
                    "name": menu_item["name"],
                    "quantity": quantity,
                    "price": menu_item["price"],
                    "customizations": item_data.get("customizations", []),
                    "total": menu_item["price"] * quantity
                }
                added_items.append(order_item)
                self.shared_memory.add_order_item(order_item)
            else:
                failed_items.append({
                    "requested_name": item_name,
                    "alternatives": item_data.get("alternatives", [])
                })
        
        # Generate response message
        if added_items and not failed_items:
            message = f"Great! I've added {len(added_items)} item(s) to your order."
        elif added_items and failed_items:
            message = f"I've added {len(added_items)} item(s) to your order, but couldn't find {len(failed_items)} item(s)."
        else:
            message = "I couldn't find any of those items on our menu. Would you like to see our menu?"
        
        return OrderProcessingResult(
            success=len(added_items) > 0,
            added_items=added_items,
            failed_items=failed_items,
            message=message,
            requires_clarification=len(failed_items) > 0
        )

    def _find_best_menu_match(self, item_name: str) -> Optional[Dict[str, Any]]:
        """Find best matching menu item"""
        item_name_lower = item_name.lower()
        
        # Handle menu as a list of items (not a dict)
        menu_items = self.menu if isinstance(self.menu, list) else []
        if not menu_items and isinstance(self.menu, dict):
            # Flatten dict format
            for category, items in self.menu.items():
                if isinstance(items, list):
                    menu_items.extend(items)
        
        # Direct matches first
        for item in menu_items:
            if item["name"].lower() == item_name_lower:
                return item
        
        # Partial matches
        for item in menu_items:
            if item_name_lower in item["name"].lower() or item["name"].lower() in item_name_lower:
                return item
        
        # Special intelligent matches
        intelligent_matches = {
            "coc": "Coca Cola",
            "coca": "Coca Cola", 
            "burger": "Classic Burger",
            "pizza": "Margherita Pizza",
            "wings": "Buffalo Wings",
            "pasta": "Pasta Carbonara",
            "salmon": "Grilled Salmon",
            "salad": "Caesar Salad",
            "cheesecake": "New York Cheesecake",
            "ice cream": "Vanilla Ice Cream"
        }
        
        for key, menu_name in intelligent_matches.items():
            if key in item_name_lower:
                # Find this item in menu
                for item in menu_items:
                    if item["name"] == menu_name:
                        return item
        
        return None

    def handle_order_modification(self, customer_input: str) -> str:
        """Handle order modifications like removing or changing quantities.
        This function now applies changes to shared memory before generating a response.
        """
        # Disallow edits once order is completed/confirmed
        if self.shared_memory.conversation_stage == "completed" or self.shared_memory.order_status in ("COMPLETE", "CONFIRMED"):
            return "The order has already been completed and can no longer be modified."

        # Lightweight deterministic parsing for removals and quantity changes
        original_items = json.dumps(self.shared_memory.current_order, sort_keys=True)
        original_total = self.shared_memory.order_total
        text = customer_input.strip().lower()

        # Cancel entire order
        if any(kw in text for kw in ["cancel my order", "cancel order", "cancel it", "forget my order", "abort order", "nevermind, cancel"]):
            self.shared_memory.clear_order()
            return "Your order has been cancelled. Would you like to start a new order?"

        # Helper: find item in current order by best match
        def find_order_item_by_text(name_text: str) -> Optional[Dict[str, Any]]:
            # Try to map to canonical menu item name first
            menu_item = self._find_best_menu_match(name_text)
            target_name = menu_item["name"] if menu_item else name_text.strip()
            # Exact name match
            for it in self.shared_memory.current_order:
                if it.get("name", "").lower() == target_name.lower():
                    return it
            # Fallback: partial contains
            for it in self.shared_memory.current_order:
                if target_name.lower() in it.get("name", "").lower() or it.get("name", "").lower() in target_name.lower():
                    return it
            return None

        modified = False
        changes: List[str] = []

        # Patterns for removal like: remove 1 burger, remove the burger, delete salad, take off 2 cokes
        removal_patterns = [
            r"(?:remove|delete|take off|drop)\s+(?:the\s+)?(?:(\d+)\s+)?([a-zA-Z][a-zA-Z\s]+)"
        ]
        for pat in removal_patterns:
            for qty_str, item_txt in re.findall(pat, text):
                qty = int(qty_str) if qty_str.isdigit() else None
                item = find_order_item_by_text(item_txt)
                if item:
                    if qty is None or qty >= item.get("quantity", 1):
                        # Remove entire line
                        self.shared_memory.current_order.remove(item)
                        changes.append(f"removed {item.get('name')}")
                    else:
                        item["quantity"] = item.get("quantity", 1) - qty
                        changes.append(f"reduced {item.get('name')} by {qty}")
                    modified = True
        
        # Pattern for quantity set: make that 2 burgers, change burger to 3
        qty_set_patterns = [
            r"(?:make that|change|set)\s+(?:it|that|the\s+)?(?:(\d+)\s+)?([a-zA-Z][a-zA-Z\s]+?)s?(?:\b|$)",
            r"(?:change|set)\s+([a-zA-Z][a-zA-Z\s]+?)\s+(?:to\s+)?(\d+)"
        ]
        for pat in qty_set_patterns:
            for m in re.finditer(pat, text):
                g1 = m.group(1)
                g2 = m.group(2) if m.lastindex and m.lastindex >= 2 else None
                if g2 and g1 and g1.isalpha():
                    # pattern variant where order is (item, qty)
                    item_txt, qty_str = g1, g2
                else:
                    qty_str = g1 if g1 and g1.isdigit() else g2
                    item_txt = g2 if g2 and not g2.isdigit() else g1
                if not qty_str or not item_txt:
                    continue
                try:
                    new_qty = int(qty_str)
                except:
                    continue
                if new_qty <= 0:
                    new_qty = 0
                item = find_order_item_by_text(item_txt)
                if item:
                    if new_qty == 0:
                        self.shared_memory.current_order.remove(item)
                        changes.append(f"removed {item.get('name')}")
                    else:
                        item["quantity"] = new_qty
                        changes.append(f"set {item.get('name')} to {new_qty}")
                    modified = True
        
        # If user says things like "no salad" and that exact item is in order, treat as removal
        if not modified:
            m = re.findall(r"\bno\s+([a-zA-Z][a-zA-Z\s]+)\b", text)
            for item_txt in m:
                item = find_order_item_by_text(item_txt)
                if item:
                    self.shared_memory.current_order.remove(item)
                    changes.append(f"removed {item.get('name')}")
                    modified = True
        
        # Update totals if changed
        if modified:
            # Remove any lines with non-positive quantity
            self.shared_memory.current_order = [
                it for it in self.shared_memory.current_order if it.get("quantity", 0) > 0
            ]
            self.shared_memory._update_order_total()
            
            # Build an updated summary
            summary = self.get_order_summary()
            parts = [
                "✅ I've updated your order:",
                ""
            ]
            for item_data in summary['items']:
                q = item_data['quantity']
                name = item_data['name']
                up = item_data['unit_price']
                tp = item_data['total_price']
                if q == 1:
                    parts.append(f"• {name} - ${up:.2f}")
                else:
                    parts.append(f"• {q}x {name} - ${up:.2f} each (${tp:.2f})")
            parts.extend([
                "",
                f"💰 New total: ${summary['totals']['total']:.2f}"
            ])
            if changes:
                parts.append("\nChanges: " + ", ".join(changes))
            return "\n".join(parts)
        
        # If nothing deterministically modified, fall back to LLM assistant response
        modification_prompt = PromptTemplate(
            input_variables=["customer_input", "current_order", "menu_context"],
            template="""
You are helping a customer modify their restaurant order.

Current Order:
{current_order}

Available Menu:
{menu_context}

Customer Request: "{customer_input}"

Understand what modification they want:
- Remove items: "remove the burger", "take off the pizza"
- Change quantities: "make that 2 burgers instead of 1"
- Add customizations: "add extra cheese to the pizza"
- Replace items: "change the burger to chicken"

Provide a clear response about what you've changed and show the updated order.
"""
        )
        
        try:
            chain = modification_prompt | self.llm | StrOutputParser()
            response_text = chain.invoke({
                "customer_input": customer_input,
                "current_order": json.dumps(self.shared_memory.current_order, indent=2),
                "menu_context": self._format_menu_for_context()
            })
            return response_text
        except:
            return "I'd be happy to help modify your order. Could you please tell me specifically what you'd like to change?"

    def get_order_summary(self) -> Dict[str, Any]:
        """Get comprehensive order summary from shared memory"""
        if not self.shared_memory.current_order:
            return {
                'status': 'empty',
                'message': 'Your order is currently empty.',
                'items': [],
                'totals': {
                    'subtotal': 0.0,
                    'tax': 0.0,
                    'total': 0.0
                }
            }
        
        # Calculate totals
        subtotal = sum(item.get("price", 0) * item.get("quantity", 1) for item in self.shared_memory.current_order)
        tax = subtotal * 0.08
        total = subtotal + tax
        
        return {
            'status': 'active',
            'message': 'Here is your current order:',
            'items': [
                {
                    'name': item.get("name", ""),
                    'quantity': item.get("quantity", 1),
                    'unit_price': item.get("price", 0),
                    'total_price': item.get("price", 0) * item.get("quantity", 1),
                    'customizations': item.get("customizations", [])
                }
                for item in self.shared_memory.current_order
            ],
            'totals': {
                'subtotal': subtotal,
                'tax': tax,
                'total': total
            }
        }

    def validate_order_completion(self) -> Dict[str, Any]:
        """Validate if order is ready for completion"""
        if not self.shared_memory.current_order:
            return {
                "ready": False,
                "message": "No items in order",
                "missing": ["items"]
            }
        
        missing = []
        if self.shared_memory.order_total <= 0:
            missing.append("valid pricing")
        
        return {
            "ready": len(missing) == 0,
            "message": "Order ready for completion" if len(missing) == 0 else f"Missing: {', '.join(missing)}",
            "missing": missing,
            "order_summary": self.get_order_summary()
        }