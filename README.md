# 🤖 Personal WhatsApp Assistant - Enhanced Edition

A sophisticated AI-powered personal assistant built with **FastAPI** and **LangChain** that integrates WhatsApp, Gmail, and Google Calendar for intelligent email management and scheduling.

## 🚀 **Key Features**

### **Modern LangChain Integration**
- **Latest LangChain patterns** with `langchain-openai` and `langchain-core`
- **Pydantic output parsers** for structured responses
- **Conversation memory** with context-aware processing
- **Multi-step reasoning** for complex email analysis
- **Custom output schemas** for type safety

### **Production-Ready FastAPI**
- **Async/await patterns** throughout
- **Pydantic validation** for all inputs/outputs
- **Comprehensive error handling** with custom exceptions
- **Background task processing** for non-blocking operations
- **Health checks and metrics** endpoints
- **Docker containerization** ready

### **Advanced AI Capabilities**
- **Email sentiment analysis** and intent detection
- **Context-aware response generation** with conversation history
- **Priority-based email categorization**
- **Action item extraction** and follow-up tracking
- **Meeting scheduling** with availability checking
- **Human-in-the-loop** approval system

## 📋 **Prerequisites**

- Python 3.11+
- OpenAI API key
- UltraMsg account for WhatsApp integration
- Google Cloud project with Gmail and Calendar APIs enabled

## 🛠 **Installation**

### **1. Clone and Setup**
```bash
git clone <your-repo>
cd my-assistant
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### **2. Install Dependencies**
```bash
# For enhanced version with latest LangChain
pip install -r requirements_enhanced.txt

# Or for basic version
pip install -r requirements.txt
```

### **3. Environment Configuration**
```bash
cp env.example .env
# Edit .env with your actual credentials
```

### **4. Google API Setup**
1. Create a Google Cloud project
2. Enable Gmail and Calendar APIs
3. Create service account credentials
4. Download credentials JSON files to `./credentials/`

## 🏗 **Architecture Overview**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   WhatsApp      │    │   FastAPI App    │    │   AI Engine     │
│   Integration   │◄──►│   (Router)       │◄──►│   (LangChain)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Integrations   │
                       │  Gmail + Calendar│
                       └──────────────────┘
```

## 🚀 **Running the Application**

### **Development Mode**
```bash
# Basic version
python app.py

# Enhanced version with modern patterns
python app_enhanced.py

# With auto-reload
uvicorn app_enhanced:app --reload --host 0.0.0.0 --port 8000
```

### **Production Mode with Docker**
```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build individual container
docker build -t whatsapp-assistant .
docker run -p 8000:8000 --env-file .env whatsapp-assistant
```

## 📚 **API Documentation**

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/

### **Key Endpoints**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/whatsapp-webhook` | POST | WhatsApp message webhook |
| `/gmail-webhook` | POST | Gmail notification webhook |
| `/calendar-webhook` | POST | Calendar event webhook |
| `/status` | GET | System status |
| `/command` | POST | Execute command (testing) |
| `/metrics` | GET | Application metrics |

## 🤖 **AI Features Deep Dive**

### **1. Modern LangChain Patterns**

The enhanced version uses the latest LangChain patterns:

```python
# Modern chain composition
response_chain = (
    ChatPromptTemplate.from_messages([...])
    | ChatOpenAI(model="gpt-4")
    | PydanticOutputParser(pydantic_object=EmailResponse)
)

# Structured output with Pydantic
class EmailResponse(BaseModel):
    response: str
    tone: str
    confidence: float
    suggestions: List[str]
    action_items: List[str]
```

### **2. Conversation Memory**

```python
# Context-aware processing
processor = AdvancedEmailProcessor()
result = await processor.process_email_with_context(
    email_data, 
    sender_id="user@example.com"
)
```

### **3. Multi-Step Reasoning**

1. **Email Analysis**: Sentiment, intent, priority detection
2. **Context Building**: Previous conversation history
3. **Response Generation**: Style-matched, context-aware responses
4. **Action Planning**: Extract and track action items

## 🔧 **Configuration Options**

### **Environment Variables**

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `ULTRAMSG_TOKEN` | UltraMsg API token | Required |
| `MY_PHONE_NUMBER` | Your WhatsApp number | Required |
| `DEBUG` | Debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `AI_PROCESSING_TIMEOUT` | AI processing timeout | `30` |
| `ENABLE_CONVERSATION_MEMORY` | Enable memory | `true` |

### **AI Model Configuration**

```python
# In .env file
OPENAI_MODEL=gpt-4  # or gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=1000
```

## 📊 **Monitoring and Observability**

### **Health Checks**
```bash
curl http://localhost:8000/status
```

### **Metrics**
```bash
curl http://localhost:8000/metrics
```

### **Logging**
Structured logging with configurable levels:
```python
logger = get_logger(__name__)
logger.info("Processing email", extra={"email_id": email_id})
```

## 🧪 **Testing**

```bash
# Run tests
pytest

# With coverage
pytest --cov=src

# Test specific module
pytest tests/test_ai_responder.py
```

## 🚀 **Deployment Strategies**

### **1. Docker Deployment**
```bash
# Production build
docker-compose -f docker-compose.prod.yml up -d
```

### **2. Cloud Deployment**
- **AWS**: ECS with Application Load Balancer
- **Google Cloud**: Cloud Run with Cloud SQL
- **Azure**: Container Instances with Cosmos DB

### **3. Kubernetes**
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: whatsapp-assistant
spec:
  replicas: 3
  selector:
    matchLabels:
      app: whatsapp-assistant
  template:
    spec:
      containers:
      - name: assistant
        image: whatsapp-assistant:latest
        ports:
        - containerPort: 8000
```

## 🔒 **Security Best Practices**

1. **Environment Variables**: Never commit secrets
2. **API Keys**: Rotate regularly
3. **HTTPS**: Use SSL/TLS in production
4. **Rate Limiting**: Implement request throttling
5. **Input Validation**: Validate all inputs with Pydantic
6. **Error Handling**: Don't expose internal errors

## 🐛 **Troubleshooting**

### **Common Issues**

1. **LangChain Import Errors**
   ```bash
   pip install langchain-openai langchain-core
   ```

2. **OpenAI API Errors**
   - Check API key validity
   - Verify billing and usage limits
   - Check rate limits

3. **WhatsApp Integration Issues**
   - Verify UltraMsg credentials
   - Check webhook URL configuration
   - Ensure phone number format is correct

4. **Google API Authentication**
   - Verify credentials file path
   - Check OAuth scopes
   - Ensure APIs are enabled

### **Debug Mode**
```bash
DEBUG=true LOG_LEVEL=DEBUG python app_enhanced.py
```

## 📈 **Performance Optimization**

1. **Async Processing**: All I/O operations are async
2. **Connection Pooling**: Reuse HTTP connections
3. **Caching**: Redis for frequently accessed data
4. **Background Tasks**: Non-blocking email processing
5. **Memory Management**: Conversation history limits

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 **License**

MIT License - see LICENSE file for details

## 🙏 **Acknowledgments**

- **LangChain** for the amazing AI framework
- **FastAPI** for the high-performance web framework
- **OpenAI** for the powerful language models
- **UltraMsg** for WhatsApp integration

---

**Built with ❤️ using FastAPI and LangChain**


