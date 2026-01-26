import hashlib
from manim import *
import numpy as np
import os

# Config for cinematic aesthetic
config.background_color = "#0a0a12"
config.frame_width = 16
config.frame_height = 9

class GlowingDot(VGroup):
    """Creates a glowing dot with multiple layers"""
    def __init__(self, color=WHITE, radius=0.1, glow_factor=3, **kwargs):
        super().__init__(**kwargs)
        for i in range(5, 0, -1):
            opacity = 0.15 * (6-i) / 5
            self.add(Dot(radius=radius * i * glow_factor / 5, color=color, fill_opacity=opacity))
        self.add(Dot(radius=radius, color=color, fill_opacity=1))

class PulsingCircle(VGroup):
    """Animated pulsing circle effect"""
    def __init__(self, radius=1, color=BLUE, **kwargs):
        super().__init__(**kwargs)
        self.inner = Circle(radius=radius, color=color, stroke_width=3)
        self.glow = Circle(radius=radius, color=color, stroke_width=8, stroke_opacity=0.3)
        self.add(self.glow, self.inner)

class AgentSkillsDeepDive(Scene):
    def construct(self):
        # --- PATHS TO ASSETS ---
        AUDIO_DIR = "/data/Yanlai/llama3-hackathon/llama3/Hackathon/prompt-portal/AgentSkillsAnimationExplain/audio"
        os.makedirs(AUDIO_DIR, exist_ok=True)

        # --- ENHANCED COLOR PALETTE ---
        indigo = "#6366f1"
        indigo_dark = "#4338ca"
        emerald = "#10b981"
        emerald_dark = "#059669"
        amber = "#f59e0b"
        amber_dark = "#d97706"
        cyan = "#06b6d4"
        cyan_dark = "#0891b2"
        purple = "#a855f7"
        rose = "#f43f5e"
        gray = "#94a3b8"
        gray_dark = "#475569"
        math_blue = "#58c4dd"
        soft_white = "#e2e8f0"

        # --- HELPER FUNCTIONS ---
        self.current_subtitle = None
        self.segment_count = 0
        self.section_number = 0

        def create_glow_effect(mobject, color, blur_radius=0.05, layers=5):
            """Creates a glow effect around any mobject"""
            glow_group = VGroup()
            for i in range(layers, 0, -1):
                opacity = 0.1 * (layers - i + 1) / layers
                glow_copy = mobject.copy().set_stroke(color, width=i*3, opacity=opacity)
                glow_group.add(glow_copy)
            glow_group.add(mobject)
            return glow_group

        def create_section_header(title, number):
            """Creates a beautiful section header"""
            header_group = VGroup()
            
            # Number badge - smaller
            badge = VGroup(
                RoundedRectangle(width=0.6, height=0.6, corner_radius=0.1, 
                                fill_color=indigo, fill_opacity=0.3, stroke_color=indigo),
                Text(str(number), font="Outfit", weight=BOLD).scale(0.4).set_color(soft_white)
            )
            
            # Title with gradient - smaller
            title_text = Text(title, font="Outfit", weight=BOLD).scale(0.6)
            title_text.set_color_by_gradient(soft_white, gray)
            
            # Decorative line
            line = Line(LEFT*1.5, RIGHT*1.5, color=indigo, stroke_width=2, stroke_opacity=0.5)
            
            header_group.add(badge, title_text, line)
            header_group.arrange(DOWN, buff=0.2)
            return header_group.to_edge(UP, buff=0.3)

        def play_segment(text, duration, wait=True):
            self.segment_count += 1
            
            # Cinematic Subtitle Design (Glass-morphism strip)
            sub_bg = Rectangle(
                width=16, height=1.0, 
                fill_color=BLACK, fill_opacity=0.6, 
                stroke_width=0
            ).to_edge(DOWN, buff=0)
            
            # Subtle top border line for the subtitle strip
            sub_line = Line(LEFT*8, RIGHT*8, color=indigo, stroke_width=2, stroke_opacity=0.3).next_to(sub_bg, UP, buff=0)
            
            new_sub = Text(text, font="Outfit", weight=MEDIUM).scale(0.38)
            new_sub.set_color(WHITE).move_to(sub_bg.get_center())
            
            sub_group = VGroup(sub_bg, sub_line, new_sub)
            
            if self.current_subtitle:
                self.play(
                    FadeOut(self.current_subtitle, shift=DOWN*0.3),
                    FadeIn(sub_group, shift=UP*0.3),
                    run_time=0.4
                )
            else:
                self.play(FadeIn(sub_group, shift=UP*0.3), run_time=0.4)
            
            self.current_subtitle = sub_group
            
            # Robust audio mapping using text hash
            txt_hash = hashlib.md5(text.strip().encode()).hexdigest()[:12]
            audio_path = os.path.join(AUDIO_DIR, f"{txt_hash}.ogg")
            
            if os.path.exists(audio_path):
                self.add_sound(audio_path)
            
            if wait:
                self.wait(duration - 0.4 if duration > 0.4 else 0)
            return duration

        def create_data_particle(start, end, color):
            """Creates animated data particles"""
            particle = GlowingDot(color=color, radius=0.03)
            particle.move_to(start)
            return particle

        def animate_connection(start, end, color, run_time=1):
            """Animates a glowing connection line"""
            line = Line(start, end, color=color, stroke_width=2)
            glow = Line(start, end, color=color, stroke_width=8, stroke_opacity=0.3)
            
            # Animated particle along the line
            particle = GlowingDot(color=color, radius=0.05)
            particle.move_to(start)
            
            self.play(Create(glow), Create(line), run_time=run_time*0.5)
            self.play(MoveAlongPath(particle, line), run_time=run_time*0.5)
            self.play(FadeOut(particle), run_time=0.2)
            
            return VGroup(glow, line)

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 0: ANIMATED BACKGROUND & INTRO
        # ═══════════════════════════════════════════════════════════════════════
        
        # Create animated grid with gradient
        grid = NumberPlane(
            x_range=[-10, 10, 1],
            y_range=[-6, 6, 1],
            background_line_style={
                "stroke_color": indigo_dark,
                "stroke_width": 1,
                "stroke_opacity": 0.1
            },
            axis_config={"stroke_opacity": 0}
        )
        
        # Add floating particles in background
        bg_particles = VGroup()
        for _ in range(50):
            x, y = np.random.uniform(-7, 7), np.random.uniform(-4, 4)
            particle = Dot(
                point=[x, y, 0],
                color=indigo,
                radius=np.random.uniform(0.01, 0.03),
                fill_opacity=np.random.uniform(0.1, 0.4)
            )
            bg_particles.add(particle)
        
        self.add(bg_particles)
        self.play(
            Create(grid, run_time=2),
            *[particle.animate.shift(UP*np.random.uniform(-0.5, 0.5)) 
              for particle in bg_particles],
            run_time=2
        )

        # Opening title sequence
        main_title = Text("AGENT SKILLS", font="Outfit", weight=BOLD).scale(1.8)
        main_title.set_color_by_gradient(indigo, cyan, emerald)
        
        subtitle = Text("The Future of Modular AI Intelligence", font="Outfit", weight=LIGHT).scale(0.5)
        subtitle.set_color(gray).next_to(main_title, DOWN, buff=0.4)
        
        # Animated underline
        underline = Line(LEFT*3, RIGHT*3, color=indigo, stroke_width=3)
        underline.next_to(subtitle, DOWN, buff=0.3)
        
        title_group = VGroup(main_title, subtitle, underline)
        
        self.play(
            Write(main_title, run_time=2),
            rate_func=smooth
        )
        self.play(
            FadeIn(subtitle, shift=UP*0.3),
            GrowFromCenter(underline),
            run_time=1
        )
        self.wait(1)
        
        # Transition out
        self.play(
            title_group.animate.scale(0.5).to_edge(UP, buff=0.2).set_opacity(0),
            run_time=1
        )

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 1: THE INTELLIGENCE FORMULA (Enhanced)
        # ═══════════════════════════════════════════════════════════════════════
        
        self.section_number += 1
        header = create_section_header("The Intelligence Formula", self.section_number)
        self.play(FadeIn(header, shift=DOWN*0.3))
        
        play_segment("In the evolution of AI, we often talk about raw intelligence.", 4.9, wait=False)
        self.wait(0.5)
        
        # Create the formula with beautiful styling
        formula_parts = VGroup(
            Text("Intelligence", font="Outfit", weight=BOLD).scale(0.8).set_color(math_blue),
            MathTex("=").scale(1.2).set_color(soft_white),
            Text("Reasoning", font="Outfit", weight=BOLD).scale(0.8).set_color(emerald),
            MathTex("+").scale(1.2).set_color(soft_white),
            Text("Capability", font="Outfit", weight=BOLD).scale(0.8).set_color(amber)
        ).arrange(RIGHT, buff=0.4).shift(DOWN*0.5)
        
        # Add glow effects
        for i, part in enumerate(formula_parts):
            if i in [0, 2, 4]:
                glow = part.copy().set_opacity(0.3).scale(1.1)
                formula_parts[i] = VGroup(glow, part)
        
        # Animated reveal of formula
        self.play(Write(formula_parts[0]), run_time=1.5)
        self.play(Write(formula_parts[1]), run_time=0.5)
        self.wait(2.4) # Wait for first voiceover to finish (4.9 - 0.5 - 2.0)
        
        play_segment("But intelligence isn't just about thinking—it's about DOING.", 4.6)
        
        self.play(
            LaggedStart(
                Write(formula_parts[2]),
                Write(formula_parts[3]),
                Write(formula_parts[4]),
                lag_ratio=0.3
            ),
            run_time=2
        )
        
        # Visual representation of the concept
        brain = SVGMobject("brain.svg").scale(0.5).set_color(emerald) if os.path.exists("brain.svg") else \
                Circle(radius=0.4, color=emerald, fill_opacity=0.2).add(Text("🧠", font_size=24))
        
        gear = SVGMobject("gear.svg").scale(0.5).set_color(amber) if os.path.exists("gear.svg") else \
               RegularPolygon(n=6, color=amber, fill_opacity=0.2).scale(0.4).add(Text("⚙️", font_size=24))
        
        icons_group = VGroup(brain, gear).arrange(RIGHT, buff=3).shift(DOWN*2.0)
        
        play_segment("This is where Agent Skills come in—the bridge between logic and action.", 4.7, wait=False)
        
        self.play(FadeIn(icons_group, shift=UP))
        
        # Connection between brain and gear
        bridge_line = Line(brain.get_right() + RIGHT*0.2, gear.get_left() + LEFT*0.2, 
                          color=cyan, stroke_width=4)
        bridge_glow = bridge_line.copy().set_stroke(width=12, opacity=0.3)
        
        bridge_label = Text("Agent Skills", font="Outfit", weight=BOLD).scale(0.5)
        bridge_label.set_color(cyan).next_to(bridge_line, UP, buff=0.2)
        
        self.play(
            GrowFromEdge(bridge_glow, LEFT),
            GrowFromEdge(bridge_line, LEFT),
            run_time=1.5
        )
        self.play(Write(bridge_label))
        
        # Animated particles flowing through the bridge
        for _ in range(3):
            particle = GlowingDot(color=cyan, radius=0.05)
            particle.move_to(brain.get_right() + RIGHT*0.2)
            self.play(
                MoveAlongPath(particle, bridge_line),
                run_time=0.5
            )
            self.remove(particle)
        self.wait(0.2) # Sync with voiceover (4.7s)
        
        self.wait(1)
        
        # Clean transition
        self.play(
            FadeOut(VGroup(formula_parts, icons_group, bridge_line, bridge_glow, bridge_label, header)),
            run_time=1
        )

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 2: WHAT IS AN AGENT SKILL? (Enhanced Visual Container)
        # ═══════════════════════════════════════════════════════════════════════
        
        self.section_number += 1
        header = create_section_header("The Skill Container", self.section_number)
        self.play(FadeIn(header, shift=DOWN*0.3))
        
        play_segment("What exactly IS an Agent Skill?", 3.4, wait=False)
        self.wait(0.5)
        
        # Create a 3D-like container effect
        container_outer = RoundedRectangle(
            width=8, height=5, corner_radius=0.3,
            stroke_color=indigo, stroke_width=3
        )
        container_glow = container_outer.copy().set_stroke(width=12, opacity=0.2)
        
        # Inner shadow effect
        container_inner = RoundedRectangle(
            width=7.8, height=4.8, corner_radius=0.25,
            fill_color=indigo_dark, fill_opacity=0.1, stroke_width=0
        )
        
        container = VGroup(container_glow, container_outer, container_inner).shift(DOWN*0.8)
        
        # Header bar
        header_bar = VGroup(
            RoundedRectangle(
                width=7.6, height=0.6, corner_radius=0.1,
                fill_color=indigo, fill_opacity=0.3, stroke_width=0
            ),
            Text("CAPABILITY UNIT", font="Outfit", weight=BOLD).scale(0.35).set_color(soft_white)
        )
        header_bar[1].move_to(header_bar[0])
        header_bar.move_to(container.get_top() + DOWN*0.3)
        
        self.play(
            DrawBorderThenFill(container),
            FadeIn(header_bar),
            run_time=2
        )
        self.wait(0.9) # Sync with voiceover (3.4s)
        
        play_segment("Think of it as a self-contained package of intelligence.", 4.0)
        
        # Create three main components with icons and descriptions
        components = VGroup()
        
        # Logic Component
        logic_box = VGroup(
            RoundedRectangle(
                width=2, height=2.5, corner_radius=0.15,
                fill_color=emerald_dark, fill_opacity=0.2,
                stroke_color=emerald, stroke_width=2
            ),
            VGroup(
                RegularPolygon(n=3, color=emerald, fill_opacity=0.5).scale(0.3),
                Text("LOGIC", font="Outfit", weight=BOLD).scale(0.3).set_color(emerald),
                Text("Rules & Reasoning", font="Outfit", weight=LIGHT).scale(0.2).set_color(gray)
            ).arrange(DOWN, buff=0.15)
        )
        logic_box[1].move_to(logic_box[0])
        
        # Tools Component
        tools_box = VGroup(
            RoundedRectangle(
                width=2, height=2.5, corner_radius=0.15,
                fill_color=cyan_dark, fill_opacity=0.2,
                stroke_color=cyan, stroke_width=2
            ),
            VGroup(
                RegularPolygon(n=6, color=cyan, fill_opacity=0.5).scale(0.3),
                Text("TOOLS", font="Outfit", weight=BOLD).scale(0.3).set_color(cyan),
                Text("APIs & Functions", font="Outfit", weight=LIGHT).scale(0.2).set_color(gray)
            ).arrange(DOWN, buff=0.15)
        )
        tools_box[1].move_to(tools_box[0])
        
        # Data Component
        data_box = VGroup(
            RoundedRectangle(
                width=2, height=2.5, corner_radius=0.15,
                fill_color=amber_dark, fill_opacity=0.2,
                stroke_color=amber, stroke_width=2
            ),
            VGroup(
                Circle(radius=0.2, color=amber, fill_opacity=0.5),
                Text("DATA", font="Outfit", weight=BOLD).scale(0.3).set_color(amber),
                Text("Context & Memory", font="Outfit", weight=LIGHT).scale(0.2).set_color(gray)
            ).arrange(DOWN, buff=0.15)
        )
        data_box[1].move_to(data_box[0])
        
        components.add(logic_box, tools_box, data_box)
        components.arrange(RIGHT, buff=0.5).move_to(DOWN*0.3)
        
        play_segment("It bundles three key elements: Logic, Tools, and Data.", 4.8, wait=False)
        
        self.play(
            LaggedStart(
                FadeIn(logic_box, shift=UP*0.5),
                FadeIn(tools_box, shift=UP*0.5),
                FadeIn(data_box, shift=UP*0.5),
                lag_ratio=0.4
            ),
            run_time=2
        )
        self.wait(2.8) # Sync with voiceover (4.8s)
        
        # Show connections between components
        connections = VGroup()
        for i in range(len(components) - 1):
            conn = DoubleArrow(
                components[i].get_right() + LEFT*0.1,
                components[i+1].get_left() + RIGHT*0.1,
                color=gray, stroke_width=2, buff=0.1,
                max_tip_length_to_length_ratio=0.15
            )
            connections.add(conn)
        
        play_segment("These components work together seamlessly.", 3.0)
        self.play(Create(connections))
        
        # Animate data flow
        for _ in range(2):
            for i in range(len(connections)):
                particle = GlowingDot(color=soft_white, radius=0.04)
                particle.move_to(components[i].get_right())
                self.play(
                    particle.animate.move_to(components[i+1].get_left()),
                    run_time=0.3
                )
                self.remove(particle)
        
        play_segment("Write it once—plug it into ANY agent.", 3.2)
        
        # Pulsing effect
        self.play(
            container.animate.scale(1.03),
            run_time=0.4, rate_func=there_and_back_with_pause
        )
        
        self.play(FadeOut(VGroup(container, header_bar, components, connections, header)))

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 3: THE SKILL.MD BLUEPRINT (Enhanced)
        # ═══════════════════════════════════════════════════════════════════════
        
        self.section_number += 1
        header = create_section_header("The SKILL.MD Blueprint", self.section_number)
        self.play(FadeIn(header, shift=DOWN*0.3))
        
        play_segment("The brain of every skill lives in a file called SKILL.MD", 4.6, wait=False)
        self.wait(0.5)
        
        # Create a code editor-like visual
        editor_frame = VGroup(
            # Window frame
            RoundedRectangle(
                width=10, height=6, corner_radius=0.2,
                fill_color="#1e1e2e", fill_opacity=0.95,
                stroke_color=gray_dark, stroke_width=1
            ),
            # Title bar
            RoundedRectangle(
                width=10, height=0.6, corner_radius=0.2,
                fill_color="#2d2d3f", fill_opacity=1, stroke_width=0
            ).align_to(RoundedRectangle(width=10, height=6), UP)
        )
        
        # Window buttons
        buttons = VGroup(
            Circle(radius=0.08, fill_color=rose, fill_opacity=1, stroke_width=0),
            Circle(radius=0.08, fill_color=amber, fill_opacity=1, stroke_width=0),
            Circle(radius=0.08, fill_color=emerald, fill_opacity=1, stroke_width=0)
        ).arrange(RIGHT, buff=0.15).move_to(editor_frame[1]).shift(LEFT*4.2)
        
        file_name = Text("SKILL.MD", font="JetBrains Mono", weight=MEDIUM).scale(0.3)
        file_name.set_color(soft_white).move_to(editor_frame[1])
        
        editor_group = VGroup(editor_frame, buttons, file_name).shift(DOWN*1.0)
        
        self.play(FadeIn(editor_group, shift=UP*0.3))
        self.wait(3.7) # Sync with voiceover (4.6s)
        
        # Animated markdown content
        md_content = VGroup(
            VGroup(
                Text("# ", font="JetBrains Mono").scale(0.25).set_color(rose),
                Text("Legal Researcher Skill", font="JetBrains Mono").scale(0.25).set_color(soft_white)
            ).arrange(RIGHT, buff=0.1),
            VGroup(
                Text("## ", font="JetBrains Mono").scale(0.25).set_color(amber),
                Text("Description", font="JetBrains Mono").scale(0.25).set_color(soft_white)
            ).arrange(RIGHT, buff=0.1),
            Text("Analyzes legal documents and precedents.", font="JetBrains Mono").scale(0.2).set_color(gray),
            VGroup(
                Text("## ", font="JetBrains Mono").scale(0.25).set_color(amber),
                Text("Tools", font="JetBrains Mono").scale(0.25).set_color(soft_white)
            ).arrange(RIGHT, buff=0.1),
            VGroup(
                Text("- ", font="JetBrains Mono").scale(0.2).set_color(cyan),
                Text("search_case_law(query)", font="JetBrains Mono").scale(0.2).set_color(emerald)
            ).arrange(RIGHT, buff=0.05),
            VGroup(
                Text("- ", font="JetBrains Mono").scale(0.2).set_color(cyan),
                Text("summarize_document(doc_id)", font="JetBrains Mono").scale(0.2).set_color(emerald)
            ).arrange(RIGHT, buff=0.05),
            VGroup(
                Text("- ", font="JetBrains Mono").scale(0.2).set_color(cyan),
                Text("compare_statutes(s1, s2)", font="JetBrains Mono").scale(0.2).set_color(emerald)
            ).arrange(RIGHT, buff=0.05),
            VGroup(
                Text("## ", font="JetBrains Mono").scale(0.25).set_color(amber),
                Text("Context Rules", font="JetBrains Mono").scale(0.25).set_color(soft_white)
            ).arrange(RIGHT, buff=0.1),
            Text("Load only relevant jurisdiction data.", font="JetBrains Mono").scale(0.2).set_color(gray),
        ).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        md_content.move_to(editor_frame[0]).shift(DOWN*0.1 + LEFT*1.5)
        
        play_segment("This Markdown file defines everything: purpose, tools, and rules.", 5.6, wait=False)
        
        # Typewriter effect for code - synced with audio
        self.play(
            LaggedStart(
                *[Write(line) for line in md_content],
                lag_ratio=0.3
            ),
            run_time=4
        )
        self.wait(1.6) # Sync with voiceover (5.6s)
        self.wait(1)
        
        # Highlight sections
        play_segment("The description tells agents WHAT this skill does.", 4.5)
        
        highlight_1 = SurroundingRectangle(
            VGroup(md_content[1], md_content[2]),
            color=amber, buff=0.1, stroke_width=2
        )
        self.play(Create(highlight_1))
        self.wait(1)
        self.play(FadeOut(highlight_1))
        
        play_segment("Tools define the specific ACTIONS it can take.", 3.5)
        
        highlight_2 = SurroundingRectangle(
            VGroup(md_content[3], md_content[4], md_content[5], md_content[6]),
            color=emerald, buff=0.1, stroke_width=2
        )
        self.play(Create(highlight_2))
        self.wait(1)
        self.play(FadeOut(highlight_2))
        
        play_segment("Context Rules prevent information overload.", 3.5)
        
        highlight_3 = SurroundingRectangle(
            VGroup(md_content[7], md_content[8]),
            color=cyan, buff=0.1, stroke_width=2
        )
        self.play(Create(highlight_3))
        self.wait(1)
        
        self.play(FadeOut(VGroup(editor_group, md_content, highlight_3, header)))

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 4: PROGRESSIVE DISCLOSURE (Enhanced Visualization)
        # ═══════════════════════════════════════════════════════════════════════
        
        self.section_number += 1
        header = create_section_header("Progressive Disclosure", self.section_number)
        self.play(FadeIn(header, shift=DOWN*0.3))
        
        play_segment("One of the biggest problems in AI: context overload.", 4.3)
        
        # Create chaotic noise visualization
        noise_particles = VGroup()
        np.random.seed(42)
        for _ in range(400):
            x, y = np.random.uniform(-6, 6), np.random.uniform(-3.5, 2)
            color = np.random.choice([gray, gray_dark, "#3f3f5f"])
            particle = Dot(
                point=[x, y, 0],
                color=color,
                radius=np.random.uniform(0.02, 0.08),
                fill_opacity=np.random.uniform(0.2, 0.5)
            )
            noise_particles.add(particle)
        
        self.play(FadeIn(noise_particles, lag_ratio=0.002), run_time=2)
        
        # Agent in the center - confused
        agent_core = VGroup(
            Circle(radius=0.6, color=rose, fill_opacity=0.2, stroke_width=3),
            Text("AI", font="Outfit", weight=BOLD).scale(0.4).set_color(rose)
        )
        agent_core[1].move_to(agent_core[0])
        
        play_segment("If an agent tries to process EVERYTHING, it gets overwhelmed.", 4.0, wait=False)
        
        self.play(FadeIn(agent_core))
        
        # Digital tremor effect
        for _ in range(12):
            self.play(
                agent_core.animate.shift(np.random.uniform(-0.15, 0.15, 3)),
                run_time=0.1,
                rate_func=wiggle
            )
        self.play(agent_core.animate.move_to(DOWN*0.5), run_time=0.2)
        self.wait(2.2) # Sync with voiceover (4.0s)
        
        play_segment("This is where Progressive Disclosure changes everything.", 4.1)
        
        # Transform to focused state
        skill_lens = VGroup(
            Annulus(inner_radius=0.8, outer_radius=2.5, color=indigo, fill_opacity=0.15),
            Circle(radius=2.5, color=indigo, stroke_width=2),
        ).shift(DOWN*0.5)
        
        lens_label = Text("Skill Lens", font="Outfit", weight=MEDIUM).scale(0.35)
        lens_label.set_color(indigo).next_to(skill_lens, UP, buff=0.2)
        
        self.play(
            Create(skill_lens),
            Write(lens_label),
            agent_core[0].animate.set_color(emerald),
            run_time=2
        )
        
        play_segment("Skills act as intelligent filters—loading ONLY relevant context.", 4.9)
        
        # Highlight relevant particles and fade others
        relevant_particles = VGroup()
        irrelevant_particles = VGroup()
        
        for particle in noise_particles:
            if np.linalg.norm(particle.get_center()) < 2.5:
                relevant_particles.add(particle)
            else:
                irrelevant_particles.add(particle)
        
        self.play(
            irrelevant_particles.animate.set_opacity(0.05),
            *[p.animate.set_color(cyan).set_opacity(1) for p in relevant_particles],
            run_time=2
        )
        
        # Show efficiency metrics
        metrics = VGroup(
            VGroup(
                Text("Token Cost", font="Outfit").scale(0.3).set_color(gray),
                Text("-70%", font="Outfit", weight=BOLD).scale(0.5).set_color(emerald)
            ).arrange(DOWN, buff=0.1),
            VGroup(
                Text("Accuracy", font="Outfit").scale(0.3).set_color(gray),
                Text("+45%", font="Outfit", weight=BOLD).scale(0.5).set_color(emerald)
            ).arrange(DOWN, buff=0.1),
            VGroup(
                Text("Speed", font="Outfit").scale(0.3).set_color(gray),
                Text("3x", font="Outfit", weight=BOLD).scale(0.5).set_color(emerald)
            ).arrange(DOWN, buff=0.1)
        ).arrange(RIGHT, buff=1.5).to_edge(DOWN, buff=1.85)
        
        play_segment("The result: lower costs, higher accuracy, faster responses.", 5.4)
        
        for metric in metrics:
            metric_box = SurroundingRectangle(
                metric, color=emerald, buff=0.15, stroke_width=1,
                fill_color=emerald_dark, fill_opacity=0.1
            )
            self.play(FadeIn(metric_box), Write(metric), run_time=0.8)
        
        self.wait(1)
        
        self.play(FadeOut(VGroup(
            noise_particles, agent_core, skill_lens, lens_label, metrics, header
        ).add(*[m for m in self.mobjects if isinstance(m, SurroundingRectangle)])))

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 5: INTEROPERABILITY SHOWCASE (Enhanced)
        # ═══════════════════════════════════════════════════════════════════════
        
        self.section_number += 1
        header = create_section_header("Universal Interoperability", self.section_number)
        self.play(FadeIn(header, shift=DOWN*0.3))
        
        play_segment("Because skills are standardized, they work EVERYWHERE.", 3.3)
        
        # Create platform icons with visual flair
        def create_platform_card(name, icon_shape, color):
            card = VGroup(
                RoundedRectangle(
                    width=2.5, height=3, corner_radius=0.15,
                    fill_color=color, fill_opacity=0.1,
                    stroke_color=color, stroke_width=2
                ),
                icon_shape.set_color(color).scale(0.5),
                Text(name, font="Outfit", weight=MEDIUM).scale(0.35).set_color(soft_white)
            )
            card[1].move_to(card[0].get_center() + UP*0.3)
            card[2].move_to(card[0].get_center() + DOWN*0.8)
            return card
        
        vscode = create_platform_card(
            "VS Code",
            VGroup(Square(side_length=0.6, color=cyan).rotate(PI/4)),
            cyan
        )
        cli = create_platform_card(
            "CLI Tools",
            VGroup(
                Rectangle(width=0.8, height=0.5, color=emerald),
                Text(">_", font="JetBrains Mono").scale(0.2).set_color(emerald)
            ),
            emerald
        )
        bots = create_platform_card(
            "Custom Bots",
            Circle(radius=0.3, color=purple),
            purple
        )
        api = create_platform_card(
            "REST APIs",
            VGroup(
                *[Line(LEFT*0.3, RIGHT*0.3, color=amber).shift(UP*i*0.15) for i in range(-2, 3)]
            ),
            amber
        )
        
        platforms = VGroup(vscode, cli, bots, api).arrange(RIGHT, buff=0.5).shift(DOWN*0.5)
        
        self.play(
            LaggedStart(*[FadeIn(p, shift=UP) for p in platforms], lag_ratio=0.2),
            run_time=2
        )
        
        # Central skill icon
        skill_hexagon = VGroup(
            RegularPolygon(n=6, color=indigo, fill_opacity=0.3, stroke_width=3).scale(0.8),
            Text("S", font="Outfit", weight=BOLD).scale(0.6).set_color(soft_white)
        )
        skill_hexagon[1].move_to(skill_hexagon[0])
        skill_hexagon.shift(DOWN*3.3)
        
        self.play(GrowFromCenter(skill_hexagon))
        
        play_segment("One skill. Infinite applications.", 3.2)
        
        # Animate connections to each platform
        for platform in platforms:
            connection = Line(
                skill_hexagon.get_top(),
                platform.get_bottom(),
                color=indigo, stroke_width=2
            )
            glow = connection.copy().set_stroke(width=8, opacity=0.3)
            
            particle = GlowingDot(color=indigo, radius=0.06)
            particle.move_to(skill_hexagon.get_top())
            
            self.play(
                Create(glow), Create(connection),
                MoveAlongPath(particle, connection),
                run_time=0.8
            )
            self.play(
                Indicate(platform, color=indigo, scale_factor=1.1),
                run_time=0.5
            )
            self.remove(particle)
        
        play_segment("A Legal Researcher skill works in chatbots, IDE extensions, or enterprise systems.", 6.3)
        
        # Stable pulse effect
        self.play(
            skill_hexagon.animate.scale(1.1).set_opacity(0.8),
            run_time=1, rate_func=there_and_back
        )
        self.wait(2)
        
        self.play(FadeOut(VGroup(platforms, skill_hexagon, header).add(*[
            m for m in self.mobjects if isinstance(m, Line)
        ])))

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 6: THE ECOSYSTEM VISION (New Section)
        # ═══════════════════════════════════════════════════════════════════════
        
        self.section_number += 1
        header = create_section_header("The Skill Ecosystem", self.section_number)
        self.play(FadeIn(header, shift=DOWN*0.3))
        
        play_segment("The future isn't one giant AI—it's a network of specialized skills.", 5.1)
        
        # Create a network of interconnected skills
        skill_network = VGroup()
        skill_positions = [
            ORIGIN,
            UP*1.5 + LEFT*2, UP*1.5 + RIGHT*2,
            DOWN*1.5 + LEFT*2, DOWN*1.5 + RIGHT*2,
            LEFT*3.5, RIGHT*3.5,
            UP*2.5, DOWN*2.5
        ]
        
        skill_names = [
            "Core", "Legal", "Finance", "Medical", "DevOps",
            "Research", "Creative", "Analysis", "Support"
        ]
        
        skill_colors = [
            indigo, emerald, amber, rose, cyan,
            purple, amber, emerald, cyan
        ]
        
        skill_nodes = VGroup()
        for i, (pos, name, color) in enumerate(zip(skill_positions, skill_names, skill_colors)):
            node = VGroup(
                Circle(radius=0.4 if i == 0 else 0.3, color=color, fill_opacity=0.3, stroke_width=2),
                Text(name, font="Outfit").scale(0.2).set_color(soft_white)
            )
            node[1].move_to(node[0])
            node.move_to(pos)
            skill_nodes.add(node)
        
        # Create connections
        connections = VGroup()
        for i in range(1, len(skill_nodes)):
            conn = Line(
                skill_nodes[0].get_center(),
                skill_nodes[i].get_center(),
                color=gray_dark, stroke_width=1, stroke_opacity=0.5
            )
            connections.add(conn)
        
        # Cross connections
        cross_connections = [
            (1, 2), (3, 4), (1, 5), (2, 6), (3, 7), (4, 8)
        ]
        for i, j in cross_connections:
            conn = Line(
                skill_nodes[i].get_center(),
                skill_nodes[j].get_center(),
                color=gray_dark, stroke_width=1, stroke_opacity=0.3
            )
            connections.add(conn)
        
        self.play(
            LaggedStart(*[GrowFromCenter(node) for node in skill_nodes], lag_ratio=0.1),
            run_time=2
        )
        self.play(Create(connections), run_time=1.5)
        
        play_segment("Each skill is a specialist. Together, they form unlimited intelligence.", 5.3)
        
        # Pulse effect through the network
        for _ in range(2):
            pulse = Circle(radius=0.1, color=indigo, fill_opacity=0.8)
            pulse.move_to(skill_nodes[0])
            self.play(
                pulse.animate.scale(30).set_opacity(0),
                run_time=1.5
            )
            self.remove(pulse)
        
        self.play(FadeOut(VGroup(skill_nodes, connections, header)))

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 7: GRAND FINALE
        # ═══════════════════════════════════════════════════════════════════════
        
        play_segment("Modular intelligence is the standard of the next generation.", 4.4)
        
        # Create stunning logo reveal
        logo_text = Text("AgentSkills", font="Outfit", weight=BOLD).scale(2)
        logo_suffix = Text(".io", font="Outfit", weight=LIGHT).scale(2).set_color(cyan)
        logo_suffix.next_to(logo_text, RIGHT, buff=0.1)
        
        logo_group = VGroup(logo_text, logo_suffix)
        logo_text.set_color_by_gradient(indigo, cyan)
        
        # Merging skill blocks effect
        blocks = VGroup()
        colors = [indigo, cyan, emerald, amber, purple, rose]
        for i in range(12):
            block = RegularPolygon(n=6, fill_opacity=0.7, stroke_width=2).scale(0.3)
            block.set_color(colors[i % len(colors)])
            block.move_to([np.random.uniform(-7, 7), np.random.uniform(-4, 4), 0])
            blocks.add(block)
        
        self.play(FadeIn(blocks, lag_ratio=0.1), run_time=1)
        
        # Redesigned logo
        final_logo = Text("AgentSkills.io", font="Outfit", weight=BOLD).scale(1.5)
        final_logo.set_color_by_gradient(indigo, cyan)
        
        # Particles assembling the logo
        self.play(
            LaggedStart(*[
                block.animate.move_to(final_logo.get_center() + np.random.uniform(-0.5, 0.5, 3)).set_opacity(0)
                for block in blocks
            ], lag_ratio=0.05),
            Write(final_logo),
            run_time=2.5
        )
        
        # Tagline with a glow pulse
        tagline = Text("Modular Intelligence. Limitless Capability.", font="Outfit", weight=LIGHT)
        tagline.scale(0.45).set_color(gray).next_to(final_logo, DOWN, buff=0.6)
        
        play_segment("Empower your agents. Join the modular revolution.", 4.2)
        
        self.play(
            FadeIn(tagline, shift=UP*0.3),
            final_logo.animate.set_color_by_gradient(cyan, emerald),
            run_time=1.5
        )
        
        # Final subtle bloom
        bloom = final_logo.copy().set_stroke(width=15, opacity=0.2).set_color(cyan)
        self.play(FadeIn(bloom), rate_func=there_and_back_with_pause, run_time=2)
        
        self.wait(3)
        
        # Final fade to black
        self.play(
            *[FadeOut(m) for m in self.mobjects],
            run_time=2
        )
        self.wait(1)