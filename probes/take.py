def take(nums, k):
    out = []
    for i in range(len(nums)):
        if i < k:
            out.append(nums[i])
    return out
