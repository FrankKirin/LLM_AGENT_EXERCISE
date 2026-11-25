### 需要llm识别的intent
    "general_qa",  # 通用qa
    "product_specific_qa",  # 指定产品型号问答
    "troubleshooting",  # 
    "warranty_qa",  # 保修相关

### 设置的slot
        "slots": {{
            "product_brand": null,
            "product_model": null,
            "product_component": null,
            "issue_type": null,
            "symptom": null
        }},
1. 预设的Slot：
- 产品品牌
- 产品型号
- 产品组成
- 问题类型
- 症状

2. 必填的Slot


### 设置的metadata