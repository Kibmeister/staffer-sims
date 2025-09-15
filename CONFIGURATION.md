# Environment Configuration Guide

This guide explains how to set up and manage environment configuration for the Staffer Sims project.

## 🚀 Quick Start

1. **Copy the template:**

   ```bash
   cp env.template .env
   ```

2. **Fill in your API keys:**

   ```bash
   # Edit .env file with your actual API keys
   OPENAI_API_KEY=your_actual_openai_key
   OPENROUTER_API_KEY=your_actual_openrouter_key
   LANGFUSE_PUBLIC_KEY=your_actual_langfuse_public_key
   LANGFUSE_SECRET_KEY=your_actual_langfuse_secret_key
   ```

3. **Validate configuration:**

   ```bash
   python validate_config.py
   ```

4. **Run simulation:**
   ```bash
   python simulate.py --persona personas/alex_smith.yml --scenario scenarios/senior_backend_engineer.yml
   ```

## 🖥️ Command Line Interface

### Available CLI Arguments

| Argument           | Type    | Required | Default                    | Validation                                             | Description                                  |
| ------------------ | ------- | -------- | -------------------------- | ------------------------------------------------------ | -------------------------------------------- |
| `--persona`        | string  | ✅       | -                          | File exists, readable, valid YAML with required fields | Path to persona YAML file                    |
| `--scenario`       | string  | ✅       | -                          | File exists, readable, valid YAML with required fields | Path to scenario YAML file                   |
| `--output`         | string  | ❌       | `output`                   | Directory creation                                     | Output directory for transcripts             |
| `--seed`           | integer | ❌       | auto-generated             | Positive integer                                       | Deterministic RNG seed for reproducible runs |
| `--temperature`    | float   | ❌       | `0.7`                      | 0.0-2.0 range                                          | Sampling temperature for response creativity |
| `--top_p`          | float   | ❌       | `1.0`                      | 0.0-1.0 range                                          | Nucleus sampling top_p parameter             |
| `--sut-prompt`     | string  | ❌       | `prompts/recruiter_v1.txt` | File exists, readable                                  | Path to SUT system prompt file               |
| `--use-controller` | boolean | ❌       | `True`                     | true/false                                             | Enable/disable controller logic              |
| `--timeout`        | integer | ❌       | `120`                      | Positive integer                                       | Maximum conversation duration (seconds)      |

### CLI Usage Examples

**Standard simulation:**

```bash
python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml
```

**Deterministic simulation:**

```bash
python simulate.py \
  --persona personas/alex_smith.yml \
  --scenario scenarios/referralCrisis_seniorBackendEngineer.yml \
  --seed 12345678 \
  --temperature 0.0
```

**Custom timeout and prompt:**

```bash
python simulate.py \
  --persona personas/sara_mitchell.yml \
  --scenario scenarios/ai_scepticism_in_recruitment.yml \
  --sut-prompt prompts/recruiter_v1.2.txt \
  --timeout 300
```

**Disable controller for baseline testing:**

```bash
python simulate.py \
  --persona personas/alex_smith.yml \
  --scenario scenarios/referralCrisis_seniorBackendEngineer.yml \
  --use-controller False
```

### Validation Examples

**File validation errors:**

```bash
# Missing persona file
python simulate.py --persona missing.yml --scenario test.yml
# Output: ❌ Error: Persona file not found: missing.yml

# Invalid YAML syntax
python simulate.py --persona broken.yml --scenario test.yml
# Output: ❌ Error: Invalid YAML in persona file broken.yml: while parsing a block mapping
```

**Parameter validation errors:**

```bash
# Invalid temperature range
python simulate.py --persona test.yml --scenario test.yml --temperature 3.0
# Output: ❌ Error: Temperature must be between 0.0 and 2.0, got 3.0

# Invalid seed value
python simulate.py --persona test.yml --scenario test.yml --seed -1
# Output: ❌ Error: Seed must be a positive integer, got -1
```

**Help and usage information:**

```bash
# Show detailed help with examples
python simulate.py --help

# Show help for specific argument
python simulate.py --help | grep -A 5 "temperature"
```

## 🛡️ CLI Validation & Error Handling

Staffer Sims provides enterprise-grade validation and error handling for robust CLI operation:

### File Validation

All file inputs are validated before processing:

