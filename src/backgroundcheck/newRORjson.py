# import json
# import pickle
#
# INPUT_ROR_JSON = "E:/ssrn/data/v1.72-2025-10-06-ror-data_schema_v2.json"
# OUTPUT_ROR_PICKLE = "E:/SSRNPaperResearch/data/new_ror_name.pkl"
#
# def build_slim_ror():
#     with open(INPUT_ROR_JSON, "r", encoding="utf-8") as f:
#         data = json.load(f)
#
#     # 根据你实际的 JSON 结构调整：
#     # 如果 data 本身就是 list，就用 data；
#     # 如果是 {"items": [...]}, 就用 data["items"]
#     if isinstance(data, dict) and "items" in data:
#         items = data["items"]
#     else:
#         items = data
#
#     slim_orgs = []
#
#     for org in items:
#         ror_id = org.get("id")
#         # locations 可能是空列表
#         locations = org.get("locations") or []
#         country_code = None
#         if locations:
#             # 取第一个地点的国家代码（大部分机构国家是唯一的）
#             loc = locations[0]
#             details = loc.get("geonames_details") or {}
#             country_code = details.get("country_code")
#
#         names_entries = org.get("names") or []
#         names = [e["value"] for e in names_entries if "value" in e]
#
#         slim_orgs.append({
#             "id": ror_id,
#             "country_code": country_code,
#             "names": names,
#         })
#
#     with open(OUTPUT_ROR_PICKLE, "wb") as f:
#         pickle.dump(slim_orgs, f)
#
#     print(f"Saved slim ROR data: {len(slim_orgs)} orgs -> {OUTPUT_ROR_PICKLE}")
#
# if __name__ == "__main__":
#     build_slim_ror()
import pickle
import json

PKL_PATH = "E:/SSRNPaperResearch/data/new_ror_name.pkl"
JSON_PATH = "E:/SSRNPaperResearch/data/new_ror_name.json"

# 1. 读取 pkl 文件
with open(PKL_PATH, "rb") as f:
    data = pickle.load(f)   # data 是 Python 对象，如 list/dict

# 2. 写出为 json 文件
with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(
        data,
        f,
        ensure_ascii=False,  # 保留非 ASCII 字符，比如法语重音、中文
        indent=2             # 缩进 2 个空格，方便人类阅读
    )

print("转换完成！")
