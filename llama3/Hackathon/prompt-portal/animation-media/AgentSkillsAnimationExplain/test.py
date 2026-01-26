from manim import *
class Test(Scene):
    def construct(self):
        d = Dot()
        print(f"Dot type: {type(d)}")
        print(f"Is VMobject: {isinstance(d, VMobject)}")
        vg = VGroup(d)
        self.add(vg)
