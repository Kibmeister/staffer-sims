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
    scenario = load_yaml(args.scenario)
    
    # Initialize simulation engine
    engine = SimulationEngine(settings, sut_prompt_path=args.sut_prompt)
    
    # Run simulation
    output_dir = getattr(args, 'output', None) or settings.output_dir
    # Inject RNG seed override if provided via CLI or env-backed settings
    if getattr(args, 'seed', None) is not None:
        scenario = dict(scenario)
        scenario['rng_seed_override'] = int(args.seed)
    elif settings.rng_seed is not None:
        scenario = dict(scenario)
        scenario['rng_seed_override'] = int(settings.rng_seed)

    # Allow temperature/top_p overrides
    if getattr(args, 'temperature', None) is not None:
        scenario = dict(scenario)
        scenario['temperature_override'] = float(args.temperature)
    if getattr(args, 'top_p', None) is not None:
        scenario = dict(scenario)
        scenario['top_p_override'] = float(args.top_p)

    results = engine.run_simulation(persona, scenario, output_dir)
    
    # Print results summary
    print(f"Saved: {results['transcript_path']}")
    print(f"Saved: {results['jsonl_path']}")
    print(f"Conversation Outcome: {results['final_outcome']['status']} (Level: {results['final_outcome']['completion_level']}%)")
    
    info = results['information_gathered']
    print(f"Information Gathered: {len(info['skills_mentioned'])} skills, Role: {info['role_type']}, Location: {info['location']}")
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
    args = parser.parse_args()
    simulate(args)
