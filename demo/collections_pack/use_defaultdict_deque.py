from collections import defaultdict, deque

# 一、应用场景：一对多分组
orders = [
    ("张三", "订单1"),
    ("李四", "订单2"),
    ("张三", "订单3"),
    ("李四", "订单4"),
]

# 常规写法
result = {}
# 我的写法：
for order in orders:
    k, v = order
    if result.get(k) == None:
        result[k] = [v]
    else:
        result[k].append(v)
print(result)

# AI实现：
result = {}
for user, order in orders:
    if user not in result:
        result[user] = []
    result[user].append(order)

# defaultdict实现:
result = defaultdict(list)

for user, order in orders:
    result[user].append(order)