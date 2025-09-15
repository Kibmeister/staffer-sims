# simulate.py
"""
Main simulation entry point
Refactored to use modular architecture with proper separation of concerns
"""
import yaml
import argparse
import logging
from dotenv import load_dotenv

# Load .env file first
load_dotenv()

# Import our configuration system
from config.env_loader import load_environment_config
from config.settings import get_settings

# Import our new modular components
from simulation.simulation_engine import SimulationEngine

### ---------- Helper Functions ----------
def load_yaml(path: str) -> dict:
    """Load YAML file safely"""
    with open(path, "r") as f:
        return yaml.safe_load(f)

### ---------- Main Simulation Function ----------
def simulate(args):
    """Run a persona simulation with the given arguments"""
    # Load environment configuration
    load_environment_config()
    
    # Get settings instance
    settings = get_settings()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.log_format
    )
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting simulation in {settings.environment} environment")
    logger.debug(f"Configuration: {settings.to_dict()}")
    
    # Load persona and scenario configurations
    persona = load_yaml(args.persona)
    # Pass controller toggle into scenario
    scenario = load_yaml(args.scenario)
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

        results = engine.run_simulation(persona, scenario, output_dir)
    
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
        for failure in failures[:3]:  # Show first 3 failures
            turn_info = f" (turn {failure['turn_occurred']})" if failure.get('turn_occurred') else ""
            print(f"   • {failure['category']}: {failure['reason']}{turn_info}")
        if len(failures) > 3:
            print(f"   • ... and {len(failures) - 3} more failures")
    
    info = results['information_gathered']
    print(f"Information Gathered: {len(info['skills_mentioned'])} skills, Role: {info['role_type']}, Location: {info['location']}")
    
    # Print usage and cost information
    usage = results.get('usage_stats', {})
    print(f"API Usage: {usage.get('total_tokens', 0)} tokens ({usage.get('sut_calls', 0)} SUT + {usage.get('proxy_calls', 0)} Proxy calls)")
    print(f"Estimated Cost: ${usage.get('estimated_cost', 0):.6f}")
    
    print("Evaluations: Sent to Langfuse for processing")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run persona simulation")
    parser.add_argument("--persona", required=True, help="Path to persona YAML file")
    parser.add_argument("--scenario", required=True, help="Path to scenario YAML file")
    parser.add_argument("--output", default="output", help="Output directory for transcripts")
    parser.add_argument("--seed", type=int, help="Deterministic RNG seed for per-turn decisions")
    parser.add_argument("--temperature", type=float, help="Sampling temperature (e.g., 0.0..1.2)")
    parser.add_argument("--top_p", type=float, help="Nucleus sampling top_p (0..1)")
    parser.add_argument("--sut-prompt", default="prompts/recruiter_v1.txt", help="Path to SUT system prompt file (default: prompts/recruiter_v1.txt)")
    parser.add_argument("--use-controller", type=lambda x: (str(x).lower() == 'true'), default=True, help="Enable or disable the controller logic (default: True)")
    parser.add_argument("--timeout", type=int, default=120, help="Maximum conversation duration in seconds (default: 120)")
    args = parser.parse_args()
    simulate(args)
