import functools


def transparent(function):
    @functools.wraps(function)
    async def wrapper(*args, **kwargs):
        return await function(*args, **kwargs)

    return wrapper


def configured(label):
    def decorator(function):
        @functools.wraps(function)
        async def wrapper(*args, **kwargs):
            result = await function(*args, **kwargs)
            return {label: result}

        return wrapper

    return decorator


def misleading(function):
    @functools.wraps(function)
    async def wrapper(*args, **kwargs):
        return {"called": False}

    return wrapper


def branch_only(function):
    @functools.wraps(function)
    async def wrapper(*args, **kwargs):
        if False:
            return await function(*args, **kwargs)
        return None

    return wrapper


def deferred(function):
    @functools.wraps(function)
    async def wrapper(*args, **kwargs):
        return lambda: function(*args, **kwargs)

    return wrapper
