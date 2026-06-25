"""基础类型推断示例。

演示 tiny-stubgen 如何从字面量赋值推断变量类型。
"""

# 基本类型
NAME = "tiny-stubgen"
VERSION_MAJOR = 0
VERSION_MINOR = 1
PI = 3.14159
DEBUG = False
EMPTY = None

# 集合类型
SUPPORTED_VERSIONS = [3.11, 3.12, 3.13]
DEFAULT_TAGS = {"python", "typing", "stub"}
EMPTY_LIST = []
EMPTY_DICT = {}

# 字典推断
ERROR_CODES = {404: "Not Found", 500: "Internal Server Error"}
CONFIG = {"host": "localhost", "port": 8080}

# 元组推断
COORDINATE = (10, 20)
RGB = (255, 128, 0)

# 构造函数调用
REGISTRY = dict()
ITEMS = list()
UNIQUE = set()

# f-string
GREETING = f"Hello, {NAME}!"

# 复数
IMPEDANCE = 3 + 4j

# 带类型注解的变量
MAX_RETRIES: int = 3
TIMEOUT: float = 30.0
