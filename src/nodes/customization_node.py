class CustomizationNode:
    def __init__(self):
        self.customizations = {}

    def customize_order(self, order_details):
        # Logic to customize the order based on user input
        print("Customizing your order...")
        # Example customization logic
        self.customizations['spice_level'] = input("Choose spice level (mild, medium, hot): ")
        self.customizations['extra_toppings'] = input("Add extra toppings (yes/no): ")
        if self.customizations['extra_toppings'].lower() == 'yes':
            self.customizations['toppings'] = input("List your toppings: ")
        return self.customizations

    def apply_customizations(self, order):
        # Logic to apply customizations to the order
        print("Applying customizations...")
        order.update(self.customizations)
        return order