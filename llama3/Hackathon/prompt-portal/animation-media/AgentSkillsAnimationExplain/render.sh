#!/bin/bash
# Install python dependencies
pip install -r requirements.txt

# Render the animation
# -pql: low quality (480p 15fps) - fast for testing
# -pqh: high quality (1080p 60fps) - for final
python3 -m manim -qh main.py AgentSkillsDeepDive

