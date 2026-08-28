"""
No.1 类变量
应用：统计多少实例
"""
class Dog:
    COUNT = 0
    species = "叶家专宠的狗"

    def __init__(self, name:str):
        self.name = name
        Dog.COUNT += 1
print("*"*50 + "类变量的使用:")
dog_1 = Dog("Frank")
dog_2 = Dog("Kirin")
print(f"Dog类在世界上的实例数量：{Dog.COUNT}")
# 每个实例也可以调用类变量
print(dog_1.species)
print(dog_2.species)

"""
No.2 类方法
应用：工厂方法
"""
class MilkTea:
    total_sold = 0
    pass

    def __init__(self, flavor, size, ice, sugar):
        self.flavor = flavor
        self.size = size
        self.ice = ice
        self.sugar = sugar
        MilkTea.total_sold += 1

    @classmethod
    def from_delivery_platform(cls, order:str):
        # "珍珠-大杯-少冰-半糖"
        parts = order.split("-")
        f, s, i, s = parts[0], parts[1], parts[2], parts[3]
        return cls(f, s, i, s) # 创建并返回一杯奶茶

print("*"*50 + "classmethod的使用:")
order = "抹茶-中杯-去冰-三分糖"
tea = MilkTea.from_delivery_platform(order)
print(tea.flavor)
print(tea.ice)

"""
No.3 property
应用：方法当属性使用
"""
print("*"*50 + "property的使用:")

class Circle:
    def __init__(self, radius: float):
        self.radius = radius

    @property
    def area(self):
        return 3.14 * self.radius * self.radius

    @property
    def cirumference(self):
        return 2 * 3.14 * self.radius



