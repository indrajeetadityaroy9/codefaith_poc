def total(items):
    acc = 0
    for i in range(len(items)):
        acc = acc + items[i]
    return acc


def clamp(x, lo, hi):
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x
