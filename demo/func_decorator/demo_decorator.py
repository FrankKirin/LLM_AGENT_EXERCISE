import time

def send_message(text):
    print(f"寄出：{text}")

# 实现一个装饰器函数，在寄信前后自动记录时间
def log_wrapper(func):
    def wrapper(text):
        start = time.time()
        time.sleep(2)
        result = func(text)
        end = time.time()
        print(f"开始寄信: {start}, 结束寄信：{end}")
        return result   # 语法上可选
    return wrapper

# 使用方式一：能使用，但是比较啰嗦
# send_message = log_wrapper(send_message)

# send_message("给楼亚楠的情书")

# python语法糖
@log_wrapper
def new_send_message(text):
    print(f"寄出：{text}")

new_send_message("给阿嬷的情书")