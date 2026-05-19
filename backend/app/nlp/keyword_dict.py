LOW_INFORMATION_KEYWORDS = [
    "好评",
    "不错",
    "很好",
    "物流快",
    "物流很快",
    "习惯好评",
    "还没用，先好评",
    "还没用先好评",
    "看起来不错",
    "收到了",
    "下次再来",
]

WATERPROOF_NEGATIVE_KEYWORDS = [
    "漏水",
    "进水",
    "全湿",
    "雨天不行",
    "防水差",
    "内壁水滴",
    "冷凝水",
    "睡袋湿了",
    "地垫湿了",
]

WINDPROOF_NEGATIVE_KEYWORDS = [
    "不防风",
    "风一吹就倒",
    "杆子断",
    "玻璃钢杆断",
    "支架断",
    "接头开裂",
    "结构不稳",
    "地钉松",
]

SPACE_NEGATIVE_KEYWORDS = [
    "空间小",
    "空间虚标",
    "双人放不下",
    "太挤",
    "压抑",
    "放个垫子关不上门",
    "放个双人垫关不上门",
    "高度不够",
]

STORAGE_NEGATIVE_KEYWORDS = [
    "不好收纳",
    "收不回去",
    "收纳袋太小",
    "拉链撑破",
    "自动帐不好收",
    "折不回去",
]

SETUP_NEGATIVE_KEYWORDS = [
    "难搭",
    "不好搭",
    "说明书看不懂",
    "一个人搭不了",
    "搭建复杂",
    "支架难装",
]

SMELL_NEGATIVE_KEYWORDS = [
    "味道大",
    "刺鼻",
    "甲醛味",
    "熏人",
    "头疼",
    "晾了很久还有味",
]

SUNPROOF_NEGATIVE_KEYWORDS = [
    "不防晒",
    "太热",
    "热醒",
    "亮醒",
    "黑胶没用",
    "闷热",
    "防晒差",
]

RETURN_DIFFICULTY_KEYWORDS = [
    "退货麻烦",
    "不给退",
    "退不了",
    "退货被拒",
    "拆了不给退",
    "商家不处理",
]

REFUND_AMOUNT_KEYWORDS = [
    "退款少",
    "只退一部分",
    "扣钱",
    "扣运费",
    "不全额退款",
]

REFUND_SPEED_KEYWORDS = [
    "退款慢",
    "一直不到账",
    "等了很久",
    "平台介入才退",
]

CUSTOMER_SERVICE_KEYWORDS = [
    "客服态度差",
    "客服不理人",
    "客服敷衍",
    "售后扯皮",
    "踢皮球",
]

SHIPPING_FEE_DISPUTE_KEYWORDS = [
    "退货运费自己出",
    "运费自己出",
    "运费自理",
    "扣运费",
    "运费险不赔",
    "退回去运费高",
    "退货运费争议",
]

REDBOOK_AD_KEYWORDS = [
    "闭眼入",
    "姐妹们冲",
    "必买",
    "种草",
    "链接",
    "口令",
    "私信",
    "品牌合作",
    "超值",
    "绝绝子",
]

REDBOOK_REAL_EXPERIENCE_KEYWORDS = [
    "实测",
    "露营用了",
    "下雨",
    "风大",
    "收纳",
    "搭建",
    "过夜",
    "冷凝水",
    "避坑",
    "翻车",
    "真实体验",
]

TENT_USAGE_KEYWORDS = [
    "帐篷",
    "帐",
    "露营",
    "搭建",
    "收纳",
    "防水",
    "防风",
    "下雨",
    "雨",
    "过夜",
    "地钉",
    "风绳",
    "内帐",
    "外帐",
    "睡袋",
    "地垫",
    "黑胶",
]

WEATHER_KEYWORDS = ["下雨", "雨", "雨天", "风大", "大风", "太阳", "暴晒", "冷", "热", "潮", "露水"]
PEOPLE_KEYWORDS = ["一个人", "两个人", "2个人", "三个人", "一家人", "两大一小", "双人", "多人"]
TIME_KEYWORDS = ["一晚", "用了", "用了一晚", "周末", "过夜", "半天", "两天", "第一次", "第二次"]
SCENE_KEYWORDS = ["周末露营", "露营", "湖边", "公园", "海边", "山里", "营地", "草地", "过夜"]
SPECIFIC_PROBLEM_KEYWORDS = (
    WATERPROOF_NEGATIVE_KEYWORDS
    + WINDPROOF_NEGATIVE_KEYWORDS
    + SPACE_NEGATIVE_KEYWORDS
    + STORAGE_NEGATIVE_KEYWORDS
    + SETUP_NEGATIVE_KEYWORDS
    + SMELL_NEGATIVE_KEYWORDS
    + SUNPROOF_NEGATIVE_KEYWORDS
    + RETURN_DIFFICULTY_KEYWORDS
    + REFUND_AMOUNT_KEYWORDS
    + REFUND_SPEED_KEYWORDS
    + CUSTOMER_SERVICE_KEYWORDS
    + SHIPPING_FEE_DISPUTE_KEYWORDS
)

POSITIVE_GENERIC_KEYWORDS = [
    "质量很好",
    "很好",
    "不错",
    "值得购买",
    "值得入手",
    "物流很快",
    "做工很好",
    "性价比高",
    "下次还来",
    "推荐购买",
]

LOW_RISK_NEGATIVE_KEYWORDS = ["快递慢", "物流慢", "包装一般", "颜色不喜欢", "赠品一般", "不好看"]

