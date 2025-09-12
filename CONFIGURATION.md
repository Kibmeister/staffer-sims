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

| Variable          | Default                                         | Description                                       |
| ----------------- | ----------------------------------------------- | ------------------------------------------------- |
| `ENVIRONMENT`     | `development`                                   | Environment name (development/staging/production) |
| `DEBUG`           | `false`                                         | Enable debug mode                                 |
| `LOG_LEVEL`       | `INFO`                                          | Logging level (DEBUG/INFO/WARNING/ERROR)          |
| `SUT_URL`         | `http://localhost:8080/sut/chat`                | SUT service URL                                   |
| `PROXY_URL`       | `https://openrouter.ai/api/v1/chat/completions` | Proxy service URL                                 |
| `LANGFUSE_HOST`   | `https://cloud.langfuse.com`                    | Langfuse host URL                                 |
| `MAX_TURNS`       | `18`                                            | Maximum conversation turns                        |
| `REQUEST_TIMEOUT` | `120`                                           | Request timeout in seconds                        |
| `RETRY_ATTEMPTS`  | `3`                                             | Number of retry attempts                          |
| `RETRY_DELAY`     | `1.0`                                           | Delay between retries in seconds                  |
| `OUTPUT_DIR`      | `output`                                        | Output directory for simulation results           |

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
ENVIRONMENT=development API_PROVIDER=openrouter python simulate.py --persona personas/alex_smith.yml --scenario scenarios/senior_backend_engineer.yml

# Staging with both providers
ENVIRONMENT=staging API_PROVIDER=both python simulate.py --persona personas/alex_smith.yml --scenario scenarios/senior_backend_engineer.yml

# Production with OpenAI only
ENVIRONMENT=production API_PROVIDER=openai python simulate.py --persona personas/alex_smith.yml --scenario scenarios/senior_backend_engineer.yml
```

### API Provider Examples

```bash
# Use only OpenRouter (recommended for cost savings)
API_PROVIDER=openrouter python simulate.py --persona personas/alex_smith.yml --scenario scenarios/senior_backend_engineer.yml

# Use only OpenAI (if you prefer OpenAI's models)
API_PROVIDER=openai python simulate.py --persona personas/alex_smith.yml --scenario scenarios/senior_backend_engineer.yml

# Use both (OpenAI for SUT, OpenRouter for Proxy)
API_PROVIDER=both python simulate.py --persona personas/alex_smith.yml --scenario scenarios/senior_backend_engineer.yml
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