```bash
# File existence and readability checks
❌ Error: Persona file not found: personas/missing.yml
❌ Error: Scenario file is not readable: scenarios/protected.yml
❌ Error: SUT prompt path is not a file: prompts/directory
```

### YAML Validation

YAML files are validated for syntax and structure:

```bash
# YAML syntax validation
❌ Error: Invalid YAML in persona file personas/broken.yml: while parsing a block mapping

# Structure validation
❌ Error: Persona file missing required field 'name'
❌ Error: Scenario file must contain a YAML dictionary, got list
```

### Parameter Validation

Numeric parameters are validated against acceptable ranges:

```bash
# Range validation
❌ Error: Temperature must be between 0.0 and 2.0, got 3.0
❌ Error: Top-P must be between 0.0 and 1.0, got 1.5
❌ Error: Seed must be a positive integer, got -1
❌ Error: Timeout must be a positive integer, got 0
```

### Structured Logging

Logging is configured with appropriate levels for different use cases:

#### **INFO Level Logging**

```bash
2024-03-15 14:30:22 - simulate - INFO - Starting simulation in development environment
2024-03-15 14:30:22 - simulate - INFO - Persona file: personas/alex_smith.yml
2024-03-15 14:30:22 - simulate - INFO - Scenario file: scenarios/referralCrisis_seniorBackendEngineer.yml
2024-03-15 14:30:22 - simulate - INFO - Random seed: 12345
2024-03-15 14:30:22 - simulate - INFO - Temperature: 0.7
2024-03-15 14:30:22 - simulate - INFO - Controller enabled: True
```

#### **DEBUG Level Logging**

```bash
2024-03-15 14:30:22 - simulate - DEBUG - Full configuration: {'environment': 'development', ...}
2024-03-15 14:30:22 - simulate - DEBUG - Persona keys: ['name', 'description', 'behavior_dials']
2024-03-15 14:30:22 - simulate - DEBUG - Scenario keys: ['title', 'description', 'constraints']
```

#### **WARNING Level Logging**

```bash
2024-03-15 14:30:22 - simulate - WARNING - Simulation completed with 2 failures
```

#### **ERROR Level Logging**

```bash
2024-03-15 14:30:22 - simulate - ERROR - Simulation failed: API connection timeout
```

### Exit Codes

The CLI provides consistent exit codes for automation:

| Exit Code | Meaning            | Usage                                        |
| --------- | ------------------ | -------------------------------------------- |
| `0`       | Success            | Normal completion                            |
| `1`       | General Error      | Validation failures, file issues, API errors |
| `130`     | Keyboard Interrupt | User pressed Ctrl+C (SIGINT)                 |

### CI/CD Integration

The validation system is designed for CI/CD environments:

```bash
# CI-friendly error detection
if ! python simulate.py --persona test.yml --scenario test.yml; then
    echo "Simulation failed with exit code $?"
    exit 1
fi

# Structured logging for parsing
python simulate.py --persona test.yml --scenario test.yml 2>&1 | grep "ERROR\|❌"
```

### Validation Configuration

Validation behavior can be controlled through environment variables:

```bash
# Log level control
LOG_LEVEL=DEBUG  # INFO, DEBUG, WARNING, ERROR

# Validation strictness
VALIDATE_FILES=true  # Enable/disable file validation
VALIDATE_YAML=true   # Enable/disable YAML validation
VALIDATE_PARAMS=true # Enable/disable parameter validation
```

## 🔬 Enhanced Sampling Parameter Logging

Staffer Sims provides comprehensive logging and observability of all sampling parameters to ensure full reproducibility and auditability across all output formats.

### Sampling Parameters Configuration

#### **CLI Arguments**

```bash
# Set specific seed for reproducible runs
--seed 12345

# Configure temperature for response creativity
--temperature 0.7

# Set top_p for nucleus sampling
--top_p 1.0
```

#### **Environment Variables**

```bash
# Default values (can be overridden by CLI)
RNG_SEED=12345
TEMPERATURE=0.7
TOP_P=1.0
```

### Output Format Integration

#### **Enhanced Markdown Transcripts**

All markdown transcripts now include sampling parameters in the header:

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

JSONL files include structured metadata as the first line:

