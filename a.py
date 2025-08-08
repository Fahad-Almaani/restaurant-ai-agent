from IPython.display import Image, display
# from restaurant_order_agent import create_restaurant_workflow
from src.main import RestaurantAIAgent
graph_instance = RestaurantAIAgent()

try:
    display(Image(graph_instance.graph.get_graph().draw_mermaid_png()))
    
except: 
    pass