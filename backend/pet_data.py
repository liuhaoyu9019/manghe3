SEED_PETS = [
    # ── Common (60%) · 19种 ──
    {"id": 1,  "name": "乌力乌力", "emoji": "🐔", "rarity": "common",    "description": "石器时代的原鸡，随处可见"},
    {"id": 2,  "name": "布伊",     "emoji": "🐰", "rarity": "common",    "description": "喜欢温暖水域的治愈系宠物"},
    {"id": 3,  "name": "卡克尔",   "emoji": "🦎", "rarity": "common",    "description": "敏捷的爬行宠物，擅长躲藏"},
    {"id": 4,  "name": "克克洛斯", "emoji": "🦃", "rarity": "common",    "description": "脾气暴躁的走地禽"},
    {"id": 5,  "name": "鲁尼",     "emoji": "🐭", "rarity": "common",    "description": "喜欢收集果实的小家伙"},
    {"id": 6,  "name": "霍尔克",   "emoji": "🐗", "rarity": "common",    "description": "皮糙肉厚的野猪"},
    {"id": 15, "name": "威威",     "emoji": "🐕", "rarity": "common",    "description": "忠诚的草原犬，嗅觉灵敏"},
    {"id": 16, "name": "凯比",     "emoji": "🐶", "rarity": "common",    "description": "活泼好动的小猎犬"},
    {"id": 17, "name": "卡拉",     "emoji": "🦜", "rarity": "common",    "description": "色彩斑斓的鹦鹉"},
    {"id": 18, "name": "波比",     "emoji": "🐱", "rarity": "common",    "description": "爱撒娇的野猫"},
    {"id": 19, "name": "诺姆",     "emoji": "🦔", "rarity": "common",    "description": "浑身是刺的小圆球"},
    {"id": 20, "name": "巴尼",     "emoji": "🐏", "rarity": "common",    "description": "毛茸茸的岩羊"},
    {"id": 21, "name": "菲奇",     "emoji": "🐿️", "rarity": "common",    "description": "尾巴蓬松的松鼠"},
    {"id": 22, "name": "普普",     "emoji": "🐧", "rarity": "common",    "description": "摇摇摆摆的企鹅"},
    {"id": 23, "name": "奇卡",     "emoji": "🐤", "rarity": "common",    "description": "毛茸茸的小黄鸡"},
    {"id": 24, "name": "可可",     "emoji": "🦀", "rarity": "common",    "description": "横行霸道的螃蟹"},
    {"id": 25, "name": "达拉",     "emoji": "🦘", "rarity": "common",    "description": "弹跳力惊人的袋鼠"},
    {"id": 26, "name": "克拉尔",   "emoji": "🐢", "rarity": "common",    "description": "背着厚重甲壳的古龟"},
    {"id": 27, "name": "邦诺",     "emoji": "🦛", "rarity": "common",    "description": "憨厚可爱的小河马"},
    # ── Rare (30%) · 9种 ──
    {"id": 7,  "name": "贝鲁卡",   "emoji": "🐯", "rarity": "rare",      "description": "森林之王的幼崽"},
    {"id": 8,  "name": "邦尼",     "emoji": "🦊", "rarity": "rare",      "description": "聪明的狐类宠物"},
    {"id": 9,  "name": "格鲁斯",   "emoji": "🐺", "rarity": "rare",      "description": "月夜下的孤狼"},
    {"id": 10, "name": "利则",     "emoji": "🦈", "rarity": "rare",      "description": "水域中的猎手"},
    {"id": 11, "name": "帖拉",     "emoji": "🐍", "rarity": "rare",      "description": "潜伏在暗处的蛇形宠物"},
    {"id": 28, "name": "奥恩",     "emoji": "🦏", "rarity": "rare",      "description": "厚皮重甲的犀牛"},
    {"id": 29, "name": "巴朵",     "emoji": "🐻", "rarity": "rare",      "description": "力大无穷的巨熊"},
    {"id": 30, "name": "菲欧",     "emoji": "🦩", "rarity": "rare",      "description": "优雅的火烈鸟"},
    {"id": 31, "name": "奇诺",     "emoji": "🦚", "rarity": "rare",      "description": "尾羽华丽的孔雀"},
    # ── Legendary (10%) · 5种 ──
    {"id": 12, "name": "暴龙·布鲁卡", "emoji": "🐉", "rarity": "legendary", "description": "传说中的远古霸主"},
    {"id": 13, "name": "玛斯贝卡",    "emoji": "🦅", "rarity": "legendary", "description": "翱翔天际的王者"},
    {"id": 14, "name": "阿里罗",      "emoji": "🦋", "rarity": "legendary", "description": "带来奇迹的光之蝶"},
    {"id": 32, "name": "白虎",        "emoji": "🐆", "rarity": "legendary", "description": "雪山之巅的圣兽"},
    {"id": 33, "name": "加美",        "emoji": "🦣", "rarity": "legendary", "description": "远古长毛巨象"},
]

DAILY_LIMIT = 3

RARITY_WEIGHTS = {
    "common": 60,
    "rare": 30,
    "legendary": 10,
}


def pick_pet(pets=None):
    import random
    pool = pets if pets is not None else SEED_PETS
    roll = random.random() * 100
    if roll < RARITY_WEIGHTS["legendary"]:
        rarity = "legendary"
    elif roll < RARITY_WEIGHTS["legendary"] + RARITY_WEIGHTS["rare"]:
        rarity = "rare"
    else:
        rarity = "common"
    candidates = [p for p in pool if p["rarity"] == rarity]
    return random.choice(candidates)
