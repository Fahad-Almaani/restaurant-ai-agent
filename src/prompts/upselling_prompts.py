class UpsellingPrompts:
    @staticmethod
    def suggest_upsell_prompt(selected_item):
        return f"Would you like to add a drink or dessert to your order of {selected_item}?"

    @staticmethod
    def upsell_confirmation_prompt(item):
        return f"You've chosen to add {item}. Is that correct?"

    @staticmethod
    def upsell_decline_prompt():
        return "No problem! Let me know if you change your mind."


UPSELLING_AGENT_PROMPT = """
You are a skilled upselling agent for AI Bistro. Your role is to enhance the customer's dining experience by suggesting complementary items that add value to their order.

Current Order: {current_order}
Available Upsells: {available_upsells}
Customer Response: {customer_input}

Guidelines:
1. Make suggestions that genuinely complement the customer's order
2. Be persuasive but not pushy
3. Highlight the value and benefits of additional items
4. Respect the customer's budget and preferences
5. Use enticing descriptions that make items sound irresistible
6. Offer alternatives if the first suggestion is declined
7. Always be gracious if the customer declines

Your goal is to increase order value while enhancing customer satisfaction.
"""

UPSELLING_SUGGESTIONS = {
    "appetizer_with_main": "Since you're ordering {main_dish}, would you like to start with our popular {appetizer}? It pairs perfectly and will enhance your dining experience!",

    "drink_with_meal": "To complement your {meal}, may I suggest our {drink}? It's specifically chosen to bring out the flavors in your dish.",

    "dessert_suggestion": "For the perfect ending to your meal, our {dessert} is a customer favorite and would be the ideal sweet finish!",

    "side_upgrade": "Would you like to upgrade your side to our premium {premium_side}? It's only ${extra_cost} more and really completes the dish.",

    "combo_deal": "I can offer you our {combo_name} which includes {items} for just ${combo_price} - that's a ${savings} savings compared to ordering separately!"
}

UPSELLING_RESPONSES = {
    "accepted": "Excellent choice! I've added {item} to your order. Anything else I can get for you?",

    "declined_politely": "No problem at all! Your current order of {current_order} will be delicious. Is there anything else you'd like?",

    "alternative_offer": "I understand. How about our {alternative} instead? It's {alternative_description} and only ${alternative_price}.",

    "budget_conscious": "I completely understand. Your current selection is already fantastic and will make for a wonderful meal!"
}


def get_upselling_prompt(order_context: str, upsell_type: str) -> str:
    """Generate context-specific upselling prompts"""
    base_prompt = UPSELLING_AGENT_PROMPT

    if upsell_type in UPSELLING_SUGGESTIONS:
        return base_prompt + "\n\nSuggestion Template: " + UPSELLING_SUGGESTIONS[upsell_type]

    return base_prompt