class UpsellingNode:
    def __init__(self, upselling_agent):
        self.upselling_agent = upselling_agent

    def present_upsell_options(self, selected_items):
        upsell_options = self.upselling_agent.suggest_upsell(selected_items)
        if upsell_options:
            return f"Based on your selection, you might also like: {', '.join(upsell_options)}. Would you like to add any of these to your order?"
        return "No upsell options available at this time."

    def handle_upsell_decision(self, user_response):
        if user_response.lower() in ['yes', 'sure', 'okay']:
            return "Great! What would you like to add?"
        elif user_response.lower() in ['no', 'not now']:
            return "No problem! Let's proceed with your order."
        else:
            return "I didn't quite catch that. Could you please respond with 'yes' or 'no'?"