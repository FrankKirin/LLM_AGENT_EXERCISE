# 解包
def make_burger(meet, *toppings, **remarks):
    print(f"肉饼: {meet}")
    print(f"额外配料*args: {toppings}")
    print(f"顾客备注**kwargs: {remarks}")

# make_burger("牛肉", "沙拉酱", "西红柿", "芝士")
# print("*"*30)
# make_burger("鸡肉", cut=True, sauce="extra", takeway=False)
# print("*"*30)
# make_burger("鸭肉", "芝士", "辣椒", cut=True, sauce="extra", takeway=False)

# 拆包
my_toppings = ["生菜", "番茄", "酸黄瓜"]

make_burger("牛肉", *my_toppings)