```json
{
  "type": "metadata",
  "run_id": "20240315_143022",
  "persona": "Alex Smith",
  "scenario": "Senior Backend Engineer",
  "sut_prompt_path": "prompts/recruiter_v1.txt",
  "random_seed": 12345,
  "temperature": 0.7,
  "top_p": 1.0,
  "elapsed_time": 45.2,
  "timeout_reached": false,
  "timeout_limit": 120,
  "total_turns": 8
}
```

#### **Enhanced Console Output**

Console output shows sampling parameters in the simulation summary:

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

Langfuse traces include sampling parameters as tags for filtering and analysis:

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

Output files include seed values for easy identification and reproducibility:

```
output/
├── 20240315_143022__alex-smith__senior-backend-engineer__seed_12345.md
├── 20240315_143022__alex-smith__senior-backend-engineer__seed_12345.jsonl
├── 20240315_143023__sara-mitchell__ai-scepticism__seed_67890.md
└── 20240315_143023__sara-mitchell__ai-scepticism__seed_67890.jsonl
```

### Configuration Examples

#### **Reproducible Research Runs**

```bash
# Fixed seed for reproducible results
python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml --seed 12345 --temperature 0.7 --top_p 1.0
```

#### **Parameter Sweep Testing**

```bash
# Test different temperature values
python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml --seed 12345 --temperature 0.3
python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml --seed 12345 --temperature 0.7
python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml --seed 12345 --temperature 1.0
```

#### **Creative vs Conservative Responses**

```bash
# Conservative responses (lower temperature)
python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml --temperature 0.3 --top_p 0.9

# Creative responses (higher temperature)
python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml --temperature 1.0 --top_p 1.0
```

### Performance Optimization

The system includes several performance optimizations:

- **Connection Pooling**: HTTP connections are reused across multiple API requests
- **Session Management**: Each API client uses an optimized `requests.Session()`
- **Configurable Pool Size**: Control the number of cached connections via environment variables
- **Automatic Cleanup**: Connections are properly closed after simulation completion
- **Request Timeouts**: 30-second timeouts prevent hanging requests

## 📁 Configuration Structure

```
config/
├── settings.py              # Main configuration class
├── env_loader.py            # Environment file loader
└── environments/            # Environment-specific configs
    ├── development.env      # Development settings
    ├── staging.env          # Staging settings
    └── production.env       # Production settings
```

## 🔧 Configuration Options

### API Provider Configuration

| Variable       | Options                        | Description                  |
| -------------- | ------------------------------ | ---------------------------- |
| `API_PROVIDER` | `openai`, `openrouter`, `both` | Which API provider(s) to use |

**Provider Options:**

- **`openai`**: Use OpenAI for both SUT and Proxy
- **`openrouter`**: Use OpenRouter for both SUT and Proxy (recommended)
- **`both`**: Use OpenAI for SUT, OpenRouter for Proxy

### Required Environment Variables

| Variable              | Required When                       | Description         | Example        |
| --------------------- | ----------------------------------- | ------------------- | -------------- |
| `OPENAI_API_KEY`      | `API_PROVIDER=openai` or `both`     | OpenAI API key      | `sk-...`       |
| `OPENROUTER_API_KEY`  | `API_PROVIDER=openrouter` or `both` | OpenRouter API key  | `sk-or-v1-...` |
| `LANGFUSE_PUBLIC_KEY` | Always                              | Langfuse public key | `pk-...`       |
| `LANGFUSE_SECRET_KEY` | Always                              | Langfuse secret key | `sk-...`       |

### Optional Environment Variables

