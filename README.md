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

## 🖥️ CLI Arguments

The `simulate.py` script supports the following command-line arguments:

### Required Arguments

| Argument     | Type   | Description                | Example                                              |
| ------------ | ------ | -------------------------- | ---------------------------------------------------- |
| `--persona`  | string | Path to persona YAML file  | `personas/alex_smith.yml`                            |
| `--scenario` | string | Path to scenario YAML file | `scenarios/referralCrisis_seniorBackendEngineer.yml` |

### Optional Arguments

| Argument           | Type    | Default                    | Description                                   | Example                                   |
| ------------------ | ------- | -------------------------- | --------------------------------------------- | ----------------------------------------- |
| `--output`         | string  | `output`                   | Output directory for transcripts              | `--output my_results`                     |
| `--seed`           | integer | auto-generated             | Deterministic RNG seed for per-turn decisions | `--seed 12345678`                         |
| `--temperature`    | float   | `0.7`                      | Sampling temperature (0.0-1.2)                | `--temperature 0.0`                       |
| `--top_p`          | float   | `1.0`                      | Nucleus sampling top_p (0.0-1.0)              | `--top_p 0.9`                             |
| `--sut-prompt`     | string  | `prompts/recruiter_v1.txt` | Path to SUT system prompt file                | `--sut-prompt prompts/recruiter_v1.2.txt` |
| `--use-controller` | boolean | `True`                     | Enable or disable the controller logic        | `--use-controller False`                  |
| `--timeout`        | integer | `120`                      | Maximum conversation duration in seconds      | `--timeout 180`                           |

### Usage Examples

**Basic run:**

```bash
python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml
```

**Deterministic run with custom settings:**

```bash
python simulate.py \
  --persona personas/alex_smith.yml \
  --scenario scenarios/referralCrisis_seniorBackendEngineer.yml \
  --seed 12345678 \
  --temperature 0.0 \
  --top_p 1.0 \
  --timeout 180
```

**Custom prompt and output:**

```bash
python simulate.py \
  --persona personas/sara_mitchell.yml \
  --scenario scenarios/ai_scepticism_in_recruitment.yml \
  --sut-prompt prompts/recruiter_v1.2.txt \
  --output custom_results \
  --use-controller True
```

**Testing without controller:**

```bash
python simulate.py \
  --persona personas/alex_smith.yml \
  --scenario scenarios/referralCrisis_seniorBackendEngineer.yml \
  --use-controller False \
  --timeout 300
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

### 📈 Comprehensive Analytics & Failure Categorization

- **Conversation Flow Analysis**: Track turn-by-turn interactions
- **Information Extraction**: Automatically extract job details, requirements, and preferences
- **Outcome Assessment**: Evaluate conversation completion and success metrics
- **Enhanced Failure Categorization**: Comprehensive failure detection and classification:
  - **10 Distinct Failure Categories**: Timeout, API errors, persona drift, protocol violations, etc.
  - **Turn-specific Tracking**: Pinpoint exactly where failures occurred
  - **Contextual Information**: Rich failure context for debugging
  - **Automated Detection**: Real-time failure identification during conversations
- **Advanced Reporting**: Multi-format failure analysis:
  - **Console Output**: Immediate failure summaries with emoji indicators
  - **Markdown Transcripts**: Dedicated failure analysis sections
  - **Detailed Logging**: Comprehensive failure information in logs
- **Langfuse Integration**: Full observability with traces, spans, and evaluations
  - Enhanced trace tags include:
    - `persona`, `scenario`
    - `seed:<int>`, `temp:<float>`, `top_p:<float>`
    - `clarify:<0-1>`, `tangent:<0-1>`, `hesitation:<0-1>`
- **Enhanced Sampling Parameter Logging**: Complete observability of seed, temperature, and top_p:
  - **Transcript Headers**: Sampling parameters in markdown output
  - **JSONL Metadata**: Structured parameter data for analysis
  - **Filename Integration**: Seed values in output filenames for easy identification
  - **Console Reporting**: Immediate parameter visibility in simulation results

### 🔧 Flexible API Integration

Support for multiple API providers:

- OpenRouter (recommended)
- OpenAI Direct
- Custom API endpoints
- Easy configuration switching

### ⚡ Optimized Performance

Connection pooling and performance optimizations:

- **Connection Pooling**: Reuses HTTP connections for multiple requests
- **Session Management**: Optimized `requests.Session()` with connection pools
- **Configurable Pool Settings**: Customizable pool size and connection limits
- **Automatic Cleanup**: Proper connection cleanup after simulations
- **Timeout Handling**: 30-second request timeouts to prevent hanging

## 🚨 Failure Categorization & Quality Monitoring

Staffer Sims features advanced failure detection and categorization to ensure simulation quality and reliability:

### Failure Categories

| Category                   | Description                              | Detection Method                         |
| -------------------------- | ---------------------------------------- | ---------------------------------------- |
| **Timeout**                | Conversation exceeded time limits        | Automatic timeout monitoring             |
| **API Error**              | General API communication failures       | Exception handling                       |
| **SUT Error**              | System Under Test specific failures      | API response analysis                    |
| **Proxy Error**            | Proxy client specific failures           | API response analysis                    |
| **Persona Drift**          | User breaking character or role          | Pattern matching & phrase detection      |
| **Protocol Violation**     | Breaking conversation rules              | Turn analysis (e.g., multiple questions) |
| **Incomplete Information** | Missing mandatory fields                 | Field extraction analysis                |
| **User Abandonment**       | Premature conversation termination       | Turn count & duration analysis           |
| **System Error**           | Internal system errors                   | Exception handling                       |
| **Validation Error**       | Configuration or input validation issues | Pre-flight validation                    |

### Failure Detection Features

#### **Real-time Monitoring**

- Continuous conversation quality assessment
- Turn-by-turn failure detection
- Immediate error categorization

#### **Persona Adherence Tracking**

- Role reversal detection (proxy acting like recruiter)
- Character breaking identification (revealing AI nature)
- Inappropriate phrase recognition

#### **Protocol Compliance**

- Single question per turn enforcement
- Conversation flow validation
- Response format verification

#### **Information Completeness**

- Mandatory field extraction tracking
- Completion percentage calculation
- Missing information identification

### Reporting Formats

#### **Console Output**

```bash
⚠️  Failures Detected: 3 total
   • timeout: Conversation exceeded 120s time limit (turn 8)
   • persona_drift: Proxy user acting like recruiter instead of hiring manager (turn 5)
   • incomplete_information: Missing 4 out of 8 mandatory fields
