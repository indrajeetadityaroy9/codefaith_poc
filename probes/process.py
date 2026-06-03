def process(nums, k):
    out = []
    for n in nums:
        if n > k:
            out.append(n * 2)
    return out