| Variable           | Default                                         | Description                                       |
| ------------------ | ----------------------------------------------- | ------------------------------------------------- |
| `ENVIRONMENT`      | `development`                                   | Environment name (development/staging/production) |
| `DEBUG`            | `false`                                         | Enable debug mode                                 |
| `LOG_LEVEL`        | `INFO`                                          | Logging level (DEBUG/INFO/WARNING/ERROR)          |
| `SUT_URL`          | `http://localhost:8080/sut/chat`                | SUT service URL                                   |
| `PROXY_URL`        | `https://openrouter.ai/api/v1/chat/completions` | Proxy service URL                                 |
| `LANGFUSE_HOST`    | `https://cloud.langfuse.com`                    | Langfuse host URL                                 |
| `MAX_TURNS`        | `18`                                            | Maximum conversation turns                        |
| `REQUEST_TIMEOUT`  | `30`                                            | Individual API request timeout in seconds         |
| `RETRY_ATTEMPTS`   | `3`                                             | Number of retry attempts                          |
| `RETRY_DELAY`      | `1.0`                                           | Delay between retries in seconds                  |
| `OUTPUT_DIR`       | `output`                                        | Output directory for simulation results           |
| `RNG_SEED`         | None                                            | Default RNG seed for deterministic runs           |
| `TEMPERATURE`      | `0.7`                                           | Default sampling temperature                      |
| `TOP_P`            | `1.0`                                           | Default nucleus sampling top_p                    |
| `POOL_CONNECTIONS` | `10`                                            | Number of connection pools to cache               |
| `POOL_MAXSIZE`     | `20`                                            | Maximum connections to save in each pool          |

## 🌍 Environment-Specific Configuration

### Development Environment

- Debug mode enabled
- Verbose logging
- Longer timeouts
- Local service URLs

### Staging Environment

- Debug mode disabled
- Info-level logging
- Standard timeouts
- Staging service URLs

### Production Environment

- Debug mode disabled
- Warning-level logging
- Optimized timeouts
- Production service URLs

## 🚨 Failure Categorization & Quality Monitoring

Staffer Sims includes comprehensive failure detection and quality monitoring capabilities that can be configured through environment variables and CLI arguments.

### Failure Categories

The system automatically detects and categorizes 10 distinct types of failures:

| Category                   | Description                         | Configuration                         |
| -------------------------- | ----------------------------------- | ------------------------------------- |
| **Timeout**                | Conversation exceeds time limits    | `REQUEST_TIMEOUT`, `--timeout`        |
| **API Error**              | General API communication failures  | `RETRY_ATTEMPTS`, `RETRY_DELAY`       |
| **SUT Error**              | System Under Test specific failures | `SUT_URL`, request timeout settings   |
| **Proxy Error**            | Proxy client specific failures      | `PROXY_URL`, request timeout settings |
| **Persona Drift**          | User breaking character or role     | Built-in pattern detection            |
| **Protocol Violation**     | Breaking conversation rules         | Built-in rule enforcement             |
| **Incomplete Information** | Missing mandatory fields            | Dynamic field extraction              |
| **User Abandonment**       | Premature conversation termination  | `MAX_TURNS` configuration             |
| **System Error**           | Internal system errors              | Error handling and logging            |
| **Validation Error**       | Configuration validation issues     | Pre-flight validation                 |

### Quality Monitoring Configuration

#### **Timeout Settings**

```bash
# Environment variables
REQUEST_TIMEOUT=30        # Individual API request timeout (seconds)
MAX_TURNS=18             # Maximum conversation turns

# CLI arguments
--timeout 120            # Maximum conversation duration (seconds)
```

#### **Connection Pooling**

```bash
# Optimize performance and reduce API failures
POOL_CONNECTIONS=10      # Number of connection pools to cache
POOL_MAXSIZE=20         # Maximum connections per pool
```

#### **Retry Configuration**

```bash
# Handle transient API failures
RETRY_ATTEMPTS=3         # Number of retry attempts
RETRY_DELAY=1.0         # Delay between retries (seconds)
```

#### **Logging Configuration**

```bash
# Control failure reporting verbosity
LOG_LEVEL=INFO          # DEBUG for detailed failure analysis
DEBUG=true              # Enable debug mode for development
```

### Quality Metrics Collection

#### **Automatic Metrics**

- Failure count per simulation
- Failure category distribution
- Turn-specific failure tracking
- Conversation completion rates
- Information extraction success rates

#### **Langfuse Integration**

Enhanced observability with failure metadata:

```bash
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Failure Analysis Output

#### **Console Reporting**

Immediate failure summaries during simulation runs:

```bash
⚠️  Failures Detected: 3 total
   • timeout: Conversation exceeded 120s time limit (turn 8)
   • persona_drift: Proxy user acting like recruiter (turn 5)
   • incomplete_information: Missing 4 out of 8 mandatory fields
