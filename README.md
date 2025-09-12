# Staffer Sims

A sophisticated AI-powered simulation platform for testing and evaluating recruiter assistant systems. This tool enables realistic conversation simulations between hiring managers (proxy users) and AI recruiter assistants (SUT - System Under Test) to assess performance, extract structured information, and validate recruitment workflows.

## 🎯 Purpose

Staffer Sims addresses the critical need for testing AI recruiter systems in realistic scenarios without requiring human participants. It provides:

- **Automated Testing**: Simulate realistic hiring conversations between AI agents
- **Performance Evaluation**: Assess how well AI recruiters gather information and guide hiring processes
- **Information Extraction**: Dynamically extract structured data from conversations based on recruiter prompts
- **Observability**: Full tracing and monitoring through Langfuse integration
- **Scalable Testing**: Run multiple scenarios with different personas and job requirements

## 🏗️ Architecture

The project follows a modular, service-oriented architecture with clear separation of concerns:

```
staffer-sims/
├── analysis/              # Conversation analysis and information extraction
│   ├── conversation_analyzer.py    # Dynamic field extraction from conversations
│   └── models.py                   # Data models for analysis results
├── config/                # Configuration management
│   ├── settings.py                 # Centralized settings with environment support
│   ├── env_loader.py              # Environment-specific configuration loading
│   └── environments/              # Environment-specific .env files
├── services/              # External API integrations
│   ├── base_api_client.py         # Base HTTP client with retry logic
│   ├── sut_client.py              # System Under Test API client
│   ├── proxy_client.py            # Proxy user (hiring manager) API client
│   └── langfuse_service.py        # Langfuse observability integration
├── simulation/            # Core simulation engine
│   └── simulation_engine.py       # Orchestrates conversation flow
├── personas/              # Hiring manager personas
│   └── alex_smith.yml             # Example hiring manager profile
├── scenarios/             # Job scenarios and requirements
│   └── senior_backend_engineer.yml # Example job scenario
├── prompts/               # System prompts and templates
│   └── recruiter_v1.txt           # Recruiter assistant system prompt
└── output/                # Simulation results and transcripts
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)
- API keys for your chosen providers (OpenRouter, OpenAI, etc.)

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd staffer-sims
   ```

2. **Create and activate virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**

   ```bash
   cp env.template .env
   # Edit .env with your API keys and configuration
   ```

5. **Validate configuration**
   ```bash
   python validate_config.py
   ```

### Running Simulations

**Basic simulation:**

```bash
python simulate.py --persona personas/alex_smith.yml --scenario scenarios/senior_backend_engineer.yml
```

**With custom output directory:**

```bash
python simulate.py --persona personas/alex_smith.yml --scenario scenarios/senior_backend_engineer.yml --output my_results
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file based on `env.template`:

```bash
# Environment selection
ENVIRONMENT=development

# API Provider (openrouter, openai, etc.)
API_PROVIDER=openrouter

# API Keys
OPENROUTER_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Service URLs
SUT_URL=https://openrouter.ai/api/v1/chat/completions
PROXY_URL=https://openrouter.ai/api/v1/chat/completions
LANGFUSE_HOST=https://your-langfuse-instance.com

# Langfuse Configuration
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key

