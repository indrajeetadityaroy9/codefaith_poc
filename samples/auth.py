def is_adult(age):
    return age >= 18


def can_access(user, resource):
    return user.is_admin and resource.public


def is_enabled(flag):
    return flag == True