```

#### **Enhanced Markdown Transcripts**

Detailed failure analysis sections in transcript files:

- Categorized failure information
- Turn-specific failure tracking
- Contextual error details
- Quality metrics summary

#### **Structured Logging**

Comprehensive failure information in application logs:

```
WARNING:simulation_engine:Failures detected in simulation 20240315_143022:
WARNING:simulation_engine:  - timeout: Conversation exceeded 120s time limit (turn 8)
WARNING:simulation_engine:    Context: {'elapsed_time': 125.3, 'timeout_limit': 120}
```

### Configuration for Different Use Cases

#### **Quality Assurance Testing**

```bash
# Strict timeouts and comprehensive logging
REQUEST_TIMEOUT=15
MAX_TURNS=12
LOG_LEVEL=DEBUG
--timeout 90
```

#### **Performance Testing**

```bash
# Optimized for throughput
POOL_CONNECTIONS=20
POOL_MAXSIZE=50
REQUEST_TIMEOUT=30
RETRY_ATTEMPTS=1
```

#### **Development & Debugging**

```bash
# Enhanced logging and flexible timeouts
DEBUG=true
LOG_LEVEL=DEBUG
REQUEST_TIMEOUT=60
--timeout 300
```

## 🔍 Configuration Validation

The `validate_config.py` script checks:

- ✅ All required API keys are present
- ✅ Service URLs are valid
- ✅ Configuration methods work correctly
- ✅ Environment-specific settings are loaded

## 🛠️ Usage Examples

### Using Configuration in Code

```python
from config.settings import get_settings

# Get settings instance
settings = get_settings()

# Access configuration values
print(f"Environment: {settings.environment}")
print(f"API Provider: {settings.api_provider}")
print(f"Max turns: {settings.max_turns}")

# Get service configurations
langfuse_config = settings.get_langfuse_config()
proxy_config = settings.get_proxy_api_config()
sut_config = settings.get_sut_config()
sut_api_config = settings.get_sut_api_config()
```

### Environment-Specific Deployment

```bash
# Development with OpenRouter only
ENVIRONMENT=development API_PROVIDER=openrouter python simulate.py \
  --persona personas/alex_smith.yml \
  --scenario scenarios/referralCrisis_seniorBackendEngineer.yml

# Staging with both providers
ENVIRONMENT=staging API_PROVIDER=both python simulate.py \
  --persona personas/alex_smith.yml \
  --scenario scenarios/referralCrisis_seniorBackendEngineer.yml

# Production with OpenAI only
ENVIRONMENT=production API_PROVIDER=openai python simulate.py \
  --persona personas/alex_smith.yml \
  --scenario scenarios/referralCrisis_seniorBackendEngineer.yml
```

### API Provider Examples

```bash
# Use only OpenRouter (recommended for cost savings)
API_PROVIDER=openrouter python simulate.py \
  --persona personas/alex_smith.yml \
  --scenario scenarios/referralCrisis_seniorBackendEngineer.yml

# Use only OpenAI (if you prefer OpenAI's models)
API_PROVIDER=openai python simulate.py \
  --persona personas/alex_smith.yml \
  --scenario scenarios/referralCrisis_seniorBackendEngineer.yml

# Use both (OpenAI for SUT, OpenRouter for Proxy)
API_PROVIDER=both python simulate.py \
  --persona personas/alex_smith.yml \
  --scenario scenarios/referralCrisis_seniorBackendEngineer.yml
```

## 🔒 Security Best Practices

1. **Never commit `.env` files** - They contain sensitive API keys
2. **Use environment-specific configs** - Different settings for different environments
3. **Validate configuration** - Always run `validate_config.py` before deployment
4. **Rotate API keys regularly** - Keep your API keys secure and up-to-date

## 🐛 Troubleshooting

### Common Issues

1. **Missing API Keys**

   ```
   ❌ Missing required environment variables: openai_api_key (from OPENAI_API_KEY)
   ```

   **Solution:** Add the missing API key to your `.env` file

2. **Invalid URLs**

   ```
   ❌ SUT: Invalid URL
   ```

   **Solution:** Check that the URL starts with `http://` or `https://`

3. **Configuration Not Loading**
   ```
   ❌ Configuration validation failed: [Error details]
   ```
   **Solution:** Run `python validate_config.py` to see detailed error information

### Getting Help

1. Run the validation script: `python validate_config.py`
2. Check the logs for detailed error messages
3. Verify your `.env` file format matches `env.template`
4. Ensure all required environment variables are set
