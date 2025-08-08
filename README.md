# 🍽️ AI Restaurant Agent

A sophisticated AI-powered restaurant ordering system built with LangChain, LangGraph, and Google's Gemini AI. This system provides an intelligent conversational interface for customers to browse menus, place orders, customize items, and receive personalized upselling suggestions.

## 🌟 Features

- **Intelligent Menu Display**: AI-powered menu browsing with detailed descriptions and recommendations
- **Order Management**: Take orders with customizations and modifications
- **Smart Upselling**: Context-aware suggestions to enhance the dining experience
- **Conversation Flow**: Structured conversation management using LangGraph
- **Multiple Agents**: Specialized agents for different tasks (Menu, Order, Upselling, Coordination)
- **Professional Architecture**: Clean, modular code with separate concerns
- **Real-time Interaction**: Interactive command-line interface

## 🏗️ Architecture

The system is built with a modular architecture featuring:

### Core Components

- **Coordinator Agent**: Manages conversation flow and routes requests
- **Menu Agent**: Handles menu display and item queries
- **Order Agent**: Processes orders and customizations
- **Upselling Agent**: Provides intelligent upselling suggestions

### LangGraph Workflow

- Structured conversation nodes for different states
- Conditional routing based on user intent
- State management throughout the conversation

### Data Models

- Order and OrderItem models with comprehensive functionality
- Menu models with dietary restrictions and categories
- Validation tools for input sanitization

## 📁 Project Structure

```
restaurant-ai-agent/
├── src/
│   ├── agents/
│   │   ├── coordinator_agent.py    # Main conversation coordinator
│   │   ├── menu_agent.py          # Menu display and queries
│   │   ├── order_agent.py         # Order processing
│   │   └── upselling_agent.py     # Upselling suggestions
│   ├── models/
│   │   ├── order_models.py        # Order and OrderItem classes
│   │   └── menu_models.py         # Menu data models
│   ├── tools/
│   │   ├── menu_tools.py          # Menu operations
│   │   ├── order_tools.py         # Order validation and formatting
│   │   └── validation_tools.py    # Input validation utilities
│   ├── prompts/
│   │   ├── menu_agent_prompts.py  # Menu agent system prompts
│   │   ├── order_agent_prompts.py # Order agent system prompts
│   │   └── upselling_prompts.py   # Upselling agent prompts
│   ├── data/
│   │   ├── menu.json             # Restaurant menu data
│   │   └── upselling_rules.json  # Upselling rules and suggestions
│   ├── graph/
│   │   └── restaurant_graph.py    # LangGraph workflow definition
│   └── main.py                    # Main application entry point
├── config.py                      # Configuration settings
├── requirements.txt               # Python dependencies
├── .env.example                  # Environment variables example
└── README.md                     # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google API Key for Gemini

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd restaurant-ai-agent
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env and add your Google API key
   ```

4. **Run the application**
   ```bash
   cd src
   python main.py
   ```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

### Menu Customization

Edit `src/data/menu.json` to customize the restaurant menu with your items, prices, and descriptions.

### Upselling Rules

Modify `src/data/upselling_rules.json` to adjust upselling suggestions and combo deals.

## 💬 Usage Examples

### Basic Conversation Flow

1. **Welcome & Menu Display**

   ```
   Customer: "Hi, I'd like to see your menu"
   AI: [Displays formatted menu with categories]
   ```

2. **Order Placement**

   ```
   Customer: "I'll have a burger and fries"
   AI: [Processes order, confirms items]
   ```

3. **Upselling**

   ```
   AI: "Would you like to add a drink to complete your meal?"
   Customer: "Yes, I'll take a Coke"
   ```

4. **Order Confirmation**
   ```
   AI: [Shows final order with total]
   Customer: "That's all"
   AI: [Confirms order completion]
   ```

## 🤖 AI Agents Details

### Menu Agent

- Displays categorized menu with prices and descriptions
- Handles dietary restriction filtering
- Provides detailed item information
- Suggests popular items and chef recommendations

### Order Agent

- Processes natural language order requests
- Handles quantity specifications
- Manages order modifications
- Validates orders against menu availability

### Upselling Agent

- Context-aware suggestions based on current order
- Combo deal recommendations
- Dietary-specific upsells
- Graceful handling of customer responses

### Coordinator Agent

- Intent recognition and routing
- Conversation state management
- Agent orchestration
- Error handling and fallbacks

## 🔄 Conversation States

The system manages conversation through these states:

- **Greeting**: Initial welcome and introduction
- **Menu Browsing**: Menu display and item queries
- **Ordering**: Order placement and modifications
- **Upselling**: Suggestion and additional item offers
- **Confirming**: Final order review and confirmation
- **Completed**: Order finalization

## 🛠️ Development

### Adding New Menu Items

1. Update `src/data/menu.json` with new items
2. Follow the existing JSON structure
3. Include all required fields (name, price, description, category)

### Extending Functionality

1. Create new agent classes inheriting from base patterns
2. Add corresponding tools in the `tools/` directory
3. Update the coordinator routing logic
4. Add new prompts in the `prompts/` directory

### Custom Prompts

Modify prompt templates in the `prompts/` directory to customize AI behavior and responses.

## 📊 Features in Detail

### Order Management

- Real-time order tracking
- Automatic price calculation with tax
- Order modification support
- Comprehensive order validation

### Menu System

- Hierarchical categorization
- Dietary restriction support
- Popular item highlighting
- Chef recommendation system

### Upselling Intelligence

- Rule-based suggestions
- Order value optimization
- Customer preference learning
- Respectful decline handling

## 🔮 Future Enhancements

- Web interface integration
- Database persistence
- Payment processing integration
- Multi-language support
- Voice interface capabilities
- Analytics and reporting
- Customer preference learning
- Integration with POS systems

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support, please open an issue in the GitHub repository or contact the development team.

## 🙏 Acknowledgments

- Built with LangChain and LangGraph
- Powered by Google's Gemini AI
- Inspired by modern restaurant technology solutions
