def keep_even(nums, k):
    out = []
    for n in nums:
        if n % 2 == 0:
            out.append(n + k)
    return out
