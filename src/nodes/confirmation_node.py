class ConfirmationNode:
    def __init__(self, order_details):
        self.order_details = order_details

    def confirm_order_details(self):
        confirmation_message = f"Please confirm your order: {self.order_details}"
        return confirmation_message

    def send_confirmation(self):
        confirmation_message = self.confirm_order_details()
        # Logic to send confirmation to the customer (e.g., via chat or notification)
        print(confirmation_message)
        return "Order confirmed!"