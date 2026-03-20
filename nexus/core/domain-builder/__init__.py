"""
NEXUS Domain Builder Engine

Given process.md + domain_knowledge.xlsx + document folder paths as input,
automatically generates a domain expert AI through interactive tools.

Based on NFD (Nurture-First Development) architecture.

Modules:
- analyzer: Excel structure analysis
- converter: Excel -> JSON conversion
- process_refiner: process.md refinement (Socratic question generation)
- skill_generator: process.md -> skill.md conversion
- soul_generator: soul.md generation (interactive question generation)
- config_generator: config.yaml auto-generation
"""