```

#### **Markdown Transcripts**

Enhanced transcript files include dedicated failure analysis sections:

```markdown
**Failures Detected:** 3

## 🚨 Failure Analysis

### Timeout (Turn 8)

**Reason:** Conversation exceeded 120s time limit
**Context:** {'elapsed_time': 125.3, 'timeout_limit': 120, 'turns_completed': 8}

### Persona Drift (Turn 5)

**Reason:** Proxy user acting like recruiter instead of hiring manager
**Context:** {'violating_phrases': ['let me ask you about', 'i can help you with']}

### Incomplete Information

**Reason:** Missing 4 out of 8 mandatory fields
**Context:** {'missing_fields': ['salary_range', 'experience_level'], 'completion_percentage': 50.0}
```

#### **Detailed Logging**

Comprehensive failure information in application logs:

```
WARNING:simulation_engine:Failures detected in simulation 20240315_143022:
WARNING:simulation_engine:  - timeout: Conversation exceeded 120s time limit (turn 8)
WARNING:simulation_engine:    Context: {'elapsed_time': 125.3, 'timeout_limit': 120}
```

### Quality Metrics

#### **Failure Statistics**

- Total failure count per simulation
- Failure category distribution
- Turn-specific failure tracking
- Failure rate trends

#### **Quality Indicators**

- Conversation completion rates
- Information extraction success
- Persona adherence scores
- Protocol compliance metrics

## 🔬 Enhanced Sampling Parameter Logging

Staffer Sims provides comprehensive logging and observability of all sampling parameters to ensure full reproducibility and auditability:

### Sampling Parameters Tracked

| Parameter       | Description                                  | Default        | CLI Override    |
| --------------- | -------------------------------------------- | -------------- | --------------- |
| **Random Seed** | Deterministic RNG seed for reproducible runs | Auto-generated | `--seed`        |
| **Temperature** | Sampling temperature (0.0-1.2)               | 0.7            | `--temperature` |
| **Top-P**       | Nucleus sampling parameter (0.0-1.0)         | 1.0            | `--top_p`       |

### Output Format Integration

#### **Enhanced Markdown Transcripts**

```markdown
# Transcript 20240315_143022

