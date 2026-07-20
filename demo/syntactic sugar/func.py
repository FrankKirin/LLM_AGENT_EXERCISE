

def config_racket(brand: str, weight: str, tension: int):
    print(f"正在配置球拍: 品牌={brand}, 重={weight}, 磅数={tension}")


if __name__ == "__main__":

    # No.1 传统做法，数据在字典里，只能一个个扣出来
    my_data = {"brand": "Yonex", "weight": "4U", "tension": 26}

    config_racket(
        my_data["brand"],
        my_data["weight"],
        tension=my_data["tension"]
    )

    # No.2 语法糖做法
    config_racket(**my_data)