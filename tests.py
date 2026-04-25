from storage import init_db, save_record, load_all_records, load_record_by_name, delete_record_by_name

init_db()
print("1. 数据库初始化完成")

save_record(
    "45-9-6-5-5-1-58",
    "Saved At: 2026-04-25 21:00:00\n"
    "Status: ok\n"
    "m = 45\n"
    "n = 9\n"
    "k = 6\n"
    "j = 5\n"
    "s = 5\n"
    "Selected Groups:\n"
    "1. (1, 5, 9, 12, 18, 21)\n"
    "2. (5, 9, 12, 21, 27, 33)"
)
print("2. 保存测试记录完成")

save_record(
    "45-10-6-5-4-1-20",
    "Saved At: 2026-04-25 21:05:00\n"
    "Status: ok\n"
    "m = 45\n"
    "n = 10\n"
    "k = 6\n"
    "j = 5\n"
    "s = 4\n"
    "Selected Groups:\n"
    "1. (1, 4, 8, 10, 16, 22)"
)
print("3. 再保存一条测试记录完成")

print("4. 所有记录名：")
print(load_all_records())

print("5. 读取第一条详情：")
print(load_record_by_name("45-9-6-5-5-1-58"))

# 如果你想先保留数据，不要删
# delete_record_by_name("45-9-6-5-5-1-58")
# print("6. 删除第一条后：")
# print(load_all_records())