**Persona:** Alex Smith
**Scenario:** Senior Backend Engineer
**SUT System Prompt:** prompts/recruiter_v1.txt
**Random Seed:** 12345
**Temperature:** 0.7
**Top-P:** 1.0
**SUT Model:** gpt-4 - 14:30:22 15/03/2024
**Proxy Model:** gpt-3.5-turbo - 14:30:22 15/03/2024
**Conversation Duration:** 45.2s / 120s
```

#### **Enhanced JSONL Metadata**

```json
{"type": "metadata", "run_id": "20240315_143022", "persona": "Alex Smith", "scenario": "Senior Backend Engineer", "sut_prompt_path": "prompts/recruiter_v1.txt", "random_seed": 12345, "temperature": 0.7, "top_p": 1.0, "elapsed_time": 45.2, "timeout_reached": false, "timeout_limit": 120, "total_turns": 8}
{"role": "system", "content": "Hello! I'm here to help you find the right candidate...", "model": "gpt-4", "timestamp": "14:30:22 15/03/2024", "turn_controller": null}
```

#### **Enhanced Console Output**

```bash
Saved: output/20240315_143022__alex-smith__senior-backend-engineer__seed_12345.md
Saved: output/20240315_143022__alex-smith__senior-backend-engineer__seed_12345.jsonl
Conversation Outcome: completed_successfully (Level: 100%)
Conversation Duration: 45.2s / 120s
Sampling Parameters: Seed=12345, Temp=0.7, Top-P=1.0
Information Gathered: 5 skills, Role: Senior Backend Engineer, Location: Remote
API Usage: 1250 tokens (4 SUT + 4 Proxy calls)
Estimated Cost: $0.003750
```

#### **Enhanced Langfuse Trace Tags**

```
Alex Smith
Senior Backend Engineer
seed:12345
temp:0.7
top_p:1.0
clarify:0.40
tangent:0.20
hesitation:0.10
```

### Filename Integration

Output files now include seed values for easy identification and reproducibility:

```
output/
├── 20240315_143022__alex-smith__senior-backend-engineer__seed_12345.md
├── 20240315_143022__alex-smith__senior-backend-engineer__seed_12345.jsonl
├── 20240315_143023__sara-mitchell__ai-scepticism__seed_67890.md
└── 20240315_143023__sara-mitchell__ai-scepticism__seed_67890.jsonl
```

### Benefits

#### **🔍 Full Observability**

- All sampling parameters visible in every output format
- Consistent parameter logging across transcripts, JSONL, and traces
- Immediate parameter visibility in console output

#### **📊 Easy Auditing**

- Parameters logged consistently across all output formats
- JSONL metadata enables programmatic analysis of parameter effects
- Langfuse tags allow filtering and analysis by sampling parameters

#### **🎯 Reproducibility**

- Seed values in filenames make it easy to identify specific runs
- Complete parameter tracking enables exact reproduction of simulations
- Deterministic runs with same parameters produce identical results

#### **📈 Analysis Ready**

- Structured metadata in JSONL format for data analysis
- Trace correlation through Langfuse tags
- Parameter effect analysis across multiple simulation runs

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

- **`*.md`**: Human-readable conversation transcripts with enhanced analysis:
  - Complete conversation flow with sampling parameters in header
  - Turn-by-turn controller decisions
  - Comprehensive failure categorization section
  - Contextual failure information
  - Quality metrics and completion status
  - Seed, temperature, and top_p values prominently displayed
- **`*.jsonl`**: Machine-readable conversation data with structured metadata:
  - Metadata header with complete sampling parameters
  - Conversation turns with model and timestamp information
  - Structured format for programmatic analysis
  - Seed values in filenames for easy identification
- **Langfuse traces**: Detailed observability data with enhanced tagging:
  - Enhanced trace tags including `temp:` and `top_p:` values
  - Failure metadata and quality metrics
  - Cost tracking and usage statistics
  - Conversation outcome analysis with sampling parameter correlation

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

### 6. Failure Analysis & Debugging

Comprehensive failure detection and categorization for:

- Identifying conversation quality issues
- Debugging persona adherence problems
- Monitoring protocol compliance
- Tracking information extraction completeness
- Analyzing timeout and performance issues

### 7. System Reliability Monitoring

Continuous monitoring of simulation quality:

- Real-time failure detection during conversations
- Automated quality metrics collection
- Performance trend analysis
- System health monitoring

### 8. Parameter Analysis & Reproducibility

Comprehensive sampling parameter tracking for:

- Analyzing the effect of temperature and top_p on conversation quality
- Reproducing exact simulation runs with identical parameters
- Comparing performance across different sampling configurations
- Parameter optimization for specific use cases
- Research and experimentation with different AI model settings

## 🛠️ Development

### Enhanced Data Models for Failure Analysis

The system includes comprehensive data models for failure categorization and quality monitoring:

#### **FailureDetail Model**

```python
@dataclass
class FailureDetail:
    category: FailureCategory          # Failure type (enum)
    reason: str                        # Human-readable reason
    error_message: Optional[str]       # API error message (if applicable)
    turn_occurred: Optional[int]       # Turn number where failure occurred
    context: Optional[Dict[str, Any]]  # Additional context data
```

#### **ConversationOutcome Model**

```python
@dataclass
class ConversationOutcome:
    status: ConversationStatus         # Success/failure status (enum)
    completion_level: int              # 0-100 completion percentage
    success_indicators: List[str]      # Success indicators
    issues: List[str]                  # Issues identified
    failures: List[FailureDetail]     # Detailed failure list
    total_failures: int               # Total failure count
```

#### **Failure Categories (Enum)**

```python
class FailureCategory(Enum):
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    PERSONA_DRIFT = "persona_drift"
    SUT_ERROR = "sut_error"
    PROXY_ERROR = "proxy_error"
    PROTOCOL_VIOLATION = "protocol_violation"
    INCOMPLETE_INFORMATION = "incomplete_information"
    USER_ABANDONMENT = "user_abandonment"
    SYSTEM_ERROR = "system_error"
    VALIDATION_ERROR = "validation_error"
```

#### **Enhanced Analysis Methods**

- `determine_conversation_outcome()` - Comprehensive outcome analysis with failure detection
- `_analyze_persona_adherence()` - Role-playing quality assessment
- `_analyze_information_completeness()` - Information extraction validation

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
    --sut-prompt prompts/recruiter_v1.txt \
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
