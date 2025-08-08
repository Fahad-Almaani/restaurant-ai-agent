class MenuDisplayNode:
    def __init__(self, menu_agent):
        self.menu_agent = menu_agent

    def render_menu(self):
        menu = self.menu_agent.display_menu()
        print("Here is the menu:")
        for item in menu:
            print(f"{item['name']}: ${item['price']}")

    def handle_user_input(self, user_input):
        selection = self.menu_agent.get_menu_selection(user_input)
        if selection:
            print(f"You have selected: {selection['name']}")
            return selection
        else:
            print("Invalid selection. Please try again.")
            return None