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
├── personas/              # Hiring manager personas (decoupled from scenarios)
│   ├── alex_smith.yml             # Persona with behavior dials
│   └── sara_mitchell.yml          # Persona with behavior dials
├── scenarios/             # Situational constraints and objectives
│   └── referralCrisis_seniorBackendEngineer.yml # Example job scenario with contract fields
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
python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml
```

**With custom output directory:**

```bash
python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml --output my_results
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
- Behavior dials (runtime-controllable):
  - `question_propensity`: `{ when_uncertain: float, when_budget: float }`
  - `tangent_propensity`: `{ after_field_capture: float }`
  - `hesitation_patterns`: `string[]`
  - `elaboration_distribution`: `{ one_sentence: float, two_sentences: float, three_sentences: float }`
  - Optional: `topic_preferences`: `string[]`

### 📈 Comprehensive Analytics

- **Conversation Flow Analysis**: Track turn-by-turn interactions
- **Information Extraction**: Automatically extract job details, requirements, and preferences
- **Outcome Assessment**: Evaluate conversation completion and success metrics
- **Langfuse Integration**: Full observability with traces, spans, and evaluations
  - Trace tags now include:
    - `persona`, `scenario`
    - `seed:<int>`
    - `clarify:<0-1>`, `tangent:<0-1>`, `hesitation:<0-1>`

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

- **`personas/*.yml`**: Hiring manager personas with detailed behavioral specifications and behavior dials
- **`scenarios/*.yml`**: Job scenarios defining requirements, context, and interaction contract fields
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

# Behavior dials (engine reads these at runtime)
behavior_dials:
  question_propensity:
    when_uncertain: 0.6
    when_budget: 0.5
  tangent_propensity:
    after_field_capture: 0.3
  hesitation_patterns:
    - 'Honestly,'
    - 'Let me think…'
  elaboration_distribution:
    one_sentence: 0.7
    two_sentences: 0.25
    three_sentences: 0.05
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

# Contract fields used by the engine to build an interaction contract
pressure_index:
  timeline: high
  quality: medium
  budget: medium
must_hit_metrics:
  - 'p95_latency<=250ms'
  - 'deploys/week>=2'
consultative_topics:
  - 'hire vs perfect_fit tradeoff'
  - 'market_rate guidance'
success_criteria:
  - 'all mandatory fields captured'
  - 'proxy confirms summary'
  - 'closure message'

goal: Hire a Marketing Manager who can drive user acquisition
```

### Customizing Field Extraction

The system automatically reads mandatory fields from `prompts/recruiter_v1.txt`. To add new fields:

1. Update the recruiter prompt with new mandatory fields
2. The analyzer will automatically detect and extract them
3. No code changes required

### How Runtime Dials Work

At run start, the engine computes behavior dials from `persona.behavior_dials` × `scenario.pressure_index`:

- `clarifying_question_prob = persona.question_propensity.when_uncertain × avg(pressure_index)` (budget boosts slightly)
- `tangent_prob_after_field = persona.tangent_propensity.after_field_capture × min(1, avg(pressure_index))`
- `hesitation_insert_prob = persona.elaboration_distribution.two_sentences`

The engine injects an `INTERACTION CONTRACT` block into the proxy system prompt containing:

- Priorities (fields → consultative → tangents → closure)
- Behavior dials with values
- A `randomness_seed` for reproducibility

Langfuse tags include `seed` and dial values for observability.

### Deterministic RNG and per-turn decisions

The engine uses a seeded RNG to turn dials into reproducible yes/no decisions per turn:

- rng_seed: Generated once per run; attached to the scenario and logged to Langfuse as `seed:<int>`.
- Clarifying decision:
  - Draw r = hash(rng_seed, turn_idx, "clarify") ∈ [0,1).
  - Allow only if (uncertainty phrase detected) AND r < `clarifying_question_prob`.
- Tangent decision:
  - Draw r = hash(rng_seed, turn_idx, "tangent") ∈ [0,1).
  - Allow only if (a field was just captured this turn) AND (cooldown elapsed) AND r < `tangent_prob_after_field`.
- Hesitation: Guided by `hesitation_insert_prob`; used as a soft prompt cue.

The engine emits a per‑turn `TURN CONTROLLER` block appended to the proxy system prompt, e.g.:

```text
TURN CONTROLLER:
- clarifying_allowed: yes (roll: 0.42 < 0.58 if uncertainty phrase)
- tangent_allowed: no (roll: 0.77 < 0.30; cooldown: 2; field_just_captured: false)
- on_summary: confirm succinctly with approved closure phrasing
- resume_policy: after any tangent, answer the recruiter's last question directly
```

Reproducibility: Same persona + scenario + dials + seed ⇒ identical decisions. Changing only the seed explores different, statistically consistent human behaviors.

### Fixing the seed across runs

You can force a specific seed via either CLI or environment:

- CLI:
  ```bash
  python simulate.py --persona personas/alex_smith.yml \
    --scenario scenarios/referralCrisis_seniorBackendEngineer.yml \
    --seed 12345678
  ```
- Environment (useful for CI):
  ```bash
  export RNG_SEED=12345678
  python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml
  ```

CLI flag takes precedence over the environment variable.

### Adjusting temperature and top_p

Control sampling for reproducibility vs creativity:

- CLI:
  ```bash
  python simulate.py --persona personas/alex_smith.yml \
    --scenario scenarios/referralCrisis_seniorBackendEngineer.yml \
    --seed 12345678 --temperature 0.0 --top_p 1.0
  ```
- Environment:
  ```bash
  export TEMPERATURE=0.0
  export TOP_P=1.0
  python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml
  ```

Notes:

- T=0.0 & top_p=1.0 → deterministic wording (given the same seed and prompts).
- Raise T (e.g., 0.3–0.7) for more natural variation in phrasing.

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
