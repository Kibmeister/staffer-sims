# simulate.py
"""
Main simulation entry point
Refactored to use modular architecture with proper separation of concerns
Enhanced with robust validation, structured errors, and CI-friendly behavior
"""
import yaml
import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load .env file first
load_dotenv()

# Import our configuration system
from config.env_loader import load_environment_config
from config.settings import get_settings

# Import our new modular components
from simulation.simulation_engine import SimulationEngine

### ---------- Validation Functions ----------
def validate_file_exists(file_path: str, file_type: str) -> None:
    """Validate that a file exists and is readable"""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Error: {file_type} file not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    if not path.is_file():
        print(f"❌ Error: {file_type} path is not a file: {file_path}", file=sys.stderr)
        sys.exit(1)
    if not os.access(path, os.R_OK):
        print(f"❌ Error: {file_type} file is not readable: {file_path}", file=sys.stderr)
        sys.exit(1)

def validate_yaml_file(file_path: str, file_type: str) -> Dict[str, Any]:
    """Validate and load YAML file with clear error messages"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
        if content is None:
            print(f"❌ Error: {file_type} file is empty or contains no valid YAML: {file_path}", file=sys.stderr)
            sys.exit(1)
        if not isinstance(content, dict):
            print(f"❌ Error: {file_type} file must contain a YAML dictionary, got {type(content).__name__}: {file_path}", file=sys.stderr)
            sys.exit(1)
        return content
    except yaml.YAMLError as e:
        print(f"❌ Error: Invalid YAML in {file_type} file {file_path}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: Failed to read {file_type} file {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

def validate_numeric_range(value: float, param_name: str, min_val: float, max_val: float) -> None:
    """Validate that a numeric parameter is within the specified range"""
    if not (min_val <= value <= max_val):
        print(f"❌ Error: {param_name} must be between {min_val} and {max_val}, got {value}", file=sys.stderr)
        sys.exit(1)

def validate_positive_integer(value: int, param_name: str) -> None:
    """Validate that a parameter is a positive integer"""
    if value <= 0:
        print(f"❌ Error: {param_name} must be a positive integer, got {value}", file=sys.stderr)
        sys.exit(1)

def validate_persona_structure(persona: Dict[str, Any]) -> None:
    """Validate that persona has required fields"""
    required_fields = ["name"]
    for field in required_fields:
        if field not in persona:
            print(f"❌ Error: Persona file missing required field '{field}'", file=sys.stderr)
            sys.exit(1)

def validate_scenario_structure(scenario: Dict[str, Any]) -> None:
    """Validate that scenario has required fields"""
    required_fields = ["title"]
    for field in required_fields:
        if field not in scenario:
            print(f"❌ Error: Scenario file missing required field '{field}'", file=sys.stderr)
            sys.exit(1)

def setup_structured_logging(settings) -> logging.Logger:
    """Setup structured logging with appropriate levels"""
    # Configure logging format for structured output
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=log_format,
        force=True  # Override any existing configuration
    )
    
    logger = logging.getLogger(__name__)
    
    # Set specific loggers to appropriate levels
    logging.getLogger("simulation").setLevel(logging.INFO)
    logging.getLogger("services").setLevel(logging.INFO)
    logging.getLogger("analysis").setLevel(logging.INFO)
    
    return logger

### ---------- Main Simulation Function ----------
def simulate(args):
    """Run a persona simulation with the given arguments"""
    try:
        # Load environment configuration
        load_environment_config()
        
        # Get settings instance
        settings = get_settings()
        
        # Setup structured logging
        logger = setup_structured_logging(settings)
        
        # Log startup information
        logger.info(f"Starting simulation in {settings.environment} environment")
        logger.info(f"Persona file: {args.persona}")
        logger.info(f"Scenario file: {args.scenario}")
        logger.info(f"Output directory: {getattr(args, 'output', settings.output_dir)}")
        
        # Log parameters at INFO level
        if hasattr(args, 'seed') and args.seed is not None:
            logger.info(f"Random seed: {args.seed}")
        if hasattr(args, 'temperature') and args.temperature is not None:
            logger.info(f"Temperature: {args.temperature}")
        if hasattr(args, 'top_p') and args.top_p is not None:
            logger.info(f"Top-P: {args.top_p}")
        if hasattr(args, 'timeout') and args.timeout is not None:
            logger.info(f"Timeout: {args.timeout}s")
        logger.info(f"Controller enabled: {args.use_controller}")
        
        # Log detailed configuration at DEBUG level
        logger.debug(f"Full configuration: {settings.to_dict()}")
        
        # Validate file existence and load configurations
        validate_file_exists(args.persona, "Persona")
        validate_file_exists(args.scenario, "Scenario")
        validate_file_exists(args.sut_prompt, "SUT prompt")
        
        # Load and validate YAML files
        persona = validate_yaml_file(args.persona, "Persona")
        scenario = validate_yaml_file(args.scenario, "Scenario")
        
        # Validate file structures
        validate_persona_structure(persona)
        validate_scenario_structure(scenario)
        
        # Validate numeric parameters
        if hasattr(args, 'seed') and args.seed is not None:
            validate_positive_integer(args.seed, "Seed")
        
        if hasattr(args, 'temperature') and args.temperature is not None:
            validate_numeric_range(args.temperature, "Temperature", 0.0, 2.0)
        
        if hasattr(args, 'top_p') and args.top_p is not None:
            validate_numeric_range(args.top_p, "Top-P", 0.0, 1.0)
        
        if hasattr(args, 'timeout') and args.timeout is not None:
            validate_positive_integer(args.timeout, "Timeout")
        
        # Log payload summaries at DEBUG level (keys only for security)
        logger.debug(f"Persona keys: {list(persona.keys())}")
        logger.debug(f"Scenario keys: {list(scenario.keys())}")
        
        # Prepare scenario with controller toggle
        scenario = dict(scenario)
        scenario['use_controller'] = args.use_controller
        
        # Initialize simulation engine with context manager for proper cleanup
        with SimulationEngine(settings, sut_prompt_path=args.sut_prompt) as engine:
            # Run simulation
            output_dir = getattr(args, 'output', None) or settings.output_dir
            
            # Inject RNG seed override if provided via CLI or env-backed settings
            if getattr(args, 'seed', None) is not None:
                scenario = dict(scenario)
                scenario['rng_seed_override'] = int(args.seed)
            elif settings.rng_seed is not None:
                scenario = dict(scenario)
                scenario['rng_seed_override'] = int(settings.rng_seed)

            # Allow temperature/top_p/timeout overrides
            if getattr(args, 'temperature', None) is not None:
                scenario = dict(scenario)
                scenario['temperature_override'] = float(args.temperature)
            if getattr(args, 'top_p', None) is not None:
                scenario = dict(scenario)
                scenario['top_p_override'] = float(args.top_p)
            if getattr(args, 'timeout', None) is not None:
                scenario = dict(scenario)
                scenario['conversation_timeout'] = int(args.timeout)

            logger.info("Starting simulation execution")
            results = engine.run_simulation(persona, scenario, output_dir)
            logger.info("Simulation completed successfully")
            
            # Log output paths
            logger.info(f"Transcript saved: {results['transcript_path']}")
            logger.info(f"JSONL saved: {results['jsonl_path']}")
            
            # Print results summary
            print(f"Saved: {results['transcript_path']}")
            print(f"Saved: {results['jsonl_path']}")
            timeout_info = f" - TIMEOUT REACHED" if results.get('timeout_reached', False) else ""
            print(f"Conversation Outcome: {results['final_outcome']['status']} (Level: {results['final_outcome']['completion_level']}%)")
            print(f"Conversation Duration: {results.get('elapsed_time', 0):.1f}s / {results.get('timeout_limit', 120)}s{timeout_info}")
            
            # Print failure information if any
            failures = results['final_outcome'].get('failures', [])
            total_failures = results['final_outcome'].get('total_failures', 0)
            if total_failures > 0:
                print(f"⚠️  Failures Detected: {total_failures} total")
                logger.warning(f"Simulation completed with {total_failures} failures")
                for failure in failures[:3]:  # Show first 3 failures
                    turn_info = f" (turn {failure['turn_occurred']})" if failure.get('turn_occurred') else ""
                    print(f"   • {failure['category']}: {failure['reason']}{turn_info}")
                if len(failures) > 3:
                    print(f"   • ... and {len(failures) - 3} more failures")
            
            # Print sampling parameters
            sampling = results.get('sampling_parameters', {})
            print(f"Sampling Parameters: Seed={sampling.get('random_seed', 'auto')}, Temp={sampling.get('temperature', 'default')}, Top-P={sampling.get('top_p', 'default')}")
            
            info = results['information_gathered']
            print(f"Information Gathered: {len(info['skills_mentioned'])} skills, Role: {info['role_type']}, Location: {info['location']}")
            
            # Print usage and cost information
            usage = results.get('usage_stats', {})
            print(f"API Usage: {usage.get('total_tokens', 0)} tokens ({usage.get('sut_calls', 0)} SUT + {usage.get('proxy_calls', 0)} Proxy calls)")
            print(f"Estimated Cost: ${usage.get('estimated_cost', 0):.6f}")
            
            print("Evaluations: Sent to Langfuse for processing")
            logger.info("Simulation completed successfully")
            
    except KeyboardInterrupt:
        print("\n❌ Simulation interrupted by user", file=sys.stderr)
        logger.error("Simulation interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"❌ Simulation failed: {e}", file=sys.stderr)
        logger.error(f"Simulation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run persona simulation with robust validation and structured logging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic simulation
  python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml
  
  # Reproducible run with specific parameters
  python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml --seed 12345 --temperature 0.7 --top_p 1.0
  
  # Custom output directory and timeout
  python simulate.py --persona personas/alex_smith.yml --scenario scenarios/referralCrisis_seniorBackendEngineer.yml --output results --timeout 300
        """
    )
    
    # Required arguments
    parser.add_argument("--persona", required=True, 
                       help="Path to persona YAML file (must exist and be valid YAML)")
    parser.add_argument("--scenario", required=True, 
                       help="Path to scenario YAML file (must exist and be valid YAML)")
    
    # Optional arguments with validation
    parser.add_argument("--output", default="output", 
                       help="Output directory for transcripts (default: output)")
    parser.add_argument("--seed", type=int, 
                       help="Deterministic RNG seed for reproducible runs (must be positive integer)")
    parser.add_argument("--temperature", type=float, 
                       help="Sampling temperature for response creativity (0.0-2.0, default: 0.7)")
    parser.add_argument("--top_p", type=float, 
                       help="Nucleus sampling parameter (0.0-1.0, default: 1.0)")
    parser.add_argument("--sut-prompt", default="prompts/recruiter_v1.txt", 
                       help="Path to SUT system prompt file (must exist, default: prompts/recruiter_v1.txt)")
    parser.add_argument("--use-controller", type=lambda x: (str(x).lower() == 'true'), default=True, 
                       help="Enable or disable the controller logic (true/false, default: true)")
    parser.add_argument("--timeout", type=int, default=120, 
                       help="Maximum conversation duration in seconds (must be positive, default: 120)")
    
    try:
        args = parser.parse_args()
        simulate(args)
    except SystemExit as e:
        # Re-raise system exit to preserve exit codes
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
