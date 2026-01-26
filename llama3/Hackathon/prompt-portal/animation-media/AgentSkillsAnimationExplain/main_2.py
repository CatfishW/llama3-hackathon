import hashlib
from manim import *
import numpy as np
import os

# Config for cinematic aesthetic
config.background_color = "#0a0a12"
config.frame_width = 16
config.frame_height = 9

# --- CUSTOM COLORS (Modern & Professional) ---
class Colors:
    INDIGO = "#6366f1"
    INDIGO_DARK = "#4338ca"
    EMERALD = "#10b981"
    EMERALD_DARK = "#059669"
    AMBER = "#f59e0b"
    AMBER_DARK = "#d97706"
    CYAN = "#06b6d4"
    CYAN_DARK = "#0891b2"
    PURPLE = "#a855f7"
    ROSE = "#f43f5e"
    GRAY = "#94a3b8"
    GRAY_DARK = "#475569"
    MATH_BLUE = "#58c4dd"
    SOFT_WHITE = "#e2e8f0"
    DEEP_NAVY = "#0a0a12"

class GlassMobject(VGroup):
    """Creates a glassmorphic container effect"""
    def __init__(self, mobject, color=Colors.INDIGO, fill_opacity=0.1, stroke_opacity=0.5, **kwargs):
        super().__init__(**kwargs)
        # Main body
        self.body = mobject.copy().set_fill(color, opacity=fill_opacity).set_stroke(color, width=2, opacity=stroke_opacity)
        # Inner glow / border highlight
        self.highlight = mobject.copy().scale(0.99).set_stroke(color, width=1, opacity=stroke_opacity * 0.5)
        # Outer glow (soft)
        self.glow = mobject.copy().set_stroke(color, width=8, opacity=stroke_opacity * 0.2)
        
        self.add(self.glow, self.body, self.highlight)

class GlowingDot(VGroup):
    """Creates a glowing dot with multiple layers"""
    def __init__(self, color=WHITE, radius=0.1, glow_factor=3, **kwargs):
        super().__init__(**kwargs)
        for i in range(5, 0, -1):
            opacity = 0.15 * (6-i) / 5
            self.add(Dot(radius=radius * i * glow_factor / 5, color=color, fill_opacity=opacity))
        self.add(Dot(radius=radius, color=color, fill_opacity=1))

class NeuralBackground(VGroup):
    """Animated neural-like background with dots and lines"""
    def __init__(self, num_dots=40, area_width=16, area_height=9, **kwargs):
        super().__init__(**kwargs)
        self.dots = VGroup()
        for _ in range(num_dots):
            dot = Dot(
                point=[
                    np.random.uniform(-area_width/2, area_width/2),
                    np.random.uniform(-area_height/2, area_height/2),
                    0
                ],
                radius=0.02,
                color=Colors.INDIGO_DARK,
                fill_opacity=np.random.uniform(0.1, 0.4)
            )
            dot.velocity = np.array([
                np.random.uniform(-0.1, 0.1),
                np.random.uniform(-0.1, 0.1),
                0
            ])
            self.dots.add(dot)
        self.add(self.dots)
        
    def update_dots(self, dt):
        for dot in self.dots:
            dot.shift(dot.velocity * dt)
            # Bounce off edges
            if abs(dot.get_x()) > 8: dot.velocity[0] *= -1
            if abs(dot.get_y()) > 4.5: dot.velocity[1] *= -1

