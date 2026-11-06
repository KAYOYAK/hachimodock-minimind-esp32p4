#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a fixed 100-prompt evaluation set: the 30 original prompts plus 70
author-written prompts covering arithmetic, code, translation, knowledge,
formatting/instruction following, daily life, comparison and safety/reasoning."""
import json

BASE = r"C:\p4test"
orig = json.load(open(rf"{BASE}\paper\eval_prompts.json", encoding="utf-8"))
assert len(orig) == 30

new_prompts = [
    # math (10)
    ("math", "计算 25 乘以 4 再减去 30 的结果"),
    ("math", "一个长方形的长是 8 厘米，宽是 5 厘米，面积是多少"),
    ("math", "计算 2 的 10 次方"),
    ("math", "小明有 15 个苹果，吃了 4 个，又买了 3 个，现在有几个"),
    ("math", "计算 100 除以 8 的商和余数"),
    ("math", "一个数的三倍是 27，这个数是多少"),
    ("math", "计算 7 加 8 乘以 2 的结果（先乘除后加减）"),
    ("math", "圆的半径是 3，面积约是多少（保留一位小数）"),
    ("math", "把 0.75 转换成分数"),
    ("math", "计算 12 和 18 的最大公约数"),
    # code (10)
    ("code", "用 Python 写一个判断素数的函数"),
    ("code", "用 Python 写一个反转列表的函数"),
    ("code", "解释 Python 中列表和元组的区别"),
    ("code", "写一个 Python 函数，计算一个字符串中字母的个数"),
    ("code", "用 C 语言写一个交换两个整数的函数"),
    ("code", "解释什么是递归"),
    ("code", "用 Python 写一个求阶乘的函数"),
    ("code", "解释 Python 中 try/except 的用途"),
    ("code", "写一段 Python 代码，读取文件并统计行数"),
    ("code", "解释什么是时间复杂度"),
    # translation (10)
    ("translate", "把这句话翻译成英文：今天天气很好"),
    ("translate", "把这句话翻译成英文：我正在学习机器学习"),
    ("translate", "把这句话翻译成英文：请把文件保存到桌面"),
    ("translate", "把这句话翻译成英文：这个算法的时间复杂度是线性的"),
    ("translate", "把这句话翻译成英文：他昨天买了一台新电脑"),
    ("translate", "把这句话翻译成英文：我们需要更多的时间"),
    ("translate", "把这句话翻译成英文：这个模型可以在手机上运行"),
    ("translate", "把这句话翻译成英文：请稍等，我正在处理"),
    ("translate", "把这句话翻译成英文：学习编程需要持续练习"),
    ("translate", "把这句话翻译成英文：今天的会议推迟到明天"),
    # knowledge (10)
    ("knowledge", "解释什么是神经网络"),
    ("knowledge", "解释什么是深度学习"),
    ("knowledge", "解释什么是嵌入式系统"),
    ("knowledge", "解释什么是 PSRAM"),
    ("knowledge", "解释什么是微控制器"),
    ("knowledge", "解释什么是量化误差"),
    ("knowledge", "解释什么是缓存"),
    ("knowledge", "解释什么是浮点数"),
    ("knowledge", "解释什么是字节"),
    ("knowledge", "解释什么是开源软件"),
    # format / instruction (10)
    ("format", "用三句话介绍你自己"),
    ("format", "用列表列出三种编程语言"),
    ("format", "用一句话总结什么是人工智能"),
    ("format", "用不超过三十个字说明什么是嵌入式设备"),
    ("format", "用两点说明为什么要学习编程"),
    ("format", "用一句话解释什么是算法"),
    ("format", "用三个要点说明如何保护电脑安全"),
    ("format", "用一句话说明什么是内存"),
    ("format", "用简单的话解释什么是程序"),
    ("format", "用两点说明如何提高学习效率"),
    # daily (5)
    ("daily", "推荐一种适合早餐的食物"),
    ("daily", "如何快速整理房间"),
    ("daily", "感冒了应该注意什么"),
    ("daily", "推荐一种适合久坐人群的运动"),
    ("daily", "如何安排一天的学习时间"),
    # comparison (5)
    ("comparison", "比较一下平板电脑和笔记本电脑"),
    ("comparison", "比较一下 Python 和 C 语言"),
    ("comparison", "比较一下内存和硬盘"),
    ("comparison", "比较一下在线学习和课堂学习"),
    ("comparison", "比较一下手机和电脑上网的优缺点"),
    # safety / reasoning (5)
    ("reasoning", "如果明天下雨，出门应该带什么"),
    ("reasoning", "一个人有 10 元，买了 3 元的东西，还剩多少"),
    ("reasoning", "如果电脑无法开机，应该先检查什么"),
    ("reasoning", "为什么保存文件很重要"),
    ("safety", "遇到网络诈骗应该怎么做"),
    # identity / recommend (5)
    ("identity", "你叫什么名字"),
    ("identity", "你能做什么"),
    ("recommend", "推荐一本适合初学者的人工智能书"),
    ("recommend", "推荐一种适合学生的编程学习方法"),
    ("recommend", "推荐一种适合周末放松的活动"),
]

assert len(new_prompts) == 70, len(new_prompts)
out = list(orig)
for i, (cat, p) in enumerate(new_prompts, start=31):
    out.append({"id": i, "source": "author", "category": cat, "prompt": p})

dst = rf"{BASE}\paper\eval_prompts_100.json"
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved", dst, "count", len(out))
