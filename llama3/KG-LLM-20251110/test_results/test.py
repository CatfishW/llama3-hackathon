import turtle

# 画圆的小工具函数
def draw_circle(t, x, y, r, fill_color=None, pen_size=2):
    t.penup()
    t.goto(x, y - r)          # turtle 以圆心正下方为起点
    t.setheading(0)
    t.pensize(pen_size)
    t.pendown()
    if fill_color:
        t.fillcolor(fill_color)
        t.begin_fill()
    t.circle(r)
    if fill_color:
        t.end_fill()

# 画一个小高光
def draw_highlight(t, x, y, r):
    t.penup()
    t.goto(x, y)
    t.setheading(0)
    t.pendown()
    t.fillcolor("white")
    t.begin_fill()
    t.circle(r)
    t.end_fill()

def main():
    screen = turtle.Screen()
    screen.title("升级版卡通米老鼠")
    screen.bgcolor("white")

    t = turtle.Turtle()
    t.speed(0)
    t.hideturtle()
    t.pencolor("black")

    # ---------------- 头和耳朵 ----------------
    # 耳朵稍微大一点，看起来更可爱
    draw_circle(t, -80, 140, 70, "black")   # 左耳
    draw_circle(t,  80, 140, 70, "black")   # 右耳
    draw_circle(t,   0,  40, 110, "black")  # 外轮廓大头

    # ---------------- 脸部肤色区域 ----------------
    # 上面略窄、下面略圆一点：用两个圆叠出“瓜子脸”效果
    draw_circle(t, 0, 10, 90, "#ffe4c4")    # 主脸
    draw_circle(t, 0, -20, 80, "#ffe4c4")   # 下巴加圆润

    # ---------------- 鼻子 ----------------
    draw_circle(t, 0, 25, 18, "black")

    # 鼻子高光
    draw_highlight(t, 5, 38, 4)

    # ---------------- 眼睛 ----------------
    # 眼白
    draw_circle(t, -30, 70, 20, "white")
    draw_circle(t,  30, 70, 20, "white")

    # 瞳孔（略偏向中间，看起来在看前方）
    draw_circle(t, -25, 77, 8, "black")
    draw_circle(t,  25, 77, 8, "black")

    # 眼睛高光
    draw_highlight(t, -20, 86, 3)
    draw_highlight(t,  30, 86, 3)

    # ---------------- 眉毛 ----------------
    t.pensize(4)
    t.penup()
    t.goto(-45, 100)
    t.setheading(160)
    t.pendown()
    t.circle(40, 40)

    t.penup()
    t.goto(45, 100)
    t.setheading(20)
    t.pendown()
    t.circle(-40, 40)

    # ---------------- 微笑的嘴 ----------------
    t.pensize(5)
    t.pencolor("black")
    t.penup()
    t.goto(-45, 30)
    t.setheading(-60)
    t.pendown()
    t.circle(60, 120)   # 大弧线

    # 嘴角小弧，让笑容更自然
    t.pensize(3)
    t.penup()
    t.goto(-10, 15)
    t.setheading(-130)
    t.pendown()
    t.circle(15, 80)

    t.penup()
    t.goto(10, 15)
    t.setheading(-50)
    t.pendown()
    t.circle(-15, 80)

    # ---------------- 舌头 ----------------
    t.penup()
    t.goto(-15, -5)
    t.setheading(0)
    t.fillcolor("#ff4d4d")
    t.begin_fill()
    t.pendown()
    t.circle(15, 180)  # 半圆
    t.goto(-15, -5)
    t.end_fill()

    # ---------------- 脸颊腮红 ----------------
    draw_circle(t, -55, 20, 13, "#ffb6c1", pen_size=1)
    draw_circle(t,  55, 20, 13, "#ffb6c1", pen_size=1)

    turtle.done()

if __name__ == "__main__":
    main()