class AgentSkillsAdvanced(MovingCameraScene):
    def construct(self):
        # --- PATHS TO ASSETS ---
        AUDIO_DIR = "/data/Yanlai/llama3-hackathon/llama3/Hackathon/prompt-portal/AgentSkillsAnimationExplain/audio"
        os.makedirs(AUDIO_DIR, exist_ok=True)

        self.current_subtitle = None
        self.section_number = 0

        # --- UTILITIES ---
        def play_segment(text, duration, wait=True):
            # Cinematic Subtitle Design
            sub_bg = Rectangle(
                width=16, height=0.8, 
                fill_color=Colors.DEEP_NAVY, fill_opacity=0.8, 
                stroke_width=0
            ).to_edge(DOWN, buff=0)
            
            sub_line = Line(LEFT*8, RIGHT*8, color=Colors.INDIGO, stroke_width=1, stroke_opacity=0.3).next_to(sub_bg, UP, buff=0)
            new_sub = Text(text, font="Lato", weight=MEDIUM).scale(0.35)
            new_sub.set_color(WHITE).move_to(sub_bg.get_center())
            
            sub_group = VGroup(sub_bg, sub_line, new_sub).set_z_index(100)
            
            if self.current_subtitle:
                self.play(
                    FadeOut(self.current_subtitle, shift=DOWN*0.2),
                    FadeIn(sub_group, shift=UP*0.2),
                    run_time=0.3
                )
            else:
                self.play(FadeIn(sub_group, shift=UP*0.2), run_time=0.3)
            
            self.current_subtitle = sub_group
            
            txt_hash = hashlib.md5(text.strip().encode()).hexdigest()[:12]
            audio_path = os.path.join(AUDIO_DIR, f"{txt_hash}.ogg")
            if os.path.exists(audio_path):
                self.add_sound(audio_path)
            
            if wait:
                self.wait(max(0, duration - 0.3))
            return duration

        def create_section_header(title, number):
            badge = VGroup(
                RoundedRectangle(width=0.5, height=0.5, corner_radius=0.1, 
                                fill_color=Colors.INDIGO, fill_opacity=0.2, stroke_color=Colors.INDIGO, stroke_width=1),
                Text(str(number), font="Lato", weight=BOLD).scale(0.35).set_color(Colors.SOFT_WHITE)
            )
            title_text = Text(title, font="Lato", weight=BOLD).scale(0.55)
            title_text.set_color_by_gradient(Colors.SOFT_WHITE, Colors.GRAY)
            
            header = VGroup(badge, title_text).arrange(RIGHT, buff=0.3)
            underline = Line(LEFT*2, RIGHT*2, color=Colors.INDIGO, stroke_width=2, stroke_opacity=0.4).next_to(header, DOWN, buff=0.2)
            
            full_header = VGroup(header, underline).to_edge(UP, buff=0.4).set_z_index(50)
            return full_header

        # --- BACKGROUND ---
        bg = NeuralBackground().set_z_index(-10)
        bg.add_updater(lambda m, dt: m.update_dots(dt))
        self.add(bg)

        # ═══════════════════════════════════════════════════════════════════════
        # INTRO
        # ═══════════════════════════════════════════════════════════════════════
        main_title = Text("AGENT SKILLS", font="Lato", weight=BOLD).scale(1.8)
        main_title.set_color_by_gradient(Colors.INDIGO, Colors.CYAN, Colors.EMERALD)
        
        subtitle = Text("The Standard for Modular AI Intelligence", font="Lato", weight=LIGHT).scale(0.45)
        subtitle.set_color(Colors.GRAY).next_to(main_title, DOWN, buff=0.4)
        
        intro_group = VGroup(main_title, subtitle)
        
        self.play(
            Write(main_title),
            FadeIn(subtitle, shift=UP*0.3),
            run_time=2
        )
        self.wait(1)
        self.play(intro_group.animate.scale(0.6).to_edge(UP).set_opacity(0), run_time=1)

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 1: THE INTELLIGENCE FORMULA
        # ═══════════════════════════════════════════════════════════════════════
        self.section_number += 1
        header = create_section_header("The Intelligence Formula", self.section_number)
        self.play(FadeIn(header, shift=DOWN*0.3))
        
        play_segment("In the evolution of AI, we often talk about raw intelligence.", 4.9, wait=False)
        self.wait(0.5)
        
        formula = VGroup(
            Text("Intelligence", font="Lato", weight=BOLD).scale(0.7).set_color(Colors.MATH_BLUE),
            MathTex("=").scale(1).set_color(Colors.SOFT_WHITE),
            Text("Reasoning", font="Lato", weight=BOLD).scale(0.7).set_color(Colors.EMERALD),
            MathTex("+").scale(1).set_color(Colors.SOFT_WHITE),
            Text("Capability", font="Lato", weight=BOLD).scale(0.7).set_color(Colors.AMBER)
        ).arrange(RIGHT, buff=0.4).shift(UP*0.5)
        
        self.play(Write(formula[0]), Write(formula[1]), run_time=1)
        self.wait(2.4)
        
        play_segment("But intelligence isn't just about thinking—it's about DOING.", 4.6, wait=False)
        self.play(
            LaggedStart(*[Write(p) for p in formula[2:]], lag_ratio=0.3),
            run_time=1.5
        )
        self.wait(2.5)
        
        # Skill Bridge Visualization
        brain = VGroup(Circle(radius=0.5, color=Colors.EMERALD, fill_opacity=0.2), Text("🧠").scale(0.6)).shift(LEFT*3 + DOWN*1.5)
        gear = VGroup(RegularPolygon(n=8, radius=0.5, color=Colors.AMBER, fill_opacity=0.2), Text("⚙️").scale(0.6)).shift(RIGHT*3 + DOWN*1.5)
        bridge = Line(brain.get_right(), gear.get_left(), color=Colors.CYAN, stroke_width=4)
        bridge_label = Text("Agent Skills", font="Lato", weight=BOLD).scale(0.4).set_color(Colors.CYAN).next_to(bridge, UP, buff=0.2)
        
        play_segment("This is where Agent Skills come in—the bridge between logic and action.", 4.7, wait=False)
        
        self.play(
            FadeIn(brain, shift=RIGHT),
            FadeIn(gear, shift=LEFT),
            Create(bridge),
            Write(bridge_label),
            run_time=2
        )
        
        # Particle Flow
        for _ in range(5):
            p = GlowingDot(color=Colors.CYAN, radius=0.04).move_to(brain.get_right())
            self.play(MoveAlongPath(p, bridge), run_time=0.4, rate_func=linear)
            self.remove(p)
            
        self.wait(1)
        self.play(FadeOut(VGroup(header, formula, brain, gear, bridge, bridge_label)))

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 2: THE SKILL CONTAINER
        # ═══════════════════════════════════════════════════════════════════════
        self.section_number += 1
        header = create_section_header("The Skill Container", self.section_number)
        self.play(FadeIn(header, shift=DOWN*0.3))
        
        play_segment("What exactly IS an Agent Skill?", 3.4, wait=False)
        
        container_rect = RoundedRectangle(width=9, height=5, corner_radius=0.2)
        glass_container = GlassMobject(container_rect, color=Colors.INDIGO).shift(DOWN*0.5)
        
        play_segment("Think of it as a self-contained package of intelligence.", 4.0, wait=False)
        self.play(DrawBorderThenFill(glass_container), run_time=2)
        
        # Component boxes
        comp_labels = ["LOGIC", "TOOLS", "DATA"]
        comp_colors = [Colors.EMERALD, Colors.CYAN, Colors.AMBER]
        comp_icons = ["🧠", "🛠️", "🗄️"]
        
        components = VGroup()
        for label, color, icon in zip(comp_labels, comp_colors, comp_icons):
            box = RoundedRectangle(width=2.2, height=3, corner_radius=0.1)
            glass_box = GlassMobject(box, color=color, fill_opacity=0.15)
            content = VGroup(
                Text(icon).scale(0.8),
                Text(label, font="Lato", weight=BOLD).scale(0.4).set_color(color)
            ).arrange(DOWN, buff=0.3)
            components.add(VGroup(glass_box, content))
            
        components.arrange(RIGHT, buff=0.6).move_to(glass_container.get_center())
        
        play_segment("It bundles three key elements: Logic, Tools, and Data.", 4.8, wait=False)
        self.play(
            LaggedStart(*[FadeIn(c, shift=UP*0.5) for c in components], lag_ratio=0.4),
            run_time=2
        )
        self.wait(2.5)
        
        play_segment("These components work together seamlessly.", 3.0, wait=False)
        # Internal connections
        conn1 = DoubleArrow(components[0].get_right(), components[1].get_left(), buff=0.1, color=Colors.GRAY, stroke_width=2)
        conn2 = DoubleArrow(components[1].get_right(), components[2].get_left(), buff=0.1, color=Colors.GRAY, stroke_width=2)
        self.play(Create(conn1), Create(conn2))
        self.wait(1.5)
        
        play_segment("Write it once—plug it into ANY agent.", 3.2)
        self.play(Indicate(glass_container, color=Colors.CYAN, scale_factor=1.05))
        
        self.play(FadeOut(VGroup(header, glass_container, components, conn1, conn2)))

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 3: THE SKILL.MD BLUEPRINT
        # ═══════════════════════════════════════════════════════════════════════
        self.section_number += 1
        header = create_section_header("The SKILL.MD Blueprint", self.section_number)
        self.play(FadeIn(header, shift=DOWN*0.3))
        
        play_segment("The brain of every skill lives in a file called SKILL.MD", 4.6, wait=False)
        
        editor_base = RoundedRectangle(width=10, height=6, corner_radius=0.2)
        editor = GlassMobject(editor_base, color=Colors.GRAY_DARK, fill_opacity=0.9).shift(DOWN*0.8)
        
        # Title bar
        title_bar = RoundedRectangle(width=10, height=0.6, corner_radius=0.1).set_fill(Colors.GRAY_DARK, opacity=0.5).set_stroke(width=0)
        title_bar.move_to(editor.get_top() + DOWN*0.3)
        dots = VGroup(*[Circle(radius=0.08, color=c, fill_opacity=1) for c in [Colors.ROSE, Colors.AMBER, Colors.EMERALD]]).arrange(RIGHT, buff=0.15).move_to(title_bar.get_left() + RIGHT*0.5)
        filename = Text("SKILL.MD", font="Ubuntu Mono").scale(0.3).move_to(title_bar)
        
        self.play(FadeIn(editor), FadeIn(title_bar), FadeIn(dots), Write(filename))
        self.wait(2)
        
        # Code content
        code_lines = VGroup(
            Text("# Legal Researcher", font="Ubuntu Mono", color=Colors.ROSE).scale(0.3),
            Text("## Description", font="Ubuntu Mono", color=Colors.AMBER).scale(0.25),
            Text("Analyzes legal documents.", font="Ubuntu Mono", color=Colors.GRAY).scale(0.2),
            Text("## Tools", font="Ubuntu Mono", color=Colors.AMBER).scale(0.25),
            Text("- search_case_law()", font="Ubuntu Mono", color=Colors.EMERALD).scale(0.2),
            Text("- summarize_doc()", font="Ubuntu Mono", color=Colors.EMERALD).scale(0.2),
            Text("## Rules", font="Ubuntu Mono", color=Colors.AMBER).scale(0.25),
            Text("Load relevant data only.", font="Ubuntu Mono", color=Colors.GRAY).scale(0.2),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.25).move_to(editor.get_center() + LEFT*1.5 + DOWN*0.2)
        
        play_segment("This Markdown file defines everything: purpose, tools, and rules.", 5.6, wait=False)
        self.play(LaggedStart(*[Write(line) for line in code_lines], lag_ratio=0.1), run_time=4)
        self.wait(1.5)
        
        # Highlighting
        play_segment("The description tells agents WHAT this skill does.", 4.5, wait=False)
        h1 = SurroundingRectangle(code_lines[0:3], color=Colors.AMBER, buff=0.1)
        self.play(Create(h1))
        self.wait(3)
        self.play(FadeOut(h1))
        
        play_segment("Tools define the specific ACTIONS it can take.", 3.5, wait=False)
        h2 = SurroundingRectangle(code_lines[3:6], color=Colors.EMERALD, buff=0.1)
        self.play(Create(h2))
        self.wait(2)
        self.play(FadeOut(h2))
        
        play_segment("Context Rules prevent information overload.", 3.5, wait=False)
        h3 = SurroundingRectangle(code_lines[6:], color=Colors.CYAN, buff=0.1)
        self.play(Create(h3))
        self.wait(2.5)
        
        self.play(FadeOut(VGroup(header, editor, title_bar, dots, filename, code_lines, h3)))

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 4: PROGRESSIVE DISCLOSURE
        # ═══════════════════════════════════════════════════════════════════════
        self.section_number += 1
        header = create_section_header("Progressive Disclosure", self.section_number)
        self.play(FadeIn(header, shift=DOWN*0.3))
        
        play_segment("One of the biggest problems in AI: context overload.", 4.3, wait=False)
        
        # Noise particles
        noise = VGroup(*[Dot(radius=0.03, color=Colors.GRAY_DARK, fill_opacity=0.3).move_to([np.random.uniform(-6, 6), np.random.uniform(-3, 2), 0]) for _ in range(300)])
        self.play(FadeIn(noise, lag_ratio=0.001), run_time=2)
        
        agent = VGroup(Circle(radius=0.6, color=Colors.ROSE, fill_opacity=0.2), Text("AI", weight=BOLD).scale(0.5)).shift(DOWN*0.5)
        self.play(FadeIn(agent))
        
        play_segment("If an agent tries to process EVERYTHING, it gets overwhelmed.", 4.0, wait=False)
        self.play(agent.animate.set_color(Colors.ROSE).scale(1.2), rate_func=wiggle, run_time=2)
        self.wait(1.5)
        
        play_segment("This is where Progressive Disclosure changes everything.", 4.1, wait=False)
        lens = VGroup(
            Annulus(inner_radius=1.0, outer_radius=2.5, color=Colors.INDIGO, fill_opacity=0.2),
            Circle(radius=2.5, color=Colors.INDIGO, stroke_width=2)
        ).move_to(agent)
        
        self.play(Create(lens), agent.animate.scale(0.83).set_color(Colors.EMERALD), run_time=2)
        
        play_segment("Skills act as intelligent filters—loading ONLY relevant context.", 4.9, wait=False)
        
        relevant = []
        irrelevant = []
        for p in noise:
            if np.linalg.norm(p.get_center() - agent.get_center()) < 2.5:
                relevant.append(p)
            else:
                irrelevant.append(p)
                
        self.play(
            *[p.animate.set_color(Colors.CYAN).set_opacity(1) for p in relevant],
            *[p.animate.set_opacity(0.05) for p in irrelevant],
            run_time=2
        )
        self.wait(2)
        
        metrics = VGroup(
            Text("-70% Token Cost", color=Colors.EMERALD).scale(0.4),
            Text("+45% Accuracy", color=Colors.EMERALD).scale(0.4),
            Text("3x Speed", color=Colors.EMERALD).scale(0.4)
        ).arrange(RIGHT, buff=1).to_edge(DOWN, buff=1.5)
        
        play_segment("The result: lower costs, higher accuracy, faster responses.", 5.4, wait=False)
        self.play(LaggedStart(*[FadeIn(m, shift=UP*0.3) for m in metrics], lag_ratio=0.5), run_time=3)
        self.wait(2)
        
        self.play(FadeOut(VGroup(header, noise, agent, lens, metrics)))

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 5: INTEROPERABILITY
        # ═══════════════════════════════════════════════════════════════════════
        self.section_number += 1
        header = create_section_header("Universal Interoperability", self.section_number)
        self.play(FadeIn(header, shift=DOWN*0.3))
        
        play_segment("Because skills are standardized, they work EVERYWHERE.", 3.3, wait=False)
        
        platforms = VGroup(
            VGroup(RoundedRectangle(width=2, height=2.5), Text("VS Code").scale(0.3)).arrange(DOWN),
            VGroup(RoundedRectangle(width=2, height=2.5), Text("CLI").scale(0.3)).arrange(DOWN),
            VGroup(RoundedRectangle(width=2, height=2.5), Text("Custom Bots").scale(0.3)).arrange(DOWN),
            VGroup(RoundedRectangle(width=2, height=2.5), Text("REST APIs").scale(0.3)).arrange(DOWN),
        ).arrange(RIGHT, buff=0.5).shift(DOWN*0.5)
        
        glass_platforms = VGroup(*[GlassMobject(p[0], color=c) for p, c in zip(platforms, [Colors.CYAN, Colors.EMERALD, Colors.PURPLE, Colors.AMBER])])
        for i, p in enumerate(platforms): p[0].become(glass_platforms[i])
        
        self.play(LaggedStart(*[FadeIn(p, shift=UP*0.5) for p in platforms], lag_ratio=0.2), run_time=2)
        
        skill_hex = VGroup(RegularPolygon(n=6, radius=0.6, color=Colors.INDIGO, fill_opacity=0.3), Text("S", weight=BOLD).scale(0.6)).shift(DOWN*3.5)
        self.play(GrowFromCenter(skill_hex))
        
        play_segment("One skill. Infinite applications.", 3.2, wait=False)
        for p in platforms:
            line = Line(skill_hex.get_top(), p.get_bottom(), color=Colors.INDIGO, stroke_opacity=0.3)
            dot = GlowingDot(color=Colors.INDIGO, radius=0.04).move_to(skill_hex.get_top())
            self.play(Create(line), MoveAlongPath(dot, line), run_time=0.6)
            self.play(Indicate(p, color=Colors.CYAN), FadeOut(dot), run_time=0.3)
            
        play_segment("A Legal Researcher skill works in chatbots, IDE extensions, or enterprise systems.", 6.3)
        self.wait(1)
        
        self.play(FadeOut(VGroup(header, platforms, skill_hex, *[m for m in self.mobjects if isinstance(m, Line)])))

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 6: THE ECOSYSTEM
        # ═══════════════════════════════════════════════════════════════════════
        self.section_number += 1
        header = create_section_header("The Skill Ecosystem", self.section_number)
        self.play(FadeIn(header, shift=DOWN*0.3))
        
        play_segment("The future isn't one giant AI—it's a network of specialized skills.", 5.1, wait=False)
        
        nodes = VGroup(*[Circle(radius=0.3, color=np.random.choice([Colors.INDIGO, Colors.CYAN, Colors.EMERALD]), fill_opacity=0.3) for _ in range(10)]).arrange_in_grid(rows=3, cols=4, buff=1).shift(DOWN*0.5)
        connections = VGroup()
        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                if np.random.random() < 0.3:
                    connections.add(Line(nodes[i].get_center(), nodes[j].get_center(), color=Colors.GRAY_DARK, stroke_opacity=0.2))
                    
        self.play(LaggedStart(*[GrowFromCenter(n) for n in nodes], lag_ratio=0.1), Create(connections), run_time=3)
        
        play_segment("Each skill is a specialist. Together, they form unlimited intelligence.", 5.3, wait=False)
        for _ in range(3):
            pulse = Circle(radius=0.1, color=Colors.INDIGO, stroke_width=0, fill_opacity=0.5).move_to(nodes[4])
            self.play(pulse.animate.scale(20).set_opacity(0), run_time=1.5, rate_func=smooth)
            self.remove(pulse)
            
        self.play(FadeOut(VGroup(header, nodes, connections)))

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 7: FINALE
        # ═══════════════════════════════════════════════════════════════════════
        play_segment("Modular intelligence is the standard of the next generation.", 4.4, wait=False)
        
        final_logo = Text("AgentSkills.io", font="Lato", weight=BOLD).scale(1.5)
        final_logo.set_color_by_gradient(Colors.INDIGO, Colors.CYAN)
        tagline = Text("Modular Intelligence. Limitless Capability.", font="Lato", weight=LIGHT).scale(0.5).next_to(final_logo, DOWN, buff=0.5).set_color(Colors.GRAY)
        
        self.play(Write(final_logo), run_time=2)
        play_segment("Empower your agents. Join the modular revolution.", 4.2, wait=False)
        self.play(FadeIn(tagline, shift=UP*0.3), run_time=1.5)
        
        glow = final_logo.copy().set_stroke(Colors.CYAN, width=10, opacity=0.3)
        self.play(FadeIn(glow), rate_func=there_and_back, run_time=2)
        
        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=2)
        self.wait(1)
