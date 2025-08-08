# Restaurant AI Agent 🤖🍽️

A sophisticated multi-agent conversational AI system for restaurant order management, built with LangChain and powered by Google's Gemini AI.

## Overview

This system implements a **router-centric architecture** with intelligent conversation flow management, featuring specialized agents for different aspects of the restaurant ordering process.

## 🏗️ System Architecture

### Core Components

**🤖 Router Agent (Central Hub)**

- Intelligent intent classification (GREETING, ORDERING, BROWSING, etc.)
- Smart item extraction from natural language
- Dynamic routing to specialized agents
- Automatic clarification requests for ambiguous inputs

**🎯 Specialized Agents**

- **🍽️ Menu Agent**: Menu queries, recommendations, item information
- **🛒 Order Agent**: Order processing with intelligent item extraction
- **💡 Upselling Agent**: Complementary item suggestions
- **✅ Finalization Agent**: Order completion and payment
- **🚚 Delivery Agent**: Delivery/pickup method selection

**💬 Conversation Flow**

```
START → Router Agent → Specialized Agents → Conversation Stages → Router Agent → END
```

### Project Structure

```
src/
├── config.py                 # Configuration settings
├── main.py                   # Main application entry point
├── agents/                   # Specialized AI agents
│   ├── router_agent.py       # Central routing logic
│   ├── menu_agent.py         # Menu handling
│   ├── order_agent.py        # Order processing
│   └── upselling_agent.py    # Upselling logic
├── graph/                    # Conversation flow graph
│   └── restaurant_graph.py   # Graph implementation
├── models/                   # Data models
│   ├── menu_models.py        # Menu data structures
│   ├── order_models.py       # Order data structures
│   └── shared_memory.py      # Shared state management
├── data/                     # Configuration data
│   ├── menu.json            # Restaurant menu
│   └── upselling_rules.json # Upselling rules
├── tools/                    # Utility functions
└── prompts/                  # AI prompts
```

## 🚀 Quick Start

### 1. Environment Setup

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

**Get your Google API Key:**

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy and paste it into your `.env` file

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python src/main.py
```

## ⚙️ Configuration

### Model Configuration

Edit `src/config.py` to customize the AI model:

```python
class Config:
    # AI Model Configuration
    MODEL_NAME = "gemma-3-27b-it"        # Available: gemma-3-27b-it, gemini-pro, etc.
    MODEL_TEMPERATURE = 0.7              # Creativity level (0.0-1.0)
    MAX_TOKENS = 1000                    # Response length limit

    # Application Settings
    MAX_ORDER_ITEMS = 5                  # Maximum items per order
    UPSELLING_THRESHOLD = 3              # Minimum items for upselling
    TIMEOUT_DURATION = 30                # User response timeout (seconds)
```

### Available Models

- `gemma-3-27b-it` (Default) - Balanced performance and speed
- `gemini-pro` - Advanced reasoning capabilities
- `gemini-pro-vision` - Multimodal support

## 🎯 Key Features

- **🧠 Intelligent Routing**: Context-aware conversation management
- **🍽️ Smart Ordering**: Natural language item extraction ("2 burgers and 3 cokes")
- **💡 Dynamic Upselling**: Context-based recommendations
- **🔄 Multi-turn Conversations**: Maintains conversation context
- **🆘 Human Intervention**: Automatic escalation for complex queries
- **📊 Order Analytics**: Comprehensive order tracking
- **🎨 Flexible Flow**: Adaptive conversation management

## 💡 Usage Examples

```python
from src.main import RestaurantAIAgent

# Initialize the agent
agent = RestaurantAIAgent()

# Start conversation
response = agent.chat("Hello! I'd like to see your menu")
print(response)

# Place an order
response = agent.chat("I want 2 burgers and a large coke")
print(response)

# Complete order
response = agent.chat("I'll take delivery please")
print(response)
```

## 🔧 Development

### Graph Visualization

Use the included Jupyter notebook to visualize the conversation flow:

```bash
jupyter notebook graph.ipynb
```

