import flowrep as fr


@fr.atomic
def add(a: float, b: float) -> float:
    """Returns the sum of a and b."""
    return a + b


@fr.atomic
def mul(a: float, b: float) -> float:
    """Returns the product of a and b."""
    return a * b


@fr.workflow
def linear(x: float, slope: float, intercept: float) -> float:
    """y = slope * x + intercept"""
    scaled = mul(x, slope) # type: ignore
    result = add(scaled, intercept) # type: ignore
    return result # type: ignore