# Models
SUT_MODEL=openai/gpt-4o-mini
PROXY_MODEL=openai/gpt-4o-mini
```

### Environment-Specific Configuration

The system supports multiple environments:

- `development` - Local development settings
- `staging` - Staging environment settings
- `production` - Production environment settings

Each environment has its own `.env` file in `config/environments/`.

## 📊 Key Features

### 🔄 Dynamic Field Extraction

The conversation analyzer dynamically parses mandatory fields from recruiter prompts, making it:

- **Industry Agnostic**: Works with any job type (tech, marketing, finance, etc.)
- **Prompt Flexible**: Automatically adapts to different recruiter prompt structures
- **Future Proof**: No code changes needed when mandatory fields change

### 🎭 Realistic Personas

Pre-configured hiring manager personas with:

- Detailed background and motivations
- Specific pain points and hiring challenges
- Behavioral patterns and response formulas
- Role adherence mechanisms

### 📈 Comprehensive Analytics

- **Conversation Flow Analysis**: Track turn-by-turn interactions
- **Information Extraction**: Automatically extract job details, requirements, and preferences
- **Outcome Assessment**: Evaluate conversation completion and success metrics
- **Langfuse Integration**: Full observability with traces, spans, and evaluations

### 🔧 Flexible API Integration

Support for multiple API providers:

- OpenRouter (recommended)
- OpenAI Direct
- Custom API endpoints
- Easy configuration switching

## 📁 File Structure Details

### Core Components

- **`simulate.py`**: Main entry point - orchestrates simulation execution
- **`SimulationEngine`**: Core simulation logic and conversation flow management
- **`ConversationAnalyzer`**: Dynamic information extraction and outcome analysis
- **`BaseAPIClient`**: Robust HTTP client with retry logic and error handling

### Configuration Files

- **`personas/*.yml`**: Hiring manager personas with detailed behavioral specifications
- **`scenarios/*.yml`**: Job scenarios defining requirements and context
- **`prompts/recruiter_v1.txt`**: System prompt for recruiter assistant behavior

### Output Files

- **`*.md`**: Human-readable conversation transcripts
- **`*.jsonl`**: Machine-readable conversation data for analysis
- **Langfuse traces**: Detailed observability data with spans and evaluations

## 🔍 Use Cases

### 1. AI Recruiter Testing

Test how well your AI recruiter system gathers information and guides hiring conversations.

### 2. Prompt Engineering

Evaluate different recruiter prompts and their effectiveness in extracting job requirements.

### 3. Performance Benchmarking

Compare different AI models or configurations for recruitment tasks.

### 4. Training Data Generation

Generate realistic conversation data for training or fine-tuning recruitment AI systems.

### 5. Quality Assurance

Validate that AI recruiters follow proper workflows and extract all necessary information.

## 🛠️ Development

### Adding New Personas

Create a new persona file in `personas/`:

```yaml
name: Sarah Johnson
role: Marketing Director
about: |
  Sarah leads marketing at a fast-growing startup and needs to hire...
needs_goals:
  - Hire a Marketing Manager
  - Find someone with digital marketing expertise
pain_points:
  - Previous hires lacked technical marketing skills
  - Need someone who can scale our marketing efforts
```

### Adding New Scenarios

Create a new scenario file in `scenarios/`:

```yaml
title: Marketing Manager (Growth)
entry_context: |
  I need to hire a Marketing Manager to help scale our growth...
challenges:
  - Finding candidates with both creative and analytical skills
requirements:
  - 3+ years digital marketing experience
  - Experience with growth marketing
goal: Hire a Marketing Manager who can drive user acquisition
```

### Customizing Field Extraction

The system automatically reads mandatory fields from `prompts/recruiter_v1.txt`. To add new fields:

1. Update the recruiter prompt with new mandatory fields
2. The analyzer will automatically detect and extract them
3. No code changes required

## 📋 Dependencies

### Core Dependencies

- **`langfuse`**: Observability and tracing platform
- **`pyyaml`**: YAML configuration file parsing
- **`python-dotenv`**: Environment variable management
- **`requests`**: HTTP client for API interactions

### Optional Dependencies

- **`pydantic`**: Data validation (for future enhancements)
- **`fastapi`**: Web API framework (for future web interface)

## 🔧 Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure all required API keys are set in your `.env` file
2. **Import Errors**: Make sure you're running from the project root directory
3. **Configuration Issues**: Run `python validate_config.py` to check your setup
4. **Permission Errors**: Ensure output directory is writable

### Debug Mode

Enable debug logging by setting:

```bash
export LOG_LEVEL=DEBUG
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built for testing AI recruiter systems and improving hiring processes
- Integrates with Langfuse for comprehensive observability
- Designed with modularity and extensibility in mind

---

**Need help?** Check the configuration guide in `CONFIGURATION.md` or open an issue for support.
