l = [0.01, 0.022, 0.035, 0.004, 0.02, 0.0111, 0.03]
for i in range(len(l)):
    for j in range(i, len(l)):
        if l[i] > l[j]:
            temp = l[j]
            l[j] = l[i]
            l[i] = temp

l = [item*1000 for item in l]
print(l)
