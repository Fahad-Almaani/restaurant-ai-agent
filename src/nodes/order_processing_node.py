class OrderProcessingNode:
    def __init__(self, order_agent, validation_tools):
        self.order_agent = order_agent
        self.validation_tools = validation_tools

    def validate_order(self, order):
        if self.validation_tools.is_valid_order(order):
            return True
        return False

    def finalize_order(self, order):
        if self.validate_order(order):
            confirmation = self.order_agent.confirm_order(order)
            return confirmation
        else:
            raise ValueError("Invalid order. Please check your selections.")