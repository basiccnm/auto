p = r"C:\Users\hardb\Desktop\블로그수입관련\학원비사이트\workers\tipoff-api\insert_academies_national.sql"
sizes = []
with open(p, encoding="utf-8") as f:
    for line in f:
        sizes.append(len(line.encode("utf-8")))
sizes.sort(reverse=True)
print("largest statement bytes:", sizes[:5])
print("total statements:", len(sizes